#!/usr/bin/env python3
"""Classify manifest install files and check coverage of repository parsers."""

import argparse
import codecs
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

# Isolated script execution does not add the script directory to sys.path.
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from corpus import CHUNK_SIZE, DEFAULT_GAME_DIR, MANIFEST

OUTPUT = MANIFEST.with_name("formats.csv")
FIELDS = ("path", "sha256", "size", "ext", "detected_format", "magic_hex",
          "spec", "tool", "parse_status", "parse_note")
PROBE_SIZE = 4096
PARSE_TIMEOUT = 30
SIGNATURES = {
    b"COTS": "SCW COTS",
    b"LRTC": "SCW LRTC",
    b"MOEG": "GEO",
    b"TXW ": "TXW",
    b"\x3f\x5f\x03\x00": "HLP",
}
SPECS = {
    "SCW COTS": "docs/formats/scw.md",
    "SCW LRTC": "docs/formats/scw.md",
    "GEO": "docs/formats/geo-txw.md",
    "TXW": "docs/formats/geo-txw.md",
    "RIFF/AVI": "docs/analysis/fmv-pipeline.md",
}
MISC_FORMATS = {"BMP", "HLP", "ICO", "INI", "plain text", "XML", "PE"}
COMPANIONS = {"DivxDecoder.dll", "DivxMediaLib.dll", "FileParser.dll"}
PARSERS = {
    "SCW COTS": ("scwdump.py", "--json"),
    "SCW LRTC": ("scwdump.py", "--json"),
    "GEO": ("geo2obj.py", "--json"),
    "TXW": ("txw2png.py", "--list"),
    "PE": ("richhdr.py", "--json"),
}


def detect_format(source, head):
    """Classify a binary stream using a prefix and the PE offset when present."""
    signature = SIGNATURES.get(head[:4])
    if signature:
        return signature
    if head.startswith(b"MZ"):
        if len(head) >= 64:
            pe_offset = int.from_bytes(head[60:64], "little")
            if pe_offset >= 64:
                source.seek(pe_offset)
                if source.read(4) == b"PE\0\0":
                    return "PE"
        return "MZ"
    if head.startswith(b"RIFF") and head[8:12] == b"AVI ":
        return "RIFF/AVI"
    if head.startswith(b"BM") and len(head) >= 18:
        pixels = int.from_bytes(head[10:14], "little")
        dib_size = int.from_bytes(head[14:18], "little")
        if dib_size >= 12 and pixels >= 14 + dib_size:
            return "BMP"
    if (head.startswith(b"\0\0\x01\0") and len(head) >= 6
            and int.from_bytes(head[4:6], "little") > 0):
        return "ICO"

    # Permit a final partial UTF-8 character when the probe fills the buffer.
    encoding = "utf-16" if head.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    try:
        decoded = codecs.getincrementaldecoder(encoding)().decode(
            head, final=len(head) < PROBE_SIZE,
        )
    except UnicodeDecodeError:
        decoded = head.decode("cp1252", errors="replace")
    # Windows DOS text EOF markers can follow the last line.
    decoded = decoded.rstrip("\x1a\r\n")
    if not decoded.strip() or any(not (c.isprintable() or c.isspace()) for c in decoded):
        return "unknown"
    if re.match(r"<(?:\?xml\s|[A-Za-z_][\w.:-]*(?:\s|/?>))", decoded.lstrip()):
        return "XML"
    if (re.search(r"^\s*\[[^\]\r\n]+\][ \t]*\r?$", decoded, re.MULTILINE)
            and re.search(r"^[ \t]*[^;#\s=][^=\r\n]*=", decoded, re.MULTILINE)):
        return "INI"
    return "plain text"


def spec_for(relative, detected):
    if detected == "PE" and relative in COMPANIONS:
        return "docs/analysis/companion-dlls.md"
    if detected == "PE" and relative == "ROTK.exe":
        return "docs/research/safe-disc.md"
    if detected in MISC_FORMATS:
        return "docs/formats/misc.md"
    return SPECS.get(detected, "")


def probe(path, detected):
    command = PARSERS.get(detected)
    if command is None:
        return "", "n/a", "no repository parser"
    script, *options = command
    tool = f"tools/{script}"
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(TOOLS / script), *options, str(path)],
            capture_output=True, timeout=PARSE_TIMEOUT, check=False,
        )
    except subprocess.TimeoutExpired:
        return tool, "fail", f"parser timed out after {PARSE_TIMEOUT} seconds"
    if result.returncode:
        # Keep diagnostics independent of absolute paths and payload strings.
        last_line = result.stderr.rstrip().split(b"\n")[-1]
        error = re.match(rb"([\w.]+(?:Error|Exception)):", last_line)
        reason = error[1].decode("ascii") if error else f"exit {result.returncode}"
        return tool, "fail", f"parser failed ({reason})"

    if detected == "TXW":
        note = "texture table listed"
    elif detected == "PE":
        report, = json.loads(result.stdout)
        status = report["status"]
        if status == "malformed":
            return tool, "fail", "malformed Rich header"
        if status == "invalid":
            note = "Rich records decoded with checksum mismatch"
        else:
            note = f"Rich header {status}"
    elif detected == "GEO":
        note = "mesh parsed"
    else:
        report = json.loads(result.stdout)
        if report.get("error"):
            return tool, "fail", report["error"]
        if detected == "SCW COTS":
            note = "scene TOC parsed"
        else:
            covered = report["covered"].split(" / ")[0]
            if not report["chunks"]:
                return tool, "fail", f"no chunks parsed at {covered}"
            note = f"chunk walk reached {covered}"
            if "stopped_at" in report:
                note += " (next size exceeds EOF)"
    if result.stderr:
        note += " (parser emitted a warning)"
    return tool, "ok", note


def audit(root, manifest):
    with manifest.open(encoding="utf-8", newline="") as source:
        installed = sorted(
            (row for row in csv.DictReader(source) if row["origin"] == "install"),
            key=lambda row: row["path"],
        )
    seen = set()
    for row in installed:
        relative = row["path"]
        if relative in seen:
            raise ValueError(f"duplicate install manifest path: {relative}")
        seen.add(relative)
        path = root / relative
        if root not in path.resolve().parents:
            raise ValueError(f"path escapes game directory: {relative}")

        with path.open("rb") as source:
            head = source.read(PROBE_SIZE)
            detected = detect_format(source, head)
            source.seek(len(head))
            digest = hashlib.sha256(head)
            size = len(head)
            for block in iter(lambda: source.read(CHUNK_SIZE), b""):
                digest.update(block)
                size += len(block)
        if size != int(row["size"]) or digest.hexdigest() != row["sha256"]:
            raise ValueError(f"size or SHA-256 differs from manifest: {relative}")

        tool, status, note = probe(path, detected)
        yield (relative, row["sha256"], size, path.suffix, detected, head[:8].hex(),
               spec_for(relative, detected), tool, status, note)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path,
                        default=os.environ.get("ROTK_GAME_DIR") or DEFAULT_GAME_DIR)
    parser.add_argument("--stdout", action="store_true", help="write CSV to stdout")
    args = parser.parse_args()
    try:
        root = args.game_dir.resolve()
        if not root.is_dir():
            raise ValueError(f"game directory does not exist: {root}")
        prefix = next((path.parent for path in root.parents if path.name == "drive_c"), root)
        destination = OUTPUT.parent.resolve() / OUTPUT.name
        if not args.stdout and prefix in destination.parents:
            raise ValueError("CSV destination is inside the game prefix")
        rows = list(audit(root, MANIFEST))
        if args.stdout:
            write_csv(sys.stdout, rows)
        else:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=destination.parent, encoding="utf-8", newline="", delete=False,
            ) as output:
                temporary_path = Path(output.name)
                try:
                    write_csv(output, rows)
                    output.close()
                    temporary_path.replace(destination)
                finally:
                    temporary_path.unlink(missing_ok=True)
    except (OSError, ValueError) as error:
        parser.exit(1, f"corpus-formats: {error}\n")


def write_csv(output, rows):
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(FIELDS)
    writer.writerows(rows)


if __name__ == "__main__":
    main()

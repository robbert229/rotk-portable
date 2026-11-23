#!/usr/bin/env python3
"""Emit file-offset library fingerprints from the installed Windows binaries."""
import argparse
import csv
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import struct
import sys

if __package__:
    from . import richhdr
    from .corpus import game_dir, game_prefix
    from .validate_dump import PE
else:
    # Isolated Python does not put the script directory on sys.path.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import richhdr
    from corpus import game_dir, game_prefix
    from validate_dump import PE


FIELDS = ("binary", "library", "version", "evidence_kind", "offset", "evidence", "confidence")

# A captured group, when present, is the version printed by the binary.
STRINGS = (
    ("zlib", "unknown", rb"(?:deflate|inflate) ([\d.]+) Copyright [\d-]+ (?:Jean-loup Gailly|Mark Adler)", "observed"),
    ("zlib", "unknown", rb"oversubscribed dynamic bit lengths tree\x00", "inferred"),
    ("MiniZip", "unknown", rb"unzip ([\d.]+) Copyright [\d-]+ Gilles Vollant", "observed"),
    ("libmad", "unknown", rb"MPEG Audio Decoder ([\d.]+[a-z]?)", "observed"),
    ("libmad", "unknown", rb"rcmp_mad_codec\.c\x00", "inferred"),
    ("libmad", "unknown", rb"Underbit Technologies, Inc\.", "inferred"),
    ("DirectX", "8 API", rb"(?:Direct3DCreate8|DirectInput8Create)\x00", "observed"),
    ("DirectX", "unknown", rb"\b(?:DSOUND|DDRAW)\.dll\x00", "inferred"),
    ("Windows ACM", "unknown", rb"\bMSACM32\.dll\x00", "inferred"),
    ("D3DX8", "unknown", rb"DisableD3DXPSGP\x00", "inferred"),
    ("DXErr8", "unknown", rb"(?:D3DXERR_CANNOTATTRSORT|DMUS_E_INVALID_CONTAINER_OBJECT)\x00", "inferred"),
    ("EAX Unified", "unknown", rb"EAXDirectSoundCreate8\x00", "observed"),
    ("DivX playback SDK", "unknown", rb"(?:OpenDivxFile|DivxGetSDKVersion|DivxDecode|divxSplitterFileParse)\x00", "observed"),
    ("DivX playback SDK", "unknown", rb"Not DIVX 5\.0 encoded\x00", "observed"),
    ("SafeDisc", "unknown", rb"\b(?:SECDRV\.SYS|DrvMgt\.dll)\x00", "inferred"),
    ("Microsoft MFC", "7.0", rb"AfxWnd70s\x00", "inferred"),
    ("Microsoft ATL", "unknown", rb"\.\?AVCComObjectRootBase@ATL@@\x00", "inferred"),
    ("Microsoft C++ standard library", "unknown", rb"ios_base::failbit set\x00", "inferred"),
    ("Microsoft C++ COM support", "unknown", rb"\.\?AV_com_error@@\x00", "inferred"),
    ("STLport", "unknown", rb"STLport(?: version)? ([\d.]+)", "observed"),
    ("Miles Sound System", "unknown", rb"Miles Sound System(?: Version ([\d.]+))?", "observed"),
    ("RAD Bink", "unknown", rb"Bink Video(?: Version ([\d.]+[a-z]?))?", "observed"),
    ("RAD Smacker", "unknown", rb"Smacker Video(?: Version ([\d.]+[a-z]?))?", "observed"),
    ("libpng", "unknown", rb"libpng version ([\d.]+)", "observed"),
    ("IJG JPEG", "unknown", rb"Independent JPEG Group", "inferred"),
)
IMPORTS = {
    "d3d8.dll": ("DirectX", "8 API"), "dinput8.dll": ("DirectX", "8 API"),
    "dsound.dll": ("DirectX", "unknown"), "ddraw.dll": ("DirectX", "unknown"),
    "msacm32.dll": ("Windows ACM", "unknown"), "d3dx8.dll": ("D3DX8", "unknown"),
    "eax.dll": ("EAX Unified", "unknown"), "drvmgt.dll": ("SafeDisc", "unknown"),
    "divxmedialib.dll": ("DivX playback SDK", "unknown"),
    "divxdecoder.dll": ("DivX playback SDK", "unknown"),
    "fileparser.dll": ("DivX playback SDK", "unknown"),
    "zlib1.dll": ("zlib", "unknown"), "mad.dll": ("libmad", "unknown"),
    "mss32.dll": ("Miles Sound System", "unknown"),
    "binkw32.dll": ("RAD Bink", "unknown"), "smackw32.dll": ("RAD Smacker", "unknown"),
    "msvcrt.dll": ("Microsoft CRT", "unknown"), "msvcr70.dll": ("Microsoft CRT", "7.0"),
    "msvcr71.dll": ("Microsoft CRT", "7.1"),
    "msvcp60.dll": ("Microsoft C++ standard library", "6.0"),
    "msvcp70.dll": ("Microsoft C++ standard library", "7.0"),
    "mfc42.dll": ("Microsoft MFC", "4.2"), "mfc70.dll": ("Microsoft MFC", "7.0"),
}

# SHA-256 of the first 16 bytes and the entire little-endian window. See the
# corpus notes for source, layout and what each match establishes.
TABLES = (
    ("CRC-32", "IEEE CRC-32 look-up table", 1024,
     "4fbb2cefcba995684367cfc08799f26382167f273095e54fd4ac82f79d7df1b7",
     "12f3e0576d447eb37b36d82ba0c1c5481b8f0d12fdc70347ce4a076b229d4c86"),
    ("MD5/SHA", "MD5 / SHA shared initial state", 16,
     "411d3f1d2390ff3f482ac8df4e730780bb081a192f283d2f373138fd101dc8fe",
     "411d3f1d2390ff3f482ac8df4e730780bb081a192f283d2f373138fd101dc8fe"),
    ("SHA-1", "SHA-1 initial state", 20,
     "411d3f1d2390ff3f482ac8df4e730780bb081a192f283d2f373138fd101dc8fe",
     "ea185fae3b9bf9674c223bdf35136262c6b4d1eb3e288eae8b9a771952b94715"),
    ("SHA-256", "SHA-256 initial state", 32,
     "27e883514456c6f476070c5768db39c93607e59377fa03961f8309fcfe351d2c",
     "5a33fcfec23c49d91bcf58ce2472dc9f3662cd086bd29fc44af2e14567238a30"),
    ("libmad", "rq_table (packed bitfields)", 32828,
     "c7aad560f42b377a623e4a53205b48647964f662cf119da13a2aef67aa825e2e",
     "7429e18f59d5bcd6eec806946b76c6f4b76ee645b69199baa4c082f423f83ca3"),
    ("libmad", "rq_table (MSVC bitfields)", 65656,
     "b3ce4a3ae2cef88f15a9aef6e9c77bab3eee6523cb9056bc574e8b19c27e3e5b",
     "82fbb340867eb9f2fbddf3a8d073900ad36816c92918f2613567e4b74f22716c"),
    ("libmad", "D.dat synthesis window", 2176,
     "2205ef83439c13bf2e46fd3293875092712ac15bcfaca36f7aa3097016674774",
     "947aa8856ee4a8ac4a935192196953a0daccec16d2a2506609a03be72b88480a"),
    ("libmad", "D.dat synthesis window (shift 12)", 2176,
     "0b803b31b75d3418c29fa1333f0073f2c19ddc75df7831a778bda28929f51c2f",
     "ca156d18e69a9b8b826acabf85f8fc53808b1780b77f2063fab34f8c22f2be89"),
    ("libmad", "D.dat synthesis window (rounded shift 14)", 2176,
     "29665a22300d3c6f1514b880f410d3554d51e1632ef230b4b510188254531125",
     "a4f0cc76c8257720a3bcc19731c6143e6d2aa11f75c8ec3e5a51d30849b85887"),
    ("D3DX8", "d3dxmathx3d.obj .rdata constants", 288,
     "d72fb9fe14d3250816558b2800a2205f395174fe86c62efa3dbbea0e998f802c",
     "0aa1a441a87eed3190fc4e855d942e52e731070616f0d99c988c59ea7f750e94"),
    ("dxguid", "IID_IDirectInput8A", 16,
     "b90d9ccff38405fa6357920c229c06de699b9c748587593fd0036c9f16bf3203",
     "b90d9ccff38405fa6357920c229c06de699b9c748587593fd0036c9f16bf3203"),
    ("dxguid", "DS3DALG_HRTF_LIGHT", 16,
     "609285cf2d96122ca90322524a83093eadc29dae4461080f8fe09eb01629b6ac",
     "609285cf2d96122ca90322524a83093eadc29dae4461080f8fe09eb01629b6ac"),
)


@dataclass(frozen=True)
class Hit:
    library: str
    version: str
    kind: str
    offset: int
    evidence: str
    confidence: str = "observed"

    def row(self, binary):
        return (binary, self.library, self.version, self.kind, f"0x{self.offset:08x}",
                f"[{self.confidence}: {self.evidence}]", self.confidence)


def table_hits(data):
    prefixes = {}
    for library, name, size, prefix, digest in TABLES:
        prefixes.setdefault(bytes.fromhex(prefix), []).append((library, name, size, digest))
    for start in range(0, len(data) - 15, 4):
        candidates = prefixes.get(hashlib.sha256(data[start:start + 16]).digest(), ())
        for library, name, size, digest in candidates:
            end = start + size
            if end <= len(data) and hashlib.sha256(data[start:end]).hexdigest() == digest:
                yield Hit(library, "unknown", "table", start, name)


def import_hits(pe):
    _, tables = pe.imports()
    if not tables:
        return
    start, _ = pe.backed(pe.directory(1)[0])
    for index in range(len(tables)):
        name_rva, = struct.unpack_from("<I", pe.data, start + 20 * index + 12)
        offset, end = pe.backed(name_rva)
        dll = pe.data[offset:pe.data.index(b"\0", offset, end)].decode("ascii")
        identity = IMPORTS.get(dll.lower())
        if identity:
            yield Hit(*identity, "import", offset, dll)


def version_resource_hit(data, library, product_marker):
    # StringFileInfo strings are UTF-16LE and values are DWORD-aligned.
    key = "FileVersion".encode("utf-16le") + b"\0\0"
    # Permit only the adjacent version-resource field, not an overlay match.
    marker = re.escape(product_marker.encode("utf-16le"))
    for product in re.finditer(marker, data):
        end = product.start()
        field = data.rfind(key, max(0, end - 768), end)
        if field >= 0:
            start = (field + len(key) + 3) & ~3
            match = re.match(rb"(?:[0-9.]\x00)+(?=\x00\x00| \x00)", data[start:end])
            if match:
                version = match.group().decode("utf-16le")
                yield Hit(library, version, "string", start, f"FileVersion {version}")



def scan(data):
    rich = richhdr.decode(data)
    pe = PE(data)
    yield from import_hits(pe)
    section_names = {section.name for section in pe.sections}
    if {"stxt371", "stxt774"} <= section_names:
        header = rich["pe_offset"]
        section_table = header + 24 + struct.unpack_from("<H", data, header + 20)[0]
        for index, section in enumerate(pe.sections):
            if section.name in ("stxt371", "stxt774"):
                yield Hit("SafeDisc", "unknown", "string", section_table + index * 40,
                          f"{section.name} section name", "inferred")
    for index, entry in enumerate(rich["entries"]):
        key = "legacy checksum" if "record_only_checksum" in rich else rich["status"]
        label = f'{entry["name"]} {entry["prodid"]}/{entry["build"]} x{entry["count"]} ({key})'
        yield Hit("Microsoft build tools", entry["version"], "rich",
                  rich["dans_offset"] + 16 + 8 * index, label)

    for library, version, pattern, confidence in STRINGS:
        for match in re.finditer(pattern, data, re.IGNORECASE):
            captured = match.group(1) if match.lastindex else None
            evidence = match.group().rstrip(b"\0").decode("ascii")[:66]
            yield Hit(library, captured.decode("ascii") if captured else version,
                      "string", match.start(), evidence, confidence)

    # A small version literal alone is weak. Require zlib diagnostics nearby.
    for match in re.finditer(rb"\x00(1\.\d+\.\d+)\x00", data):
        neighborhood = data[max(0, match.start() - 768):match.end() + 768]
        if b"incorrect header check\0" in neighborhood and b"invalid distance code\0" in neighborhood:
            version = match[1].decode("ascii")
            yield Hit("zlib", version, "string", match.start(1), f"{version} near inflate errors", "inferred")

    yield from version_resource_hit(data, "EAX Unified", "EAX Unified\0")
    yield from version_resource_hit(data, "SafeDisc", "Security Windows NT/2K/XP\0")
    crt = b"Microsoft Visual C++ Runtime Library"
    offset = data.find(crt)
    if offset >= 0:
        linker = {(row["prodid"], row["build"]) for row in rich["entries"]}
        version = "unknown"
        if rich["status"] == "valid":
            if (61, 9466) in linker:
                version = "7.0"
            elif any(product == 4 for product, _ in linker) or any(
                    row["prodid"] in (10, 11) for row in rich["entries"]):
                version = "6.0 family"
        yield Hit("Microsoft CRT", version, "string", offset, crt.decode(), "inferred")
    yield from table_hits(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_dir", type=Path, nargs="?", default=game_dir(), help="installed game directory")
    parser.add_argument("--output", type=Path, help="write CSV here instead of stdout")
    args = parser.parse_args()
    try:
        root = args.game_dir.expanduser().resolve(strict=True)
        files = sorted(path for path in root.rglob("*") if path.is_file()
                       and path.suffix.lower() in {".exe", ".dll", ".sys"})
        if not files:
            raise ValueError(f"no Windows binaries under {root}")
        rows = []
        for path in files:
            try:
                hits = set(scan(path.read_bytes()))
            except ValueError as exc:
                raise ValueError(f"{path}: {exc}") from exc
            binary = path.relative_to(root).as_posix()
            rows.extend(hit.row(binary) for hit in hits)
        rows.sort(key=lambda row: (row[0], int(row[4], 16), row[1:]))
        if args.output is None:
            write_csv(sys.stdout, rows)
        else:
            output = args.output.resolve()
            if output.is_relative_to(game_prefix(root)):
                raise ValueError("CSV destination must be outside the game directory")
            with output.open("w", encoding="utf-8", newline="") as stream:
                write_csv(stream, rows)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"libscan: {exc}\n")


def write_csv(stream, rows):
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(FIELDS)
    writer.writerows(rows)


if __name__ == "__main__":
    main()

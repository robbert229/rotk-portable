#!/usr/bin/env python3
"""Inventory printable source paths in the on-disk PE image."""

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import struct


# Root markers also recover strings preceded by printable binary metadata.
SEP = r"[/\\]"
ROOT = rf"(?:[a-z]:{SEP})?{SEP}?eathirdperson{SEP}|[a-z]:{SEP}dev{SEP}lotr{SEP}rotk(?:{SEP}|$)"
PART = r"[a-z0-9_(). -]+"
TAIL = rf"(?:{PART}{SEP})*{PART}\.(?:cpp|c|h|inl|asm|pdb)"
PATTERN = (
    rf"(?:{ROOT})(?:{PART}{SEP})*(?:{PART})?|(?:[a-z]:)?{SEP}{TAIL}|{TAIL}"
)
SOURCE = re.compile(PATTERN, re.ASCII | re.IGNORECASE)
DEV = re.compile(rf"(?:{ROOT})", re.ASCII | re.IGNORECASE)
RUN = re.compile(rb"[ -~]+")


def scan(data):
    """Yield (file offset, encoding, raw spelling) from terminated strings."""
    for encoding, stride, lane in (("ascii", 1, 0), ("utf-16le", 2, 0),
                                   ("utf-16le", 2, 1)):
        stream = data[lane::stride]
        for run in RUN.finditer(stream):
            start, end = run.span()
            if stream[end:end + 1] != b"\0":
                continue
            offset = lane + start * stride
            if stride == 2:
                if data[lane + end * 2:lane + end * 2 + 2] != b"\0\0":
                    continue
                # A UTF-16 literal can start after a printable byte in this
                # lane whose partner in the other lane is nonzero.
                partners = data[lane + 1 + start * 2:lane + 2 + end * 2:2]
                skip = len(partners.rstrip(b"\0"))
                if skip >= end - start:
                    continue
                start += skip
                offset += skip * 2
            spelling = stream[start:end].decode("ascii")
            # Prefer an embedded known root over an apparent relative path
            # when a printable prefix was attached by neighboring data.
            rooted = DEV.search(spelling)
            if rooted:
                spelling = spelling[rooted.start():]
                offset += rooted.start() * stride
            match = SOURCE.fullmatch(spelling)
            if match:
                raw = match.group()
                # Bare filenames need an identifier-like stem to reject
                # punctuation fragments from packed data.
                if not re.search(SEP, raw) and not re.fullmatch(
                    r"[a-z_][a-z0-9_]*\.[a-z]+", raw, re.IGNORECASE | re.ASCII
                ):
                    continue
                yield offset, encoding, raw


def normalize(raw):
    path = raw.lower().replace("\\", "/")
    path = re.sub(r"/+", "/", path)
    if DEV.match(path) and "/code/" in path:
        path = path[path.index("/code/") + 1:]
    return path.removeprefix("./")


def pe_locations(data):
    """Return section ranges and preferred image base for PE32 or PE32+."""
    if data[:2] != b"MZ":
        raise ValueError("expected a DOS header")
    pe, = struct.unpack_from("<I", data, 0x3C)
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("expected a PE signature")
    count, = struct.unpack_from("<H", data, pe + 6)
    size, = struct.unpack_from("<H", data, pe + 20)
    optional = pe + 24
    magic, = struct.unpack_from("<H", data, optional)
    if size < 64 or magic not in (0x10B, 0x20B):
        raise ValueError("expected a PE32 or PE32+ optional header")
    base, = struct.unpack_from("<I" if magic == 0x10B else "<Q", data,
                               optional + (28 if magic == 0x10B else 24))
    headers, = struct.unpack_from("<I", data, optional + 60)
    sections = []
    for index in range(count):
        entry = optional + size + 40 * index
        name, virtual_size, rva, raw_size, offset = struct.unpack_from("<8s4I", data, entry)
        section = name.rstrip(b"\0").decode("ascii", errors="backslashreplace")
        sections.append((offset, raw_size, virtual_size or raw_size, rva,
                         section or f"<section-{index}>"))
    return base, headers, sections


def location(offset, layout):
    base, headers, sections = layout
    for start, size, mapped, rva, name in sections:
        delta = offset - start
        if 0 <= delta < size:
            return name, base + rva + delta if delta < mapped else None
    if offset < headers:
        return "<headers>", base + offset
    return "<unmapped>", None


def inventory(data):
    layout = pe_locations(data)
    paths = defaultdict(list)
    for offset, encoding, raw in sorted(scan(data)):
        section, va = location(offset, layout)
        paths[normalize(raw)].append((offset, section, va, encoding, raw))
    return dict(sorted(paths.items()))


def render_inventory(paths, digest):
    lines = [f"# Packed PE SHA-256 {digest}", "# Regenerate with: make srcpaths",
             "# Normalised path<TAB>hit count<TAB>JSON hits [file offset, section, packed VA, encoding, raw]"]
    for path, hits in paths.items():
        records = [(f"0x{offset:08X}", section, None if va is None else f"0x{va:08X}",
                    encoding, raw) for offset, section, va, encoding, raw in hits]
        lines.append(f"{path}\t{len(hits)}\t{json.dumps(records)}")
    return "\n".join(lines) + "\n"


README_MODULES = {
    "Actors", "Animation", "Camera", "Collision", "DTB", "Hi-Rendering",
    "Kernel", "Lib", "LL", "Lo-Rendering", "Physics", "RCMP", "SFX", "UI",
}


def render_modules(paths, digest):
    modules = defaultdict(list)
    module_spellings = {name.lower(): name for name in README_MODULES}
    backends = []
    for path, hits in paths.items():
        if not path.endswith(".c") or not path.startswith("code/") or path.count("/") < 2:
            continue
        offset, section, _, _, raw = hits[0]
        parts = re.split(r"[/\\]+", raw)
        relative = "/".join(parts[-path.count("/"):])
        module, _, unit = relative.partition("/")
        module = module_spellings.setdefault(module.lower(), module)
        modules[module].append((unit, offset, section))
        if unit.split("/")[-1].lower().startswith("ll") and unit.lower().endswith("_win.c"):
            backends.append((relative, offset, section))

    c_count = sum(path.endswith(".c") for path in paths)
    sections = ", ".join(sorted({section for hits in paths.values()
                                 for _, section, _, _, _ in hits}))
    encodings = ", ".join(sorted({encoding for hits in paths.values()
                                  for _, _, _, encoding, _ in hits}))
    lines = [
        "# Packed ROTK.exe module map",
        "",
        f"Image SHA-256 `{digest}`.",
        "",
        f"[observed: {len(paths)} distinct paths in {sections or 'no sections'}",
        f"({encodings or 'no hits'}). See the [path inventory](../../re/strings/source_paths.txt)",
        "for offsets, packed-image VAs, and raw spellings].",
        "",
        f"[observed: {c_count} distinct `.c` paths in the inventory versus 563 C objects compiled",
        "by cl 13.00.9466 in the retail Rich header, as recorded in",
        "[WP-0.6](../roadmap.md) and the [README toolchain findings](../../README.md)].",
        "[inferred: 563 is an upper bound for game units from that compiler build. It",
        "includes static CRT objects. Game units may lack source-path literals, or their",
        "literals may only be visible after unpacking SafeDisc-protected regions].",
        "[unknown: how much of the gap each cause accounts for and which readable paths",
        "have assert or `__FILE__` xrefs for WP-2.3].",
        "",
        "## Source directories and expected units",
        "",
        "[inferred: one expected unit per distinct observed `.c` path under `code/`. Each",
        "top-level directory is a candidate case-sensitive symdb module. Use its recovered",
        "spelling as the CSV stem and remove the extension from the full module-relative",
        "path, including the module prefix, to get the qualified unit ID].",
        "",
        "[observed: compare the recovered directories below with the Engine bullet in the",
        "[README](../../README.md). `Project/` is represented in the inventory by the",
        "`VisualStudio/Win/EN` PDB path].",
        "",
        "| Module | Expected units | Recovered subtree or example | README comparison |",
        "| --- | ---: | --- | --- |",
    ]
    for module, units in modules.items():
        unit, offset, section = units[0]
        comparison = "Listed"
        if module == "Memory_Card":
            comparison = "Mentioned under LL. The path places it beside LL"
        elif module not in README_MODULES:
            comparison = "Additional top-level directory"
        lines.append(f"| `{module}/` | {len(units)} | "
                     f"[observed: `{unit}`, {section} file+0x{offset:08X}] | {comparison} |")
    missing = sorted(README_MODULES - modules.keys())
    if missing:
        lines.extend(["", "[unknown: no C paths recovered for " + ", ".join(missing) + "]."])

    lines.extend(["", "## Windows porting seam", "",
                  "[inferred: these `LL*_Win.c` paths identify candidate Windows backends",
                  "for WP-2.7, including the memory-card implementation].", ""])
    for relative, offset, section in backends:
        lines.append(f"- [observed: `{relative}`, {section} file+0x{offset:08X}]")
    lines.extend(["", "[unknown: per-section encryption coverage and the location of any",
                  "source paths still hidden by packing]."])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path, help="packed PE to read")
    parser.add_argument("--modules", action="store_true",
                        help="emit the ROTK module report instead of the path inventory")
    args = parser.parse_args()
    try:
        data = args.exe.read_bytes()
        paths = inventory(data)
    except (OSError, ValueError, struct.error) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")
    render = render_modules if args.modules else render_inventory
    print(render(paths, sha256(data).hexdigest()), end="")


if __name__ == "__main__":
    main()

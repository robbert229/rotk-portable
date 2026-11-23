#!/usr/bin/env python3
"""Cross-reference path strings in ROTK and its DLLs with a retail install."""

import argparse
import csv
import os
from pathlib import Path
import posixpath
import re
import struct
import sys
import tempfile

# Match tools/srcpaths.py's section attribution under isolated execution.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from srcpaths import location, pe_locations


DEFAULT_GAME_DIR = Path.home() / (
    "Games/lord-of-the-rings-the-return-of-the-king/drive_c/"
    "Program Files (x86)/EA GAMES/LOTR The Return of the King tm"
)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "re/corpus"
LISTINGS = {"filelist.txt", "common_filelist.txt", "manifest.txt", "input.ini"}
EXTENSIONS = set(
    "016 256 avi bik bmp cfg dat dll dmp exe fnt geo hlp ico inf ini jpeg jpg "
    "log mp3 ogg pac png sav scw snd str sys tdb tga tmp txw txt vid wav xml zip".split()
)
REF_COLUMNS = ("source", "offset", "section", "encoding", "string", "normalised",
               "kind", "resolves_to", "status")
LIST_COLUMNS = ("source", "line", "path", "type", "size_if_given", "present_in_install")

ASCII = re.compile(rb"[ -~]+")
WIDE = re.compile(rb"(?:[ -~]\x00)+")
PRINTF = re.compile(r"%(%|[-+ #0]*\d*(?:\.\d+)?(?:hh|ll|[hlL])?([scdiuoxX]))")
PART = r"[a-z0-9_~$*?+(). -]+"
PATH = re.compile(rf"(?:[a-z]:)?(?:/|//)?(?:{PART}/)*{PART}/?", re.ASCII | re.I)
EXTENSION = re.compile(r"\.(?:[a-z][a-z0-9]{0,7}|[0-9]{3}|\*)$", re.ASCII | re.I)
ROOTED = re.compile(r"(?i)[a-z]:[/\\]|[/\\]eathirdperson[/\\]")
PREFIXED_FORMAT = re.compile(r"^[^a-z0-9_./\\%]+(?=%)", re.ASCII | re.I)
# Avoid retaining arbitrary prose from binaries as a filename with spaces.
SPACED_PART = re.compile(r"[a-z0-9_~$*?+().-]+(?: [a-z0-9_~$*?+().-]+){0,11}",
                         re.ASCII | re.I)


def normalise(path):
    return posixpath.normpath(path.replace("\\", "/").casefold())


def kind_for(raw, extensions, directories):
    if len(raw) > 260 or raw != raw.strip() or "://" in raw:
        return None
    candidate = PRINTF.sub("placeholder", raw).replace("\\", "/")
    if not PATH.fullmatch(candidate):
        return None
    parts = re.sub(r"^[a-z]:", "", candidate, flags=re.I).strip("/").split("/")
    if not all(SPACED_PART.fullmatch(part) for part in parts):
        return None
    normal = normalise(raw)
    if candidate.endswith("/") or normal.lstrip("/") in directories:
        # A trailing separator alone is weak evidence in packed bytes.
        if normal.lstrip("/") in directories or (
            candidate.endswith("/") and re.search(r"[a-z]{3}", candidate, re.I)
            and (candidate.count("/") >= 2 or PRINTF.search(raw))
        ):
            return "pattern" if PRINTF.search(raw) or "*" in raw or "?" in raw else "directory"
        return None
    extension = EXTENSION.search(candidate)
    if extension is None:
        if "/" in candidate and normal.rsplit("/", 1)[0] in directories:
            return "pattern" if PRINTF.search(raw) or "*" in raw or "?" in raw else "directory"
        return None
    suffix = extension[0].lower()
    leaf = parts[-1]
    if " " in leaf and "/" not in candidate and suffix not in {".dll", ".exe"}:
        return None
    if "/" not in candidate and suffix[1:] not in extensions and suffix != ".*":
        return None
    if leaf == extension[0] or PRINTF.search(raw) or "*" in raw or "?" in raw:
        return "pattern"
    return "literal"


def binary_strings(data, extensions, directories):
    for encoding, regex, stride in (("ascii", ASCII, 1), ("utf-16le", WIDE, 2)):
        for match in regex.finditer(data):
            if data[match.end():match.end() + stride] != b"\0" * stride:
                continue
            raw = match[0].decode(encoding)
            # A printable byte from PE metadata can be attached to a build path.
            root = ROOTED.search(raw)
            prefix = PREFIXED_FORMAT.match(raw)
            start = root.start() if root else prefix.end() if prefix else 0
            kind = kind_for(raw[start:], extensions, directories)
            if kind:
                yield match.start() + start * stride, encoding, raw[start:], kind


def pattern_regex(path):
    chunks = []
    index = 0
    while index < len(path):
        field = PRINTF.match(path, index)
        if field:
            conversion = field[2]
            chunks.append({
                None: "%", "s": "[^/]*", "c": "[^/]", "d": "[+-]?[0-9]+",
                "i": "[+-]?[0-9]+", "u": "[0-9]+", "o": "[0-7]+", "x": "[0-9a-f]+",
            }[conversion])
            index = field.end()
            continue
        if path[index:index + 3] == "*.*" and path[index + 3:index + 4] in ("", "/"):
            # Windows wildcard *.* includes files without an extension.
            chunks.append("[^/]*")
            index += 3
            continue
        chunks.append({"*": "[^/]*", "?": "[^/]"}.get(path[index], re.escape(path[index])))
        index += 1
    return re.compile("".join(chunks))


def reference_keys(path, kind, names, *, binary=False):
    """Return matching normalised paths, preserving ambiguities."""
    if re.match(r"^[a-z]:|^//", path) or path == ".." or path.startswith("../"):
        return set()
    rooted = path.startswith("/")
    path = path.lstrip("/")
    if kind == "pattern" and re.fullmatch(r"\.[a-z0-9]+", path):
        path = "*" + path
    basename = binary and not rooted and "/" not in path
    candidates = {path}
    if binary and not rooted and "/" in path and not path.startswith("data/"):
        candidates.add(f"data/{path}")
    if kind == "pattern":
        patterns = [pattern_regex(candidate) for candidate in sorted(candidates)]
        return {name for name in names if any(
            pattern.fullmatch(name.rsplit("/", 1)[-1] if basename else name)
            for pattern in patterns
        )}
    if basename:
        return {name for name in names if name.rsplit("/", 1)[-1] == path}
    return candidates.intersection(names)


def listing_entries(source, path, extensions, directories):
    name = path.name.lower()
    data = path.read_bytes()
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    try:
        contents = data.decode(encoding)
    except UnicodeDecodeError:
        contents = data.decode("cp1252")
    for number, line in enumerate(contents.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith((";", "#")):
            continue
        size = ""
        if name == "input.ini":
            _, sep, value = line.partition("=")
            entry = value.strip().strip('"')
            kind = kind_for(entry, extensions, directories)
            if sep and kind:
                yield number, entry, "file" if kind == "literal" else kind, size, kind
            continue
        fields = next(csv.reader([line], skipinitialspace=True))
        if name.endswith("filelist.txt") and len(fields) >= 3:
            disc, entry_type, entry, *rest = fields
            if not disc.isdecimal() or not entry_type.isdecimal():
                raise ValueError(f"{source}:{number}: expected disc,type,path[,size]")
        else:
            entry, *rest = fields
            entry_type = None
        if rest:
            if len(rest) != 1 or not rest[0].strip().isdecimal():
                raise ValueError(f"{source}:{number}: expected a single byte size")
            size = rest[0].strip()
        entry = entry.strip()
        if not entry:
            raise ValueError(f"{source}:{number}: empty listing path")
        if PRINTF.search(entry) or "*" in entry or "?" in entry:
            kind = "pattern"
        elif entry.endswith(("/", "\\")) or normalise(entry) in directories:
            kind = "directory"
        else:
            kind = "literal"
        yield number, entry, entry_type or ("file" if kind == "literal" else kind), size, kind


def install_index(root):
    files, directories = {}, {}

    def fail(error):
        raise error

    for directory, subdirs, filenames in os.walk(root, onerror=fail):
        for name in sorted(subdirs + filenames):
            path = Path(directory) / name
            spelling = path.relative_to(root).as_posix()
            if path.is_dir():
                directories.setdefault(normalise(spelling), []).append(spelling)
            elif path.is_file():
                files.setdefault(normalise(spelling), []).append(spelling)
    return dict(sorted(files.items())), dict(sorted(directories.items()))


def inventory(root, exe):
    files, directories = install_index(root)
    if "rotk.exe" not in files:
        raise ValueError(f"ROTK.exe is missing from {root}")
    extensions = EXTENSIONS.union(
        suffix[1:] for name in files if (suffix := posixpath.splitext(name)[1])
    )
    listing_rows = []
    listed = {"literal": set(), "pattern": set(), "directory": set()}
    for paths in files.values():
        for source in paths:
            if source.rsplit("/", 1)[-1].lower() not in LISTINGS:
                continue
            for line, entry, entry_type, size, kind in listing_entries(
                source, root / source, extensions, directories
            ):
                path = normalise(entry)
                index = directories if kind == "directory" else files
                present = bool(reference_keys(path, kind, index))
                listing_rows.append((source, line, entry, entry_type, size,
                                     "yes" if present else "no"))
                listed[kind].add(path)

    binaries = [(source, root / source) for name, paths in files.items()
                if name.endswith(".dll") or (name == "rotk.exe" and exe is None)
                for source in paths]
    if exe is not None:
        binaries.append((exe.name, exe))
    ref_rows = []
    for source, path in binaries:
        data = path.read_bytes()
        try:
            layout = pe_locations(data)
        except (ValueError, struct.error) as error:
            raise ValueError(f"{source}: {error}") from error
        for offset, encoding, raw, kind in binary_strings(data, extensions, directories):
            section, _ = location(offset, layout)
            normal = normalise(raw)
            index = directories if kind == "directory" else files
            matches = reference_keys(normal, kind, index, binary=True)
            listed_kind = "literal" if kind == "pattern" else kind
            listing_only = reference_keys(normal, kind, listed[listed_kind], binary=True) - matches
            if kind == "pattern" and normal in listed["pattern"]:
                if not matches:
                    listing_only.add(normal)
            resolved = [spelling for key in sorted(matches) for spelling in sorted(index[key])]
            status = f"pattern-matches-{len(resolved)}" if kind == "pattern" else (
                "found" if resolved else "missing"
            )
            resolved.extend(f"listed:{key}" for key in sorted(listing_only))
            ref_rows.append((source, f"0x{offset:08X}", section, encoding, raw, normal,
                             kind, "|".join(resolved), status))
    return sorted(ref_rows), sorted(listing_rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=os.environ.get("ROTK_GAME_DIR")
                        or DEFAULT_GAME_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--exe", type=Path, help="scan this PE in place of installed ROTK.exe")
    args = parser.parse_args()
    try:
        root = args.game_dir.resolve()
        output = args.output_dir.resolve()
        targets = [output / name for name in ("filerefs.csv", "listed_files.csv")]
        if output.is_relative_to(root) or any(path.resolve().is_relative_to(root) for path in targets):
            raise ValueError("output must be outside the retail install")
        ref_rows, listing_rows = inventory(root, args.exe)
        output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output) as scratch:
            for target, header, rows in zip(
                targets, (REF_COLUMNS, LIST_COLUMNS), (ref_rows, listing_rows)
            ):
                with (Path(scratch) / target.name).open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.writer(stream, lineterminator="\n")
                    writer.writerow(header)
                    writer.writerows(rows)
            for target in targets:
                (Path(scratch) / target.name).replace(target)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")


if __name__ == "__main__":
    main()

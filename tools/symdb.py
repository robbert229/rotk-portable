#!/usr/bin/env python3
"""Validate, format and export the ROTK symbol database."""

import argparse
from collections import Counter, defaultdict
import csv
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile

SYMBOLS = Path(__file__).resolve().parents[1] / "re" / "symbols"
COLUMNS = "address size name unit module kind signature status evidence".split()
KINDS = ("func", "data", "vtable", "lib")
STATUSES = ("auto", "named", "typed", "decomp", "verified", "nonmatching")
FUNCTIONS = ("func", "lib")
IMPLEMENTED = ("decomp", "verified", "nonmatching")
COMPONENT = r"[A-Za-z_][A-Za-z0-9_-]*"
UNIT = rf"{COMPONENT}(?:/{COMPONENT})+"
EVIDENCE = r"\[(?:observed|inferred|unknown): [^\[\]]+\]"
# C89/C99 keywords plus the MSVC 7.0 extensions that cl treats as reserved.
C_KEYWORDS = frozenset("""
    auto break case char const continue default do double else enum extern float
    for goto if inline int long register restrict return short signed sizeof static
    struct switch typedef union unsigned void volatile while _Bool _Complex _Imaginary
    __asm __based __cdecl __declspec __except __fastcall __finally __inline __int8
    __int16 __int32 __int64 __leave __stdcall __try
""".split())


def validate(row, path):
    address = row["address"]
    size = row["size"]
    name = row["name"]
    kind = row["kind"]
    status = row["status"]
    module = row["module"]
    unit = row["unit"]
    valid_address = re.fullmatch(r"0x[0-9A-Fa-f]{1,8}", address)
    if not valid_address or int(address, 16) < 0x400000:
        yield "address must be a 32-bit hex VA at or above 0x00400000"
    elif not re.fullmatch(r"0x[0-9A-Fa-f]{1,8}", size):
        yield "size must be a 32-bit hex byte count"
    elif int(address, 16) + max(1, int(size, 16)) > 2**32:
        yield "address range exceeds the 32-bit image"
    if not re.fullmatch(COMPONENT, module) or module != path.stem:
        yield "module must match the CSV filename stem"
    if (unit or status != "auto") and (
        not re.fullmatch(UNIT, unit) or unit.split("/", 1)[0] != module
    ):
        yield "unit must be a module-qualified path matching module"
    if kind not in KINDS:
        yield f"unknown kind {kind!r}"
    if path.stem.startswith("lib_") and kind != "lib":
        yield "lib_* files require kind=lib"
    if kind == "lib" and not path.stem.startswith("lib_"):
        yield "kind=lib requires a lib_* file"
    if status not in STATUSES:
        yield f"unknown status {status!r}"
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        yield "name must be a C identifier"
    elif name in C_KEYWORDS:
        yield f"name {name!r} is a C keyword"
    elif name.startswith("FUN_"):
        if status != "auto" or not re.fullmatch(r"FUN_[0-9A-F]{8}", name):
            yield "FUN_ placeholders require eight uppercase hex digits and status=auto"
        elif kind not in FUNCTIONS or (valid_address and int(name[4:], 16) != int(address, 16)):
            yield "FUN_ placeholder must identify the function VA"
    elif kind == "vtable" and not name.endswith("_vtbl"):
        yield "vtable names must end in _vtbl"
    if status in ("typed", *IMPLEMENTED) and not row["signature"]:
        yield f"status={status} requires a signature"
    if status in IMPLEMENTED and (kind not in FUNCTIONS or
                                  re.fullmatch(r"0x0+", size)):
        yield f"status={status} requires a function with a known size"
    evidence = row["evidence"]
    if (evidence or status != "auto") and not re.fullmatch(
        rf"{EVIDENCE}(?: +{EVIDENCE})*", evidence
    ):
        yield "evidence requires [observed: …], [inferred: …] or [unknown: …] tags"


def read_rows(path, errors):
    line = 1
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            if next(reader, None) != COLUMNS:
                errors.append(f"{path}:1: expected header {','.join(COLUMNS)}")
                return
            while True:
                line = reader.line_num + 1
                values = next(reader, None)
                if values is None:
                    break
                if len(values) != len(COLUMNS):
                    errors.append(f"{path}:{line}: expected {len(COLUMNS)} columns")
                    continue
                if any(value != value.strip() or any(ord(c) < 32 for c in value)
                       for value in values):
                    errors.append(f"{path}:{line}: fields must be trimmed single-line text")
                    continue
                row = dict(zip(COLUMNS, values))
                problems = list(validate(row, path))
                errors.extend(f"{path}:{line}: {problem}" for problem in problems)
                if not problems:
                    yield int(row["address"], 16), path, line, row
    except (OSError, UnicodeError, csv.Error) as error:
        errors.append(f"{path}:{line}: {error}")


def load(paths):
    errors = []
    entries = []
    for path in sorted(set(paths)):
        entries.extend(read_rows(path, errors))
    entries.sort(key=lambda entry: entry[:3])
    furthest_end = 0
    starts = {}
    names = {}
    for address, path, line, row in entries:
        location = f"{path}:{line}"
        if row["name"] in names:
            errors.append(f"{location}: duplicate name {row['name']!r} with {names[row['name']]}")
        else:
            names[row["name"]] = location
        if address in starts:
            errors.append(f"{path}:{line}: duplicate address with {starts[address]}")
        elif address < furthest_end:
            errors.append(f"{path}:{line}: overlapping range with {furthest_location}")
        starts.setdefault(address, location)
        end = address + max(1, int(row["size"], 16))
        if end > furthest_end:
            furthest_end = end
            furthest_location = location
        row["address"] = f"0x{address:08X}"
        row["size"] = f"0x{int(row['size'], 16):X}"
    return entries, errors


def write_csv(stream, columns, rows):
    writer = csv.DictWriter(stream, columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


def merge(paths, entries):
    by_path = defaultdict(list)
    for _, path, _, row in entries:
        by_path[path].append(row)
    for path in sorted(set(paths)):
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                write_csv(stream, COLUMNS, by_path[path])
                stream.close()
                temporary.chmod(path.stat().st_mode & 0o777)
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)


def stats(paths, rows):
    counts = {path.stem: Counter() for path in paths}
    total = Counter()
    for row in rows:
        counts[row["module"]][row["status"]] += 1
        total[row["status"]] += 1
    for label, counter in [*sorted(counts.items()), ("TOTAL", total)]:
        count = sum(counter.values())
        percentages = " ".join(
            f"{status}={100 * counter[status] / (count or 1):.1f}%" for status in STATUSES
        )
        print(f"{label} ({count}) {percentages}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("lint", "validate all selected module files together"),
        ("merge", "sort and format selected files in place"),
        ("stats", "report status percentages"),
        ("export-ghidra", "write Ghidra import CSV to stdout"),
        ("export-hooks", "write hook candidates CSV to stdout"),
    ):
        command = commands.add_parser(name, help=help_text, description=help_text)
        command.add_argument("files", nargs="*", type=Path, help="defaults to re/symbols/*.csv")
    args = parser.parse_args()
    paths = args.files or list(SYMBOLS.glob("*.csv"))
    entries, errors = load(paths)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    rows = [entry[3] for entry in entries]
    if args.command == "merge":
        try:
            merge(paths, entries)
        except OSError as error:
            print(error, file=sys.stderr)
            return 1
    elif args.command == "stats":
        stats(paths, rows)
    elif args.command == "export-ghidra":
        write_csv(sys.stdout, "address size name kind signature".split(), rows)
    elif args.command == "export-hooks":
        write_csv(sys.stdout, "address name signature enabled_by_default".split(), (
            dict(row, enabled_by_default="false") for row in rows
            if row["status"] in IMPLEMENTED
        ))
    return 0


if __name__ == "__main__":
    sys.exit(main())

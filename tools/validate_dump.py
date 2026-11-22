#!/usr/bin/env python3
"""Validate an unpacked ROTK PE or inspect generic PE structure."""

import argparse
from collections import Counter
from dataclasses import dataclass
import json
from math import log2
from pathlib import Path
import re
import struct

EXPECTED_DLLS = {
    "d3d8.dll", "dinput8.dll", "dsound.dll", "eax.dll",
    "divxmedialib.dll", "kernel32.dll", "user32.dll",
}
STUBS = {"stxt371", "stxt774", "        "}
REFERENCE_SIZE = 2_874_232
SIZE_TOLERANCE = 512 * 1024
ENTROPY_LIMIT = 7.5


@dataclass
class Section:
    name: str
    size: int
    rva: int
    raw_size: int
    offset: int

    def contains(self, rva):
        return self.rva <= rva < self.rva + (self.size or self.raw_size)


def require(condition, message):
    if not condition:
        raise ValueError(message)


class PE:
    def __init__(self, data):
        self.data = data
        require(len(data) >= 64 and data[:2] == b"MZ", "missing DOS header")
        pe, = struct.unpack_from("<I", data, 0x3c)
        require(64 <= pe <= len(data) - 24 and data[pe:pe + 4] == b"PE\0\0",
                "missing or truncated PE header")
        self.machine, count, _, _, _, size, flags = struct.unpack_from("<HHIIIHH", data, pe + 4)
        optional = pe + 24
        table = optional + size
        end = table + count * 40
        require(flags & 2 and 0 < count <= 96 and size >= 2 and end <= len(data),
                "invalid executable header or truncated section table")
        magic, = struct.unpack_from("<H", data, optional)
        require(magic in (0x10b, 0x20b), "expected PE32 or PE32+")
        self.pe32 = magic == 0x10b
        directory_start = 96 if self.pe32 else 112
        require(size >= directory_start, "truncated optional header")
        self.base, = struct.unpack_from("<I" if self.pe32 else "<Q", data,
                                        optional + (28 if self.pe32 else 24))
        self.entry, = struct.unpack_from("<I", data, optional + 16)
        alignment, file_alignment = struct.unpack_from("<II", data, optional + 32)
        self.image_size, self.headers = struct.unpack_from("<II", data, optional + 56)
        directories, = struct.unpack_from("<I", data, optional + directory_start - 4)
        require(directories <= (size - directory_start) // 8, "truncated data directories")
        self.directories = list(struct.iter_unpack(
            "<II", data[optional + directory_start:optional + directory_start + 8 * directories]
        ))
        require(alignment and file_alignment and end <= self.headers <= len(data)
                and self.headers <= self.image_size and self.image_size % alignment == 0,
                "invalid header size, image size or alignment")
        self.sections = []
        raw_ranges = []
        mapped_ranges = []
        for index in range(count):
            name, *fields = struct.unpack_from("<8s4I", data, table + index * 40)
            section = Section(name.rstrip(b"\0").decode("ascii", "backslashreplace"), *fields)
            self.sections.append(section)
            raw_end = section.offset + section.raw_size
            if section.raw_size:
                require(self.headers <= section.offset and raw_end <= len(data),
                        f"section {section.name!r} raw data outside file")
                raw_ranges.append((section.offset, raw_end))
            mapped_size = max(section.size, section.raw_size)
            if mapped_size:
                mapped_end = section.rva + mapped_size
                require(self.headers <= section.rva and section.rva % alignment == 0
                        and mapped_end <= self.image_size,
                        f"section {section.name!r} outside aligned image")
                mapped_ranges.append((section.rva, mapped_end))
        for ranges in (raw_ranges, mapped_ranges):
            ranges.sort()
            require(all(left[1] <= right[0] for left, right in zip(ranges, ranges[1:])),
                    "overlapping section ranges")
        require(not self.entry or any(section.contains(self.entry) for section in self.sections),
                "entry point outside mapped sections")

    def directory(self, index):
        return self.directories[index] if index < len(self.directories) else (0, 0)

    def backed(self, rva):
        if 0 <= rva < self.headers:
            return rva, self.headers
        for section in self.sections:
            delta = rva - section.rva
            if 0 <= delta < min(section.size or section.raw_size, section.raw_size):
                return (section.offset + delta,
                        section.offset + min(section.size or section.raw_size, section.raw_size))
        raise ValueError(f"RVA {rva:#x} has no file backing")

    def imports(self):
        rva, size = self.directory(1)
        if not (rva or size):
            return set(), []
        require(rva and size >= 20, "invalid import directory")
        offset, end = self.backed(rva)
        names = set()
        tables = []
        for cursor in range(offset, min(offset + size, end) - 19, 20):
            descriptor = struct.unpack_from("<5I", self.data, cursor)
            if not any(descriptor):
                return names, tables
            require(descriptor[3] and descriptor[4], "incomplete import descriptor")
            tables.append((descriptor[0] or descriptor[4], descriptor[4]))
            start, limit = self.backed(descriptor[3])
            stop = self.data.find(b"\0", start, limit)
            require(stop > start, "missing or unterminated import DLL name")
            names.add(self.data[start:stop].decode("ascii").lower())
        raise ValueError("missing import descriptor terminator")


def stub_references(pe, text, code, tables):
    stubs = [section for section in pe.sections if section.name in STUBS]
    counts = {"rel32": 0, "iat_indirect": 0}
    iat, iat_size = pe.directory(12)
    ranges = [(iat, iat_size)] if iat else []
    for lookup, first_thunk in tables:
        try:
            start, end = pe.backed(lookup)
        except ValueError:
            continue
        for offset in range(start, end - 3, 4):
            if pe.data[offset:offset + 4] == bytes(4):
                ranges.append((first_thunk, offset - start))
                break
    for match in re.finditer(rb"(?=[\xe8\xe9]|\xff[\x15\x25])", code):
        index = match.start()
        if code[index] != 0xff:
            if index + 5 <= len(code):
                displacement, = struct.unpack_from("<i", code, index + 1)
                target = (text.rva + index + 5 + displacement) & 0xffffffff
                counts["rel32"] += any(section.contains(target) for section in stubs)
        elif index + 6 <= len(code):
            address, = struct.unpack_from("<I", code, index + 2)
            slot = address - pe.base
            if any(start <= slot <= start + size - 4 and (slot - start) % 4 == 0
                   for start, size in ranges):
                try:
                    offset, end = pe.backed(slot)
                except ValueError:
                    continue
                if offset + 4 <= end:
                    target, = struct.unpack_from("<I", pe.data, offset)
                    counts["iat_indirect"] += any(
                        section.contains(target - pe.base) for section in stubs
                    )
    return counts


def validate(data, structural=False):
    checks = {}

    def check(name, passed, **details):
        checks[name] = {"ok": bool(passed), **details}

    try:
        pe = PE(data)
    except ValueError as error:
        check("pe", False, reason=str(error))
        return checks
    check("pe", True, image_size=pe.image_size)
    if structural:
        return checks

    x86 = pe.pe32 and pe.machine == 0x14c
    check("x86", x86)
    text_sections = [section for section in pe.sections if section.name == ".text"]
    text = text_sections[0] if len(text_sections) == 1 else None
    code = data[text.offset:text.offset + text.raw_size] if text else b""
    check("entry_in_text", text and 0 <= pe.entry - text.rva < len(code)
          and text.contains(pe.entry), entry_rva=f"{pe.entry:#x}")
    entropy = -sum((count / len(code)) * log2(count / len(code))
                   for count in Counter(code).values()) if code else None
    check("text_entropy", entropy is not None and entropy < ENTROPY_LIMIT,
          bits_per_byte=round(entropy, 4) if entropy is not None else None,
          exclusive_limit=ENTROPY_LIMIT)
    tables = []
    try:
        imports, tables = pe.imports()
        missing = EXPECTED_DLLS - imports
        check("imports", not missing, dlls=sorted(imports), missing=sorted(missing))
    except ValueError as error:
        check("imports", False, reason=str(error))
    if x86 and code:
        mapped_code = code[:text.size or text.raw_size]
        counts = stub_references(pe, text, mapped_code, tables)
        check("stub_references", True, total=sum(counts.values()), **counts)
    else:
        check("stub_references", False, reason="requires file-backed x86 .text")
    check("file_size", abs(len(data) - REFERENCE_SIZE) <= SIZE_TOLERANCE,
          bytes=len(data), reference_bytes=REFERENCE_SIZE, tolerance_bytes=SIZE_TOLERANCE)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structural", action="store_true", help="check generic PE structure only")
    parser.add_argument("exe", type=Path)
    args = parser.parse_args()
    try:
        checks = validate(args.exe.read_bytes(), args.structural)
    except OSError as error:
        checks = {"read": {"ok": False, "reason": str(error)}}
    passed = all(check["ok"] for check in checks.values())
    report = {"file": str(args.exe), "mode": "structural" if args.structural else "rotk",
              "ok": passed, "checks": checks}
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())

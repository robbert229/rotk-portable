#!/usr/bin/env python3
"""Catalogue on-disk PE metadata across the read-only ROTK installation."""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from hashlib import sha256
from math import log2
import os
from pathlib import Path
import struct
import sys
import tempfile
from uuid import UUID

if __package__:
    from . import richhdr
    from .corpus import DEFAULT_GAME_DIR
    from .validate_dump import PE, require
else:
    # Python isolated mode omits the script directory.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import richhdr
    from corpus import DEFAULT_GAME_DIR
    from validate_dump import PE, require


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "re/corpus"
VERSION_FIELDS = (
    "CompanyName", "FileDescription", "FileVersion", "ProductName",
    "ProductVersion", "OriginalFilename", "InternalName",
)
BINARY_FIELDS = (
    "path", "sha256", "size", "machine", "timestamp_utc", "linker_version",
    "os_version", "subsystem_version", "subsystem", "image_base", "entry_rva",
    "entry_section", "checksum_stored", "checksum_computed", "characteristics",
    "dll_characteristics", "section_count", "debug_directory", "codeview_format",
    "pdb_path", "pdb_guid", "pdb_timestamp", "pdb_age", *VERSION_FIELDS,
    "rich_status", "rich_key", "rich_checksum", "rich_record_only_checksum",
    "rich_records", "import_dlls", "import_function_counts", "delay_import_rva",
    "delay_import_size", "delay_import_dlls", "delay_import_function_counts",
    "export_dll_name", "export_count", "tls_present",
    "resource_types", "overlay_size", "evidence",
)
SECTION_FIELDS = (
    "path", "index", "name", "va", "vsize", "raw_off", "raw_size",
    "characteristics", "entropy", "evidence",
)
IMPORT_FIELDS = ("path", "dll", "function_or_ordinal", "kind", "evidence")
HIGH_BIT = 0x80000000


def list_field(values):
    """Keep list delimiters distinct from literal characters in values."""
    return ";".join(str(value).replace("%", "%25").replace(";", "%3B") for value in values)


def section_name(raw):
    return "".join(
        chr(byte) if 0x21 <= byte < 0x7f and byte != 0x5c else f"\\x{byte:02x}"
        for byte in raw.rstrip(b"\0")
    )


def timestamp(value):
    if value in (0, 0xffffffff):
        return ""
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")


def checksum(data, offset):
    """Sum little-endian words with the four checksum bytes treated as zero."""
    cleared = bytearray(data)
    cleared[offset:offset + 4] = bytes(4)
    even_end = len(data) & ~1
    total = sum(word for (word,) in struct.iter_unpack("<H", memoryview(cleared)[:even_end]))
    if len(data) != even_end:
        total += cleared[-1]
    while total >> 16:
        total = (total & 0xffff) + (total >> 16)
    return total + len(data)


def file_span(pe, rva, size):
    start, end = pe.backed(rva)
    require(size <= end - start, f"RVA {rva:#x} span exceeds file backing")
    return start


def c_string(data, start, end):
    stop = data.find(b"\0", start, end)
    require(stop >= start, "unterminated PE string")
    return data[start:stop].decode("utf-8", "backslashreplace")


def import_thunks(pe, rva, base):
    offset, end = pe.backed(rva)
    width, fmt = (4, "<I") if pe.pe32 else (8, "<Q")
    ordinal_flag = 1 << (width * 8 - 1)
    for cursor in range(offset, end - width + 1, width):
        value, = struct.unpack_from(fmt, pe.data, cursor)
        if value == 0:
            return
        if value & ordinal_flag:
            yield f"#{value & 0xffff}"
        else:
            start, limit = pe.backed(value - base)
            require(limit - start >= 3, "truncated import hint/name")
            yield c_string(pe.data, start + 2, limit)
    raise ValueError("unterminated import thunk table")


def imports(pe, *, delayed=False):
    rva, size = pe.directory(13 if delayed else 1)
    if not (rva or size):
        return
    descriptor = struct.Struct("<8I" if delayed else "<5I")
    require(rva and size >= descriptor.size, "invalid import directory")
    start = file_span(pe, rva, size)
    # The validator's import method separates labels from thunk tables.
    # Keep each name paired with its table, including delay-load descriptors.
    for cursor in range(start, start + size - descriptor.size + 1, descriptor.size):
        fields = descriptor.unpack_from(pe.data, cursor)
        if not any(fields):
            return
        if delayed:
            attributes, name, _, iat, lookup, _, _, _ = fields
            # Older delay-load descriptors store VAs.
            base = 0 if attributes & 1 else pe.base
        else:
            lookup, _, _, name, iat = fields
            base = 0
        require(name > base and iat > base and (lookup or iat) > base,
                "incomplete import descriptor")
        name -= base
        label = c_string(pe.data, *pe.backed(name))
        require(label, "empty import DLL name")
        yield label, list(import_thunks(pe, (lookup or iat) - base, base))
    raise ValueError("unterminated import descriptor table")


def exports(pe):
    rva, size = pe.directory(0)
    if not (rva or size):
        return "", 0
    require(rva and size >= 40, "invalid export directory")
    start = file_span(pe, rva, 40)
    name, _, count = struct.unpack_from("<III", pe.data, start + 12)
    require(name, "missing export module name")
    return c_string(pe.data, *pe.backed(name)), count


def debug_directory(pe):
    rva, size = pe.directory(6)
    if not (rva or size):
        return
    require(rva and size and size % 28 == 0, "invalid debug directory")
    start = file_span(pe, rva, size)
    for cursor in range(start, start + size, 28):
        kind, length, address, offset = struct.unpack_from("<4I", pe.data, cursor + 12)
        if length and not offset:
            require(address, "debug entry lacks a payload address")
            offset = file_span(pe, address, length)
        require(not length or length <= len(pe.data) - offset, "truncated debug payload")
        codeview = None
        if kind == 2 and length >= 4:
            signature = pe.data[offset:offset + 4]
            if signature == b"RSDS":
                require(length >= 25, "truncated RSDS record")
                guid, age = struct.unpack_from("<16sI", pe.data, offset + 4)
                path = c_string(pe.data, offset + 24, offset + length)
                codeview = ("RSDS", path, str(UUID(bytes_le=guid)), "", age)
            elif signature == b"NB10":
                require(length >= 17, "truncated NB10 record")
                stamp, age = struct.unpack_from("<II", pe.data, offset + 8)
                path = c_string(pe.data, offset + 16, offset + length)
                codeview = ("NB10", path, "", hex(stamp), age)
        yield f"{kind}@{offset:#x}/{length}", codeview


def version_blocks(data, start, end):
    """Yield key, type, value and child bounds for sibling version blocks."""
    while start < end:
        require(end - start >= 6, "truncated version block header")
        length, value_length, kind = struct.unpack_from("<HHH", data, start)
        stop = start + length
        require(length >= 8 and stop <= end, "invalid version block length")
        key_end = start + 6
        while key_end + 2 <= stop and data[key_end:key_end + 2] != b"\0\0":
            key_end += 2
        require(key_end + 2 <= stop, "unterminated version key")
        key = data[start + 6:key_end].decode("utf-16le")
        value_start = (key_end + 5) & ~3
        value_end = value_start + value_length * (2 if kind == 1 else 1)
        require(not value_length or value_end <= stop, "truncated version value")
        yield key, kind, data[value_start:value_end], (value_end + 3) & ~3, stop
        start = (stop + 3) & ~3


def version_fields(data):
    root, _, _, children, stop = next(version_blocks(data, 0, len(data)))
    require(root == "VS_VERSION_INFO", "invalid version resource root")
    for key, _, _, tables, info_end in version_blocks(data, children, stop):
        if key != "StringFileInfo":
            continue
        for _, _, _, strings, table_end in version_blocks(data, tables, info_end):
            for name, kind, value, _, _ in version_blocks(data, strings, table_end):
                if kind == 1 and name in VERSION_FIELDS:
                    yield name, value.decode("utf-16le").rstrip("\0")


def resources(pe):
    """Count language leaves by type and collect version string variants."""
    root, span = pe.directory(2)
    types = Counter()
    versions = {field: {} for field in VERSION_FIELDS}
    if not (root or span):
        return types, versions
    require(root and span >= 16, "invalid resource directory")

    def read(fmt, relative):
        size = struct.calcsize(fmt)
        require(relative + size <= span, "resource directory offset outside range")
        return struct.unpack_from(fmt, pe.data, file_span(pe, root + relative, size))

    def entries(relative):
        named, numeric = read("<HH", relative + 12)
        for index in range(named + numeric):
            yield read("<II", relative + 16 + index * 8)

    for name, names in entries(0):
        require(names & HIGH_BIT, "resource type lacks a name table")
        if name & HIGH_BIT:
            relative = name & ~HIGH_BIT
            length, = read("<H", relative)
            raw, = read(f"<{length * 2}s", relative + 2)
            label = f"name:{raw.decode('utf-16le')}"
        else:
            label = str(name)
        types[label] += 0
        for _, languages in entries(names & ~HIGH_BIT):
            require(languages & HIGH_BIT, "resource name lacks a language table")
            for _, leaf in entries(languages & ~HIGH_BIT):
                require(not leaf & HIGH_BIT, "resource language is not a data entry")
                data_rva, length = read("<II", leaf)
                types[label] += 1
                if name == 16 and length:
                    start = file_span(pe, data_rva, length)
                    for field, value in version_fields(pe.data[start:start + length]):
                        versions[field][value] = None
    return types, versions


def catalogue(path, data):
    pe = PE(data)
    rich = richhdr.decode(data)
    header = rich["pe_offset"]
    optional = header + 24
    stamp, = struct.unpack_from("<I", data, header + 8)
    opt_size, flags = struct.unpack_from("<HH", data, header + 20)
    os_major, os_minor, _, _, sub_major, sub_minor = struct.unpack_from("<6H", data, optional + 40)
    stored, subsystem, dll_flags = struct.unpack_from("<IHH", data, optional + 64)
    sections = []
    entry_section = ""
    image_end = pe.headers
    for index, section in enumerate(pe.sections):
        start = optional + opt_size + index * 40
        raw_name, characteristics = struct.unpack_from("<8s28xI", data, start)
        name = section_name(raw_name)
        if pe.entry and section.contains(pe.entry):
            entry_section = name
        raw_end = section.offset + section.raw_size
        entropy = ""
        if section.raw_size:
            image_end = max(image_end, raw_end)
            counts = Counter(data[section.offset:raw_end])
            entropy = f"{-sum((n / section.raw_size) * log2(n / section.raw_size)
                              for n in counts.values()) + 0.0:.4f}"
        sections.append((path, index, name, hex(section.rva), hex(section.size),
                         hex(section.offset), hex(section.raw_size), hex(characteristics),
                         entropy, f"[observed: {path} file+{start:#x} section header and raw range]"))

    debug = list(debug_directory(pe))
    codeview = [record for _, record in debug if record is not None]
    import_rows = []
    import_counts = {}
    for kind in ("regular", "delay"):
        counts = Counter()
        for dll, functions in imports(pe, delayed=(kind == "delay")):
            counts[dll] += len(functions)
            evidence = f"[observed: {path} {kind} import descriptor and thunk]"
            import_rows.extend((path, dll, function, kind, evidence) for function in functions)
        import_counts[kind] = counts
    regular, delay = import_counts["regular"], import_counts["delay"]
    export_name, export_count = exports(pe)
    resource_types, versions = resources(pe)
    delay_rva, delay_size = pe.directory(13)
    row = dict(
        path=path, sha256=sha256(data).hexdigest(), size=len(data), machine=hex(pe.machine),
        timestamp_utc=timestamp(stamp), linker_version=f"{data[optional + 2]}.{data[optional + 3]:02d}",
        os_version=f"{os_major}.{os_minor}", subsystem_version=f"{sub_major}.{sub_minor}",
        subsystem=subsystem, image_base=hex(pe.base), entry_rva=hex(pe.entry),
        entry_section=entry_section, checksum_stored=hex(stored),
        checksum_computed=hex(checksum(data, optional + 64)), characteristics=hex(flags),
        dll_characteristics=hex(dll_flags), section_count=len(sections),
        debug_directory=list_field(entry for entry, _ in debug),
        **{key: list_field(record[index] for record in codeview)
           for index, key in enumerate(("codeview_format", "pdb_path", "pdb_guid",
                                        "pdb_timestamp", "pdb_age"))},
        **{field: list_field(versions[field]) for field in VERSION_FIELDS},
        rich_status=rich["status"],
        **{f"rich_{key}": hex(rich[key]) if key in rich else ""
           for key in ("key", "checksum", "record_only_checksum")},
        rich_records=list_field(f"{item['prodid']}/{item['build']}/{item['count']}"
                                for item in rich["entries"]),
        import_dlls=list_field(regular), import_function_counts=list_field(regular.values()),
        delay_import_rva=hex(delay_rva), delay_import_size=delay_size,
        delay_import_dlls=list_field(delay), delay_import_function_counts=list_field(delay.values()),
        export_dll_name=export_name, export_count=export_count, tls_present=int(bool(pe.directory(9)[0])),
        resource_types=list_field(f"{kind}={count}" for kind, count in resource_types.items()),
        overlay_size=len(data) - image_end,
        evidence=f"[observed: {path} file+{header:#x} PE headers, directories and file ranges]",
    )
    return row, sections, import_rows


def pe_files(root):
    def fail(error):
        raise error

    for directory, _, files in os.walk(root, onerror=fail):
        for filename in files:
            path = Path(directory) / filename
            if not path.is_file():
                continue
            with path.open("rb") as source:
                dos = source.read(64)
                if len(dos) < 64 or not dos.startswith(b"MZ"):
                    continue
                offset, = struct.unpack_from("<I", dos, 0x3c)
                if offset >= 64:
                    source.seek(offset)
                    if source.read(4) == b"PE\0\0":
                        yield path


def write_catalogue(root, destination):
    prefix = next((path.parent for path in root.parents if path.name == "drive_c"), root)
    require(not destination.is_relative_to(prefix), "catalogue destination is inside the game prefix")
    require(root.is_dir(), f"game directory does not exist: {root}")
    binaries, sections, import_rows = [], [], []
    for path in sorted(pe_files(root), key=lambda path: path.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        try:
            binary, image_sections, image_imports = catalogue(relative, path.read_bytes())
        except (ValueError, struct.error) as error:
            raise ValueError(f"{relative}: {error}") from error
        binaries.append(binary)
        sections.extend(image_sections)
        import_rows.extend(image_imports)
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination) as temporary:
        for name, fields, rows in (
            ("binaries.csv", BINARY_FIELDS, ([row[field] for field in BINARY_FIELDS] for row in binaries)),
            ("pe_sections.csv", SECTION_FIELDS, sections),
            ("pe_imports.csv", IMPORT_FIELDS, import_rows),
        ):
            with (Path(temporary) / name).open("w", encoding="utf-8", newline="") as output:
                writer = csv.writer(output, lineterminator="\n")
                writer.writerow(fields)
                writer.writerows(rows)
        for path in sorted(Path(temporary).iterdir()):
            path.replace(destination / path.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="directory for the three CSVs")
    args = parser.parse_args()
    root = Path(os.environ.get("ROTK_GAME_DIR") or DEFAULT_GAME_DIR).resolve()
    try:
        write_catalogue(root, args.output_dir.resolve())
    except (OSError, ValueError) as error:
        parser.exit(1, f"pecat: {error}\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Index structural metadata for non-PE install rows in the ROTK manifest."""

import argparse
import codecs
import csv
import hashlib
import mmap
import os
from pathlib import Path
import re
import struct
import sys
from tempfile import TemporaryDirectory
from urllib.parse import quote
from xml.etree import ElementTree

# Also support direct execution with python3 -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import DEFAULT_GAME_DIR, MANIFEST
from geo2obj import parse_geo
from scwdump import dump_cots, dump_lrtc
from txw2png import parse_txw

KEY_FIELDS = ("container", "width", "height", "zone_count", "bank_count", "frame_count",
              "fps", "duration_seconds", "mesh_count", "texture_count", "element_count",
              "line_count", "section_count", "encoding")
SCW_FIELDS = ("container", "u32_04_unknown", "reserved_words", "header_size", "toc_bytes",
              "toc_version", "toc_count", "chunk_count", "zone_count", "missing_zone_count",
              "bank_count", "other_igc_count", "other_record_count", "toc_gap", "llif_offset",
              "llif_size", "chain_contiguous", "chain_end", "bytes_after_chain", "record_names",
              "record_kinds", "record_offsets", "record_sizes", "embedded_doc_names",
              "nested_lrtc_offsets", "chunks", "cohs_index", "walk_end")
AVI_FIELDS = ("riff_size", "bytes_after_riff", "stream_count", "declared_stream_count", "fourcc",
              "codec", "width", "height", "frame_count", "main_header_frame_count", "rate",
              "scale", "fps", "duration_seconds", "has_audio", "has_index", "index_types")
EVIDENCE = {
    "SCW": "SCW header and COTS TOC/RVWS or LRTC chunk walk from header_size",
    "AVI": "RIFF AVI header, hdrl/avih, strl/strh and strf, idx1 or indx chunk",
    "XML": "XML element tree",
    "INI": "physical lines and bracketed section headers",
    "TXT": "physical lines and bracketed section headers",
    "GEO": "MOEG header, vertex bounds and index count",
    "TXW": "TXW header and TXHE entries",
}


def identifier(name):
    """Limit binary strings to short structural identifiers."""
    if name and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", name):
        return name
    return ""


def joined(values):
    return "|".join(str(value) for value in values)


def scw_metadata(data, name):
    magic = data[:4]
    if magic == b"LRTC":
        scene = dump_lrtc(data, name)
        chunks = scene["chunks"]
        return dict(
            container="LRTC", header_size=scene["header_size"],
            reserved_words=joined(struct.unpack_from("<4I", data, 8)),
            chunk_count=len(chunks), chunks=joined(
                f"{chunk['tag']}@{chunk['offset']}:{chunk['size']}" for chunk in chunks
            ), cohs_index=joined(
                f"{item['tag']}@{item['off']}:{item['v1']}"
                for chunk in chunks if chunk["tag"] == "COHS" for item in chunk.get("index", [])
            ), walk_end=scene["covered"].split()[0],
        )
    if magic != b"COTS":
        raise ValueError("unrecognized SCW magic")

    scene = dump_cots(data, name, scan_bytes=0)
    if "error" in scene:
        raise ValueError(scene["error"])
    records = scene["records"]
    names = [identifier(record["name"]) for record in records]
    if not all(names):
        raise ValueError("invalid TOC record name")
    embedded = [record["embedded"] or {} if int(record["f4"], 16) else {}
                for record in records]
    chunks = ["COTS"]
    llif_offset = 0x18 + scene["toc_chunk_size"] - 4
    metadata = {}
    if data[llif_offset:llif_offset + 4] == b"LLIF":
        chunks.append("LLIF")
        metadata.update(llif_offset=hex(llif_offset),
                        llif_size=struct.unpack_from("<I", data, llif_offset + 4)[0])
    zones = sum(label.startswith("zone_") and int(record["f4"], 16) > 0
                for label, record in zip(names, records))
    missing = sum(label.startswith("_missingZone_") for label in names)
    igc = sum(label.startswith("igc_") for label in names)
    # Some bank identifiers have no underscore immediately before "bank".
    banks = sum(label.startswith("igc_") and label.endswith("bank") for label in names)
    chain = scene["offset_chain"]
    return dict(
        metadata, container="COTS", u32_04_unknown=scene["u32_04_unknown"],
        reserved_words=joined(struct.unpack_from("<2I", data, 8)
                              + struct.unpack_from("<2I", data, 0x20)),
        toc_bytes=scene["toc_chunk_size"], toc_version=scene["version"],
        toc_count=scene["entry_count"], chunk_count=len(chunks), chunks=joined(chunks),
        zone_count=zones, missing_zone_count=missing, bank_count=banks,
        other_igc_count=igc - banks, other_record_count=len(records) - 1 - zones - missing - igc,
        toc_gap=scene["toc_arith"]["gap"], chain_contiguous=int(chain["contiguous"]),
        chain_end=chain["end"], bytes_after_chain=len(data) - int(chain["end"], 16),
        record_names=joined(names), record_kinds=joined(record["kind"] for record in records),
        record_offsets=joined(record["f3"] for record in records),
        record_sizes=joined(record["f4"] for record in records),
        embedded_doc_names=joined(",".join(filter(None, map(identifier, item.get("elif_names", []))))
                                  if item.get("tag_at_f3") == "RVWS" else "" for item in embedded),
        nested_lrtc_offsets=joined(item.get("nested_LRTC_at", "") for item in embedded),
    )


def riff_chunks(data, start, end):
    while start < end:
        if end - start < 8:
            raise ValueError("truncated RIFF chunk header")
        tag, size = struct.unpack_from("<4sI", data, start)
        payload = start + 8
        next_chunk = payload + size + (size & 1)
        if next_chunk > end:
            raise ValueError("RIFF chunk exceeds its parent")
        yield tag, payload, payload + size
        start = next_chunk


def avi_metadata(data):
    if data[:4] != b"RIFF" or data[8:12] != b"AVI ":
        raise ValueError("expected RIFF AVI")
    riff_size = struct.unpack_from("<I", data, 4)[0]
    riff_end = riff_size + 8
    if not 12 <= riff_end <= len(data):
        raise ValueError("RIFF size exceeds file or omits form type")

    header = None
    streams = []
    indexes = set()
    for tag, start, end in riff_chunks(data, 12, riff_end):
        if tag == b"idx1":
            indexes.add("idx1")
        if tag != b"LIST" or end - start < 4 or data[start:start + 4] != b"hdrl":
            continue
        for tag, start, end in riff_chunks(data, start + 4, end):
            if tag == b"avih" and end - start >= 40:
                header = struct.unpack_from("<10I", data, start)
            if tag != b"LIST" or end - start < 4 or data[start:start + 4] != b"strl":
                continue
            stream = {}
            for tag, start, end in riff_chunks(data, start + 4, end):
                if tag == b"strh" and end - start >= 36:
                    stream["type"], stream["handler"] = struct.unpack_from("<4s4s", data, start)
                    stream["scale"], stream["rate"], _, stream["length"] = struct.unpack_from(
                        "<4I", data, start + 20)
                if tag == b"strf" and end - start >= 20:
                    stream["format"] = struct.unpack_from("<Iii4x4s", data, start)
                if tag == b"indx":
                    indexes.add("indx")
            if "type" not in stream:
                raise ValueError("AVI stream has no complete strh")
            streams.append(stream)

    video = next((stream for stream in streams if stream["type"] == b"vids"), None)
    if header is None or video is None:
        raise ValueError("AVI has no complete main header or video stream")
    width, height = header[8:10]
    fourcc = video["handler"].decode("ascii").rstrip()
    compression = ""
    if video.get("format", (0,))[0] >= 40:
        _, width, height, code = video["format"]
        compression = "BI_RGB" if code == b"\0" * 4 else code.decode("ascii").rstrip()
    rate, scale, frames = video["rate"], video["scale"], video["length"]
    return dict(
        riff_size=riff_size, bytes_after_riff=len(data) - riff_end, stream_count=len(streams),
        declared_stream_count=header[6], fourcc=fourcc, codec=compression or fourcc, width=width,
        height=abs(height), frame_count=frames, main_header_frame_count=header[4],
        rate=rate, scale=scale, fps=f"{rate / scale:.6f}" if rate and scale else "",
        duration_seconds=f"{frames * scale / rate:.6f}" if rate and scale else "",
        has_audio=int(any(stream["type"] == b"auds" for stream in streams)),
        has_index=int(bool(indexes)), index_types=joined(sorted(indexes)),
    )


def text_metadata(data, name):
    for bom, encoding in ((codecs.BOM_UTF32_LE, "utf-32"), (codecs.BOM_UTF32_BE, "utf-32"),
                          (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16"),
                          (codecs.BOM_UTF8, "utf-8-sig")):
        if data.startswith(bom):
            break
    else:
        encoding = "ascii" if data.isascii() else "utf-8"
    try:
        content = data.decode(encoding)
    except UnicodeDecodeError:
        if encoding != "utf-8":
            raise
        encoding = "cp1252-compatible"
        content = data.decode("cp1252")
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines[-1] == "":
        lines.pop()
    metadata = dict(encoding=encoding, line_count=len(lines),
                    section_count=sum(bool(re.fullmatch(r"\s*\[[^\]\[]+\]\s*(?:;.*)?", line))
                                      for line in lines))
    if name == "filelist.txt":
        pairs = set()
        for line in lines:
            match = re.match(r"^([0-9]{1,9}),([0-9]{1,9}),", line)
            if match:
                pairs.add(tuple(map(int, match.groups())))
        metadata["integer_pairs"] = joined(f"{first},{second}" for first, second in sorted(pairs))
    return metadata


def geo_metadata(data):
    mesh = parse_geo(data)
    metadata = {key: value for key, value in mesh.items() if key not in ("vertices", "indices")}
    if mesh["vertices"]:
        metadata["xyz_extent"] = joined(
            f"{max(axis) - min(axis):.6f}" for axis in zip(*(v[:3] for v in mesh["vertices"]))
        )
    return metadata


def txw_metadata(data):
    version, declared, entries, _ = parse_txw(data)
    offset = 8
    mip_field = []
    while offset + 8 <= len(data):
        tag, size = struct.unpack_from("<4sI", data, offset)
        offset += 8
        if offset + size > len(data):
            raise ValueError("TXW chunk exceeds file")
        if tag == b"TXHE":
            mip_field = [data[offset + i * 80 + 0x41] for i in range(len(entries))]
            break
        offset += size
    dimensions = {(entry["width"], entry["height"]) for entry in entries}
    metadata = dict(version=version, texture_count=len(entries), declared_texture_count=declared,
                    textures=joined(f"{identifier(e['name'])}:{e['width']}x{e['height']}:{e['format']}"
                                    for e in entries), txhe_41_unknown=joined(mip_field))
    if len(dimensions) == 1:
        metadata["width"], metadata["height"] = next(iter(dimensions))
    return metadata


def asset_metadata(path, data):
    suffix = Path(path).suffix.upper().lstrip(".")
    if suffix == "SCW":
        return suffix, scw_metadata(data, path)
    if suffix == "AVI":
        return suffix, avi_metadata(data)
    if suffix == "XML":
        root = ElementTree.fromstring(data[:])
        return suffix, dict(root=root.tag, element_count=sum(1 for _ in root.iter()),
                            child_tags=joined(sorted({child.tag for child in root})))
    if suffix in ("INI", "TXT"):
        return suffix, text_metadata(data[:], Path(path).name)
    if suffix == "GEO":
        return suffix, geo_metadata(data)
    if suffix == "TXW":
        return suffix, txw_metadata(data)
    if data[:2] == b"BM":
        suffix = "BMP"
    return suffix or "OTHER", dict(reason="no structural parser for this format")


def is_pe(data):
    if len(data) < 64 or data[:2] != b"MZ":
        return False
    offset = struct.unpack_from("<I", data, 0x3C)[0]
    return data[offset:offset + 4] == b"PE\0\0"


def manifest_assets(root, manifest):
    with manifest.open(encoding="utf-8", newline="") as source:
        rows = sorted((row for row in csv.DictReader(source) if row["origin"] == "install"),
                      key=lambda row: row["path"])
    seen = set()
    for row in rows:
        path = row["path"]
        source = (root / path).resolve()
        if path in seen or Path(path).as_posix() != path or Path(path).is_absolute() or (
            ".." in Path(path).parts or root not in source.parents
        ):
            raise ValueError(f"duplicate or invalid install path: {path}")
        seen.add(path)
        try:
            with source.open("rb") as file:
                size = os.fstat(file.fileno()).st_size
                if size != int(row["size"]):
                    raise ValueError("file size differs from manifest")
                if size:
                    with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as data:
                        if hashlib.sha256(data).hexdigest() != row["sha256"]:
                            raise ValueError("SHA-256 differs from manifest")
                        if is_pe(data):
                            continue
                        kind, metadata = asset_metadata(path, data)
                else:
                    if hashlib.sha256(b"").hexdigest() != row["sha256"]:
                        raise ValueError("SHA-256 differs from manifest")
                    kind, metadata = asset_metadata(path, b"")
        except (ValueError, struct.error, ElementTree.ParseError, LookupError) as error:
            raise ValueError(f"{path}: {error}") from error
        evidence = f"[observed: {path} — {EVIDENCE.get(kind, 'file size and SHA-256')}]"
        yield dict(path=path, sha256=row["sha256"], format=kind, size=size, evidence=evidence), metadata


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_index(root, manifest, destination):
    root = root.resolve()
    destination = destination.resolve()
    prefix = next((parent.parent for parent in root.parents if parent.name == "drive_c"), root)
    if not root.is_dir():
        raise ValueError(f"game directory does not exist: {root}")
    if destination == prefix or prefix in destination.parents:
        raise ValueError("index destination is inside the game prefix")
    common = []
    detail = {"SCW": [], "AVI": []}
    for identity, metadata in manifest_assets(root, manifest):
        kind = identity["format"]
        keys = {key: metadata[key] for key in KEY_FIELDS if key in metadata}
        extra = {key: value for key, value in metadata.items()
                 if key not in keys and (kind not in detail or key in ("riff_size", "toc_count",
                                                                      "chunk_count", "fourcc"))}
        # Escape delimiters so details can be parsed independently of CSV quoting.
        common.append(dict(identity, **keys, details=";".join(
            f"{key}={quote(str(value), safe='|,:@')}" for key, value in sorted(extra.items())
        )))
        if kind in detail:
            detail[kind].append(dict(identity, **metadata))
    fields = ("path", "sha256", "format", "size")
    destination.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination) as staging:
        staging = Path(staging)
        write_csv(staging / "assets.csv", fields + KEY_FIELDS + ("details", "evidence"), common)
        for kind, columns in (("SCW", SCW_FIELDS), ("AVI", AVI_FIELDS)):
            write_csv(staging / f"assets_{kind.lower()}.csv", fields + columns + ("evidence",),
                      detail[kind])
        for path in sorted(staging.iterdir()):
            path.replace(destination / path.name)
    return len(common)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=os.environ.get("ROTK_GAME_DIR")
                        or DEFAULT_GAME_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=MANIFEST.parent)
    args = parser.parse_args()
    try:
        count = write_index(args.game_dir, args.manifest, args.out_dir)
    except (ValueError, OSError) as error:
        parser.exit(1, f"assetindex: {error}\n")
    print(f"Indexed {count} non-PE install files across three CSVs.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""scwdump.py — container-level dumper for ROTK (LotR: ROTK, EA 2003) .scw scene files.

Spec: docs/formats/scw.md. Dependency-free (stdlib only).

COTS missions contain a TOC and bounded RVWS regions. LRTC scenes contain
a header followed by a stream of size-prefixed chunks.

Usage:
    python3 tools/scwdump.py FILE.scw [--json] [--scan-bytes N]
    python3 tools/scwdump.py [GAME_DIR] --chunks-csv | --summary-csv
"""
import argparse
import collections
import csv
import json
import mmap
from pathlib import Path
import re
import struct
import sys

RES_TAGS = {  # aligned resource-record tags seen in COTS bodies (observed)
    "tadR", "gfxt", "zfxt", "RDHS", "SNPR", "TADS", "ONOS", "pmas",
    "xtrc", "COHS", "LLIF", "CNYS", "DAPS",
}


def read_cstring(d, o):
    e = d.find(b"\x00", o)
    if e < 0:
        return None
    return d[o:e].decode("latin1")


def dump_cots(d, name, scan_bytes):
    out = {"file": name, "kind": "COTS", "magic": "COTS"}
    (out["u32_04_unknown"],) = struct.unpack_from("<I", d, 4)
    if d[0x10:0x14] != b"COTS":
        out["error"] = "missing inner COTS at +0x10"
        return out
    (chunk_size,) = struct.unpack_from("<I", d, 0x14)
    (count,) = struct.unpack_from("<I", d, 0x18)
    (version,) = struct.unpack_from("<I", d, 0x1C)
    out.update({"toc_chunk_size": chunk_size, "entry_count": count, "version": version})
    # TOC header record at +0x28: (kind=count, name_off='initial_load', f3, f4)
    hk, hno, hf3, hf4 = struct.unpack_from("<4I", d, 0x28)
    (pool_off,) = struct.unpack_from("<I", d, 0x2C)
    recs = []
    recs.append({"i": 0, "kind": f"hdr({hk})", "name": read_cstring(d, hno),
                 "name_off": hex(hno), "f3": hex(hf3), "f4": hex(hf4)})
    o = 0x38
    for i in range(1, count):
        kind, noff, f3, f4 = struct.unpack_from("<4I", d, o)
        recs.append({"i": i, "kind": kind, "name": read_cstring(d, noff),
                     "name_off": hex(noff), "f3": hex(f3), "f4": hex(f4)})
        o += 16
    out["records"] = recs
    out["toc_arith"] = {"table_end": hex(o), "pool_off": hex(pool_off),
                        "gap": hex(pool_off - o)}
    pool = []
    p = pool_off
    end = 0x10 + 8 + chunk_size
    while p < end:
        s = read_cstring(d, p)
        if s is None:
            break
        if s:
            pool.append(s)
        p += len(s) + 1
    out["names"] = pool
    out["pool_end"] = hex(p)
    # offset/size chain arithmetic (observed): f3 = offset, f4 = size, contiguous
    chain_ok = True
    vals = [(int(r["f3"], 16), int(r["f4"], 16)) for r in recs]
    for k in range(len(vals) - 1):
        if vals[k][0] + vals[k][1] != vals[k + 1][0]:
            chain_ok = False
            break
    out["offset_chain"] = {"contiguous": chain_ok,
                           "first_off": hex(vals[0][0]),
                           "end": hex(vals[-1][0] + vals[-1][1])}
    # each record's f3 offset has been observed to start an embedded document:
    # 'RVWS' directory (u32 size) with 'ELIF' name entries, then a nested 'LRTC' stream
    for r in recs:
        fo = int(r["f3"], 16)
        info = {}
        if fo + 8 <= len(d) and all(32 <= c < 127 for c in d[fo:fo + 4]):
            info["tag_at_f3"] = d[fo:fo + 4].decode("latin1")
            (dsz,) = struct.unpack_from("<I", d, fo + 4)
            info["dir_size"] = hex(dsz)
            # scan the directory for ELIF (="FILE") names
            names = []
            q = fo + 8
            stop = min(fo + 8 + dsz, fo + 0x200)
            while q + 4 <= stop:
                if d[q:q + 4] == b"ELIF":
                    nm = read_cstring(d, q + 4)
                    if nm:
                        names.append(nm)
                    q += 4
                else:
                    q += 4
            if names:
                info["elif_names"] = names[:8]
            for cand in range(fo + 8, min(fo + 8 + max(dsz, 0x40), len(d) - 4), 4):
                if d[cand:cand + 4] == b"LRTC":
                    info["nested_LRTC_at"] = hex(cand)
                    break
        r["embedded"] = info or None
    # reconcile: report where the LLIF chunk starts relative to TOC/pool end
    llif = d.find(b"LLIF", 0x40, min(len(d), 0x40000))
    if llif >= 0:
        (sz,) = struct.unpack_from("<I", d, llif + 4)
        out["LLIF"] = {"offset": hex(llif), "size": sz,
                       "toc_declared_end": hex(0x10 + 8 + chunk_size)}
    # aligned record-tag census (top of file, cheap heuristic)
    region = d[:min(len(d), scan_bytes)]
    tags = collections.Counter()
    for mt in re.finditer(rb"[A-Za-z_]{4}", region):
        if mt.start() % 4 == 0:
            t = mt.group().decode()
            if t in RES_TAGS:
                tags[t] += 1
    out["tag_census_first_%dKB" % (len(region) // 1024)] = dict(tags.most_common(20))
    return out


PAGE_SIZE = 0x10000
STREAM_TAGS = {b"COHS", b"ONOS", b"DDAP", b"LLIF"}


def walk_chunks(d, start, end):
    """Return complete chunks and the first unparsed offset, within [start, end)."""
    chunks = []
    p = start
    while p < end:
        raw_tag = d[p:min(p + 4, end)]
        tag = raw_tag.decode("ascii", errors="replace")
        size = None
        if raw_tag not in STREAM_TAGS:
            note = "unrecognized stream tag"
        elif raw_tag == b"LLIF" and p % PAGE_SIZE == PAGE_SIZE - 4 and end - p >= 4:
            size = 4  # tag-only filler in the last word of a page
            note = None
        elif end - p < 8:
            note = "truncated chunk header"
        else:
            (size,) = struct.unpack_from("<I", d, p + 4)
            if size < 8 or size % 4 or size > end - p:
                note = "invalid chunk size for containing region"
            elif raw_tag == b"LLIF" and (p + size) % PAGE_SIZE:
                note = "LLIF does not end at a page boundary"
            elif raw_tag == b"DDAP" and (p + size) % 64:
                note = "DDAP does not end at a 64-byte boundary"
            elif raw_tag in (b"LLIF", b"DDAP") and any(d[p + 8:p + size]):
                note = "nonzero filler payload"
            elif raw_tag in (b"COHS", b"ONOS") and (
                size < 20 or size > PAGE_SIZE - p % PAGE_SIZE
            ):
                note = "resource chunk lacks a payload tag or crosses a page boundary"
            else:
                note = None
        if note:
            stop = {"offset": hex(p), "tag": tag, "note": note}
            if size is not None:
                stop["size"] = size
            return chunks, p, stop

        entry = {"offset": hex(p), "tag": tag, "size": size, "reversed": tag[::-1]}
        if raw_tag in (b"COHS", b"ONOS"):
            entry["payload_tag"] = d[p + 16:p + 20].decode("ascii", errors="replace")
            # RDHS starts with two tagged words. Later bytes can contain inline data.
            if entry["payload_tag"] == "RDHS" and size >= 32:
                entry["index"] = []
                for q in (p + 16, p + 24):
                    identifier, value = struct.unpack_from("<4sI", d, q)
                    entry["index"].append({
                        "tag": identifier.decode("ascii", errors="replace"),
                        "v1": hex(value), "off": hex(q),
                    })
        chunks.append(entry)
        p += size
    return chunks, p, None


def lrtc_header_size(d, start, end):
    if end - start < 8 or d[start:start + 4] != b"LRTC":
        raise ValueError("missing or truncated LRTC header")
    (size,) = struct.unpack_from("<I", d, start + 4)
    if size < 8 or size % 4 or size > end - start:
        raise ValueError("invalid LRTC header size")
    return size


def dump_lrtc(d, name):
    out = {"file": name, "kind": "LRTC", "magic": "LRTC"}
    try:
        hdr_size = lrtc_header_size(d, 0, len(d))
    except ValueError as error:
        out["error"] = str(error)
        return out
    chunks, end, stop = walk_chunks(d, hdr_size, len(d))
    out.update(header_size=hdr_size, chunks=chunks, covered=f"{end:#x} / {len(d):#x}")
    if stop:
        out["stopped_at"] = stop
    return out


def stream_rows(d, start, end, parent):
    chunks, _, stop = walk_chunks(d, start, end)
    if stop:
        raise ValueError(f"at {stop['offset']} ({stop['tag']!r}): {stop['note']}")
    for i, chunk in enumerate(chunks):
        tag = chunk["tag"]
        if "payload_tag" in chunk:
            notes = f"payload tag {chunk['payload_tag']}"
        elif tag == "LLIF" and chunk["size"] == 4:
            notes = "tag-only page filler"
        else:
            notes = "zero-filled payload"
        yield chunk["offset"], tag, chunk["size"], i, hex(parent), notes


def inventory_rows(d, name):
    if d[:4] == b"LRTC":
        header_size = lrtc_header_size(d, 0, len(d))
        yield "0x0", "LRTC", header_size, 0, "", "header"
        yield from stream_rows(d, header_size, len(d), 0)
        return
    if d[:4] != b"COTS":
        raise ValueError("unknown SCW magic")

    scene = dump_cots(d, name, scan_bytes=0)
    if "error" in scene:
        raise ValueError(scene["error"])
    if not scene["offset_chain"]["contiguous"]:
        raise ValueError("COTS TOC regions are not contiguous")
    toc_offset = 0x10
    llif = toc_offset + 4 + scene["toc_chunk_size"]
    if d[llif:llif + 4] != b"LLIF":
        raise ValueError("missing COTS LLIF")
    llif_size = struct.unpack_from("<I", d, llif + 4)[0]
    if llif + llif_size != int(scene["records"][0]["f3"], 16):
        raise ValueError("COTS LLIF does not reach first TOC region")
    yield "0x0", "COTS", toc_offset, 0, "", "header"
    yield hex(toc_offset), "COTS", llif - toc_offset, 0, "0x0", "inner TOC including name pool"
    yield hex(llif), "LLIF", llif_size, 1, "0x0", "before first TOC region"
    for record in scene["records"]:
        start, size = (int(record[key], 16) for key in ("f3", "f4"))
        if not size:
            continue
        end = start + size
        if size < 8 or end > len(d) or d[start:start + 4] != b"RVWS":
            raise ValueError(f"invalid RVWS region at {start:#x}")
        directory_size = struct.unpack_from("<I", d, start + 4)[0]
        if not 8 <= directory_size <= size or directory_size % 4:
            raise ValueError(f"invalid RVWS size at {start:#x}")
        p = start + directory_size
        yield hex(start), "RVWS", directory_size, record["i"], hex(toc_offset), "TOC region header"
        if d[p:min(p + 4, end)] == b"LRTC":
            header_size = lrtc_header_size(d, p, end)
            yield hex(p), "LRTC", header_size, 0, hex(start), "embedded header"
            yield from stream_rows(d, p + header_size, end, p)
        else:
            yield from stream_rows(d, p, end, start)


CHUNK_FIELDS = ("path", "offset", "tag", "size", "index", "parent", "notes")
CHUNK_TAGS = ("COTS", "LRTC", "RVWS", "COHS", "ONOS", "DDAP", "LLIF")
SUMMARY_FIELDS = ("path", "container", *CHUNK_TAGS, "max_depth", "walked_to_eof",
                  "leftover_bytes")


def summary_row(data, name, rows):
    counts = collections.Counter()
    depths = {"": -1}
    end = 0
    for offset, tag, size, _, parent, _ in rows:
        counts[tag] += 1
        depths[offset] = depths[parent] + 1
        end = max(end, int(offset, 16) + size)
    return (name, data[:4].decode("ascii"), *(counts[tag] for tag in CHUNK_TAGS),
            max(depths.values()), "yes" if end == len(data) else "no", len(data) - end)


def write_chunk_csv(game_dir, output, *, summary=False):
    files = sorted(path for path in (game_dir / "Data").rglob("*")
                   if path.suffix.lower() == ".scw" and path.is_file())
    if not files:
        raise ValueError(f"no SCW files beneath {game_dir / 'Data'}")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(SUMMARY_FIELDS if summary else CHUNK_FIELDS)
    for path in files:
        name = path.relative_to(game_dir).as_posix()
        try:
            with path.open("rb") as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as d:
                rows = inventory_rows(d, name)
                if summary:
                    writer.writerow(summary_row(d, name, rows))
                else:
                    writer.writerows((name, *row) for row in rows)
        except (ValueError, struct.error, OSError) as error:
            raise ValueError(f"{name}: {error}") from error


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scw", nargs="?")
    output = ap.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true")
    output.add_argument("--chunks-csv", action="store_true",
                        help="inventory all SCWs beneath the given game directory")
    output.add_argument("--summary-csv", action="store_true",
                        help="summarize chunk counts and coverage for each installed SCW")
    ap.add_argument("--scan-bytes", type=int, default=0x200000)
    a = ap.parse_args()
    if a.chunks_csv or a.summary_csv:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from corpus import game_dir

        root = Path(a.scw).expanduser() if a.scw else game_dir()
        try:
            write_chunk_csv(root, sys.stdout, summary=a.summary_csv)
        except ValueError as error:
            ap.exit(1, f"scwdump: {error}\n")
        return
    if a.scw is None:
        ap.error("a scene file is required outside CSV mode")
    d = Path(a.scw).read_bytes()
    magic = d[:4]
    if magic == b"COTS":
        res = dump_cots(d, a.scw, a.scan_bytes)
    elif magic == b"LRTC":
        res = dump_lrtc(d, a.scw)
    else:
        print(f"{a.scw}: unknown magic {magic!r}", file=sys.stderr)
        sys.exit(1)
    if a.json:
        print(json.dumps(res, indent=2))
        return
    print(f"== {res['file']} [{res['kind']}] {len(d):,} bytes ==")
    if res.get("error"):
        print(f"{res['file']}: {res['error']}", file=sys.stderr)
        sys.exit(1)
    if res["kind"] == "COTS":
        print(f"  u32@0x04 (unknown)      : {res['u32_04_unknown']}")
        print(f"  TOC chunk size          : {res['toc_chunk_size']}")
        print(f"  entries                 : {res['entry_count']}")
        for r in res["records"]:
            print(f"    [{r['i']:2d}] kind={r['kind']:<3} name={r['name']!r:<28} f3={r['f3']} f4={r['f4']}")
        if "LLIF" in res:
            print(f"  LLIF @ {res['LLIF']['offset']} size {res['LLIF']['size']:,} "
                  f"(TOC declared end {res['LLIF']['toc_declared_end']})")
        print(f"  TOC arithmetic        : table_end={res['toc_arith']['table_end']} "
              f"pool_off={res['toc_arith']['pool_off']} gap={res['toc_arith']['gap']}")
        oc = res["offset_chain"]
        print(f"  offset/size chain     : contiguous={oc['contiguous']} "
              f"span {oc['first_off']}..{oc['end']}")
        print(f"  tag census              : {res.get([k for k in res if k.startswith('tag_census')][0])}")
    else:
        print(f"  header size {res['header_size']}")
        for c in res["chunks"]:
            payload = f" payload {c['payload_tag']}" if "payload_tag" in c else ""
            print(f"    chunk {c['tag']} @{c['offset']} size {c['size']:,}"
                  f" (='{c['reversed']}'){payload}")
            for it in c.get("index", []):
                print(f"        idx {it['tag']} {it['v1']} @{it['off']}")
        if "stopped_at" in res:
            print(f"  walk stopped at {res['stopped_at']['offset']} tag "
                  f"{res['stopped_at']['tag']}: {res['stopped_at']['note']}")
        print(f"  walk covered {res['covered']}")


if __name__ == "__main__":
    main()

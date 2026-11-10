#!/usr/bin/env python3
"""scwdump.py — container-level dumper for ROTK (LotR: ROTK, EA 2003) .scw scene files.

Spec: docs/formats/scw.md. Dependency-free (stdlib only).

Two container families are observed on disk:
  * COTS — per-mission scenes (Data/Game/<lvl>/<lvl>NN.scw), header 'COTS':
      +0x00 char[4] 'COTS'
      +0x04 u32     unknown global (308 fro03 / 0x2cc osg01 / 0x1a0 pel02)
      +0x08 16B     zeros
      +0x20 char[4] 'COTS' ; +0x24 u32 chunk size S (covers TOC + string pool)
      +0x28 TOC: (count+1) x 16-byte records:
            u32 kind, u32 name_off, u32 f3, u32 f4   (f3/f4: unknown)
          record 0 = 'initial_load' (kind field = entry count, see spec);
          zone records kind 1/2, igc audio-bank records kind 3 (observed);
          followed by the NUL-separated name pool up to +0x20+8+S.
      then 'LLIF' chunk, zone payloads (tadR/gfxt/RDHS/TADS/ONOS/… records).
  * LRTC — global/boot scenes (GlobScen.scw, LoadOnce.scw), header 'LRTC':
      +0x00 char[4] 'LRTC' ; +0x04 u32 header size (0x18 observed)
      then top-level chunks: char[4] tag + u32 size + payload
      (observed tags: CNYS, COHS, RDHS, SNPR, TADS, DAPS, ONOS, …)

Usage:
    python3 tools/scwdump.py FILE.scw [--json] [--scan-bytes N]
"""
import argparse
import collections
import json
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


def dump_lrtc(d, name):
    out = {"file": name, "kind": "LRTC", "magic": "LRTC"}
    (hdr_size,) = struct.unpack_from("<I", d, 4)
    out["header_size"] = hdr_size
    chunks = []
    p = hdr_size
    while p + 8 <= len(d) and len(chunks) < 400:
        tag = d[p:p + 4]
        if not re.fullmatch(rb"[A-Za-z_]{4}", tag):
            break
        (sz,) = struct.unpack_from("<I", d, p + 4)
        if sz > len(d) - p:
            out["stopped_at"] = {"offset": hex(p), "tag": tag.decode(), "size": sz,
                                 "note": "size exceeds EOF — LRTC sub-TOC structure not fully "
                                         "decoded (see spec, Unknowns)"}
            break
        t = tag.decode()
        entry = {"offset": hex(p), "tag": t, "size": sz,
                 "reversed": t[::-1]}
        if t == "COHS" and sz >= 8:  # nested index: (tag, u32) pairs
            inner = []
            q = p + 8
            while q + 8 <= p + 8 + sz:
                it = d[q:q + 4]
                if re.fullmatch(rb"[A-Za-z_]{4}", it):
                    (v1,) = struct.unpack_from("<I", d, q + 4)
                    inner.append({"tag": it.decode(), "v1": hex(v1), "off": hex(q)})
                    q += 8
                else:
                    q += 4
            entry["index"] = inner[:40]
        chunks.append(entry)
        p += 8 + sz
        p = (p + 15) & ~15  # chunks observed padded to 16
    out["chunks"] = chunks
    out["covered"] = hex(p) + " / " + hex(len(d))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scw")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--scan-bytes", type=int, default=0x200000)
    a = ap.parse_args()
    d = open(a.scw, "rb").read()
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
            print(f"    chunk {c['tag']} @{c['offset']} size {c['size']:,}"
                  + (f" (='{c['reversed']}')" if c.get("reversed") else ""))
            for it in c.get("index", [])[:12]:
                print(f"        idx {it['tag']} {it['v1']} @{it['off']}")
        if "stopped_at" in res:
            print(f"  walk stopped at {res['stopped_at']['offset']} tag "
                  f"{res['stopped_at']['tag']}: {res['stopped_at']['note']}")
        print(f"  walk covered {res['covered']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""txw2png.py — extract textures from ROTK (LotR: ROTK, EA 2003) .txw files to PNG.

Format: docs/formats/geo-txw.md (TXW container). Dependency-free (stdlib only).

Usage:
    python3 tools/txw2png.py Ring.txw [-o out_dir] [--list]

Container (observed on Ring.txw):
    +0x00  u32 magic 'TXW ' ; +0x04 u32 version (=528)
    then chunks: char[4] type, u32 size, payload
      HEAD (8 B)  — global header; u16 texture_count observed == 2 at +0x02
      TXHE (80*N) — one 80-byte entry per texture:
          +0x00 char[8]  name            [observed: "ringglos", "ring"]
          +0x08 u32      data_offset     [observed: 0, 0x4000 — relative to TXDA payload]
          +0x0C u16      block_count     [observed: 1024/512 == payload/16 for fmt 2/1]
          +0x0E u16      (0xffff)        [unknown]
          +0x10 u32      (0x40000)       [unknown]
          +0x38 u16      width           [observed: 256]
          +0x3A u16      height          [observed: 64]
          +0x3C u8      format           [observed: 2 → 16 B/block (DXT3),
                                                 1 → 8 B/block (DXT1)] [inferred family]
          +0x3D..+0x48 misc u8/u32       [unknown]
      CLHE (0)    — palette header, empty on sample            [unknown]
      TXDA        — raw block data for all entries              [observed]
      CLDA (0)    — palette data, empty on sample               [unknown]
"""
import argparse
import os
import struct
import sys
import zlib


# ---------------------------------------------------------------- DXT decode
def _unpack565(c):
    return ((c >> 11) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31)


def _block_endpoints(c0, c1, dxt1):
    r0, g0, b0 = _unpack565(c0)
    r1, g1, b1 = _unpack565(c1)
    pal = [(r0, g0, b0, 255), (r1, g1, b1, 255)]
    two = [(2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3]
    one = [(2 * r1 + r0) // 3, (2 * g1 + g0) // 3, (2 * b1 + b0) // 3]
    if dxt1 and c0 <= c1:
        pal += [tuple(two) + (255,), tuple(one) + (0,)]  # 3-colour + transparent
    else:
        pal += [tuple(two) + (255,), tuple(one) + (255,)]
    return pal


def _decode_block(blk, dxt1, fourcc_alpha):
    """Return 16 RGBA tuples (row-major 4x4). blk: >=12 (DXT1) / >=16 (DXT3/5) bytes."""
    if dxt1:
        c0, c1 = struct.unpack_from("<HH", blk, 0)
        pal = _block_endpoints(c0, c1, True)
        alph = [255] * 16
        bits = struct.unpack_from("<I", blk, 4)[0]
        idxs = [(bits >> (2 * i)) & 3 for i in range(16)]
    elif fourcc_alpha == "DXT3":
        a = blk[0:8]
        alph = [(((a[i // 2] >> (4 * (i % 2))) & 0xF) * 17) for i in range(16)]
        c0, c1 = struct.unpack_from("<HH", blk, 8)
        pal = _block_endpoints(c0, c1, False)
        bits = struct.unpack_from("<I", blk, 12)[0]
        idxs = [(bits >> (2 * i)) & 3 for i in range(16)]
    else:  # DXT5
        a0, a1 = blk[0], blk[1]
        if a0 > a1:
            pal8 = [a0, a1, (6 * a0 + 1 * a1) // 7, (5 * a0 + 2 * a1) // 7,
                    (4 * a0 + 3 * a1) // 7, (3 * a0 + 4 * a1) // 7,
                    (2 * a0 + 5 * a1) // 7, (1 * a0 + 6 * a1) // 7]
        else:
            pal8 = [a0, a1, (4 * a0 + 1 * a1) // 5, (3 * a0 + 2 * a1) // 5,
                    (2 * a0 + 3 * a1) // 5, (1 * a0 + 4 * a1) // 5, 0, 255]
        abits = int.from_bytes(blk[2:8], "little")
        alph = [pal8[(abits >> (3 * i)) & 7] for i in range(16)]
        c0, c1 = struct.unpack_from("<HH", blk, 8)
        pal = _block_endpoints(c0, c1, False)
        bits = struct.unpack_from("<I", blk, 12)[0]
        idxs = [(bits >> (2 * i)) & 3 for i in range(16)]
    out = []
    for i in range(16):
        r, g, b, _ = pal[idxs[i]]
        out.append((r, g, b, alph[i]))
    return out


# ------------------------------------------------------------------ PNG save
def save_png(path, w, h, rgba):
    raw = b"".join(b"\x00" + b"".join(bytes(p[x * 4:x * 4 + 4]) for x in range(w))
                   for p in (rgba[y * w * 4:(y + 1) * w * 4] for y in range(h)))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    open(path, "wb").write(png)


FMT = {1: ("DXT1", 8), 2: ("DXT3", 16), 5: ("DXT5", 16)}  # id → (codec, bytes/block) [1,2 observed; 5 inferred]


def parse_txw(data):
    if data[:4] != b"TXW ":
        raise ValueError(f"bad magic {data[:4]!r}")
    (version,) = struct.unpack_from("<I", data, 4)
    chunks = {}
    p = 8
    while p + 8 <= len(data):
        ck = data[p:p + 4]
        (sz,) = struct.unpack_from("<I", data, p + 4)
        chunks.setdefault(ck, []).append(data[p + 8:p + 8 + sz])
        p += 8 + sz
    head = chunks.get(b"HEAD", [b""])[0]
    count = struct.unpack_from("<H", head, 2)[0] if len(head) >= 4 else 0
    entries = []
    if b"TXHE" in chunks:
        he = chunks[b"TXHE"][0]
        n = len(he) // 80
        count = count or n
        for i in range(n):
            e = he[i * 80:(i + 1) * 80]
            name = e[0:8].split(b"\x00")[0].decode("latin1")
            off, blocks, w, h, fmt = (struct.unpack_from("<I", e, 8)[0],
                                      struct.unpack_from("<H", e, 12)[0],
                                      struct.unpack_from("<H", e, 56)[0],
                                      struct.unpack_from("<H", e, 58)[0],
                                      e[60])
            entries.append(dict(index=i, name=name, offset=off, blocks=blocks,
                                width=w, height=h, format=fmt))
    txda = chunks.get(b"TXDA", [b""])[0]
    if len(chunks.get(b"TXDA", [])) > 1:
        print("warning: multiple TXDA chunks — using first", file=sys.stderr)
    return version, count, entries, txda


def decode_entry(e, txda):
    if e["format"] not in FMT:
        raise ValueError(f"texture {e['name']}: unknown format id {e['format']}")
    fourcc, bs = FMT[e["format"]]
    w, h = e["width"], e["height"]
    need = ((w + 3) // 4) * ((h + 3) // 4) * bs
    blob = txda[e["offset"]:e["offset"] + need]
    if len(blob) < need:
        raise ValueError(f"texture {e['name']}: TXDA truncated ({len(blob)}<{need})")
    blob += b"\x00" * 16  # slack so DXT1's 16-byte over-read of the last block is safe
    img = bytearray(w * h * 4)
    bw, bh = (w + 3) // 4, (h + 3) // 4
    for by in range(bh):
        for bx in range(bw):
            base = (by * bw + bx) * bs
            blk = blob[base:base + 16]
            px = _decode_block(blk, fourcc == "DXT1", fourcc)
            for k, (r, g, b, a) in enumerate(px):
                x, y = bx * 4 + k % 4, by * 4 + k // 4
                if x < w and y < h:
                    o = (y * w + x) * 4
                    img[o:o + 4] = bytes((r, g, b, a))
    return bytes(img)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("txw")
    ap.add_argument("-o", "--outdir", default=".")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    version, count, entries, txda = parse_txw(open(a.txw, "rb").read())
    print(f"{a.txw}: TXW version={version} count={count} textures={len(entries)} TXDA={len(txda)}B")
    for e in entries:
        fourcc = FMT.get(e["format"], ("?", 0))[0]
        print(f"  [{e['index']}] {e['name']!r} {e['width']}x{e['height']} fmt={e['format']}({fourcc}) "
              f"off=0x{e['offset']:x} blocks={e['blocks']}")
    if a.list:
        return
    os.makedirs(a.outdir, exist_ok=True)
    for e in entries:
        img = decode_entry(e, txda)
        out = os.path.join(a.outdir, f"{e['name'] or 'tex%d' % e['index']}.png")
        save_png(out, e["width"], e["height"], img)
        print(f"  wrote {out}")


if __name__ == "__main__":
    main()

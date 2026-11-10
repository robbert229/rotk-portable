#!/usr/bin/env python3
"""unpac.py -- list and extract members of EA ROTK install archives (data_N.pac).

The Return of the King (EA 2003) ships its game payload in zlib-compressed
install archives: data_1.pac (Disc 1), data_2.pac (Disc 2), data_3.pac
(PlayDisc).  The three packs form ONE continuous logical byte stream:

    [128-byte ASCII id header][block stream]

Each pack's block stream is a sequence of blocks:

    [u32 uncompressed_size] [u32 compressed_size] [data]

* data is a zlib stream (starts 78 9c) when compressed_size < 0x8000,
  or stored raw when compressed_size == 0x8000 (used for pre-compressed
  DivX .avi payloads).
* uncompressed_size is nominally 0x8000; the LAST block of a pack may
  inflate short.
* data_1's logical stream starts with the archive table of contents:

      u32 count
      count records:  path NUL-terminated ASCII
                      u8   attrs           (0x00 / 0x80 observed)
                      u48  FILETIME low    (100 ns since 1601, low 7 bytes;
                                            top byte always 0)
                      u32  size

  Immediately after the TOC, member files are concatenated in TOC order,
  raw and byte-identical to the installed files, with NO padding.
  Files may straddle pack boundaries (e.g. Game\\min\\min04.scw spans
  data_1/data_2, Movies\\isenfmv1.avi spans data_2/data_3).

* data_2 / data_3 have the same 128-byte header and block framing but NO
  TOC: their logical bytes simply continue the stream after data_1.

data_3 carries an unexplained 8-byte trailer after its final block.

Only files > 0 bytes appear as members; size==0 entries are directories.

Verified: all 83 members of the EN retail set extract byte-identical
(SHA-256) to the installed tree.  See docs/formats/pac.md.

Usage:
    python3 unpac.py list    data_1.pac [data_2.pac data_3.pac]
    python3 unpac.py info    data_1.pac [data_2.pac data_3.pac]
    python3 unpac.py extract data_1.pac [data_2.pac ...] [-o OUT] NAME [NAME ...]
    python3 unpac.py extract data_1.pac [data_2.pac ...] [-o OUT] --all

Stdlib only.
"""

import argparse
import json
import os
import struct
import sys
import zlib

MAGIC_LEN = 128
BLOCK_HDR_LEN = 8
NOMINAL_UNCOMPRESSED = 0x8000


class PacError(Exception):
    pass


class Pack:
    """One data_N.pac file: 128-byte id header + zlib block stream."""

    def __init__(self, path):
        self.path = path
        self._f = open(path, "rb")
        magic = self._f.read(MAGIC_LEN)
        if len(magic) < MAGIC_LEN or magic[:1] != b"x" or magic[127:128] != b"x":
            raise PacError(f"{path}: not a ROTK .pac (bad 128-byte id header)")
        self.magic = magic.decode("latin-1")
        self.blocks = self._scan_blocks()
        # block k -> (data_file_offset, compressed_size, declared_uncompressed)
        self._offsets = [0] * (len(self.blocks) + 1)  # logical offset of block k
        self._built = 0           # number of blocks whose true size is known
        self._cache = {}          # k -> inflated bytes (bounded)

    def _scan_blocks(self):
        f = self._f
        size = os.path.getsize(self.path)
        pos = MAGIC_LEN + 1  # 0x80 is a 0x00 pad byte; first block header at 0x81
        blocks = []
        while pos + BLOCK_HDR_LEN <= size:
            f.seek(pos)
            hdr = f.read(BLOCK_HDR_LEN)
            if len(hdr) < BLOCK_HDR_LEN:
                break
            u1, u2 = struct.unpack("<II", hdr)
            if u2 == 0 or pos + BLOCK_HDR_LEN + u2 > size:
                break  # trailing bytes (data_3 has an 8-byte trailer)
            blocks.append((pos + BLOCK_HDR_LEN, u2, u1))
            pos += BLOCK_HDR_LEN + u2
        self.trailer_len = size - pos
        return blocks

    def _inflate(self, k):
        data = self._cache.get(k)
        if data is not None:
            return data
        data_off, clen, u1 = self.blocks[k]
        self._f.seek(data_off)
        raw = self._f.read(clen)
        if u1 == NOMINAL_UNCOMPRESSED and clen == NOMINAL_UNCOMPRESSED:
            data = raw  # stored block
        elif raw[:2] == b"\x78\x9c":
            data = zlib.decompress(raw)
        else:
            data = raw
        if len(self._cache) > 2:
            self._cache = {k: data}
        else:
            self._cache[k] = data
        return data

    def _extend(self, lo, hi):
        """Ensure true sizes are known for blocks [lo, hi)."""
        for k in range(max(0, lo), min(hi, len(self.blocks))):
            if k >= self._built:
                self._offsets[k + 1] = self._offsets[k] + len(self._inflate(k))
                self._built = k + 1

    @property
    def logical_size(self):
        self._extend(0, len(self.blocks))
        return self._offsets[len(self.blocks)]

    def read_logical(self, start, length):
        if length <= 0:
            return b""
        # find first block covering `start`
        self._extend(0, len(self.blocks))
        out = bytearray()
        k = 0
        while k < len(self.blocks) and self._offsets[k + 1] <= start:
            k += 1
        while k < len(self.blocks) and len(out) < length:
            data = self._inflate(k)
            base = self._offsets[k]
            lo = max(0, start - base)
            hi = min(len(data), start + length - base)
            if hi > lo:
                out += data[lo:hi]
            k += 1
        if len(out) < length:
            raise PacError(
                f"{self.path}: logical stream ends at {self._offsets[-1]:#x}, "
                f"needed {start + length:#x}")
        return bytes(out[:length])


class Archive:
    """The concatenated logical stream of one or more packs (TOC from the first)."""

    def __init__(self, paths):
        if not paths:
            raise PacError("no packs given")
        self.packs = [Pack(p) for p in paths]
        self.cum = []
        total = 0
        for p in self.packs:
            self.cum.append(total)
            total += p.logical_size
        self.logical_size = total
        self.toc = self._parse_toc(self.packs[0])
        self.member_start = self.toc["end_offset"]
        self.members = self._plan()

    @staticmethod
    def _parse_toc(first_pack):
        head = first_pack.read_logical(0, 64 * 1024)
        (count,) = struct.unpack_from("<I", head, 0)
        p = 4
        entries = []
        for _ in range(count):
            e = head.index(b"\x00", p)
            name = head[p:e].decode("ascii", "replace")
            attrs = head[e + 1]
            filetime = int.from_bytes(head[e + 2:e + 9], "little")
            (size,) = struct.unpack_from("<I", head, e + 9)
            entries.append({
                "name": name,
                "attrs": attrs,
                "filetime_100ns_since_1601": filetime,
                "size": size,
                "is_dir": size == 0,
            })
            p = e + 13
        return {"count": count, "entries": entries, "end_offset": p}

    def _plan(self):
        members = []
        pos = self.member_start
        for ent in self.toc["entries"]:
            if ent["size"] == 0:
                continue
            members.append({**ent, "stream_offset": pos})
            pos += ent["size"]
        return members

    def read(self, start, length):
        out = bytearray()
        for i, pack in enumerate(self.packs):
            base = self.cum[i]
            end = base + pack.logical_size
            cur = start + len(out)
            if cur >= end:
                continue
            need = min(length - len(out), end - cur)
            out += pack.read_logical(cur - base, need)
            if len(out) >= length:
                break
        if len(out) < length:
            raise PacError(f"stream exhausted at {start + len(out):#x}")
        return bytes(out[:length])


def cmd_info(arc, args):
    for p in arc.packs:
        stored = sum(1 for _, c, u in p.blocks
                     if c == NOMINAL_UNCOMPRESSED and u == NOMINAL_UNCOMPRESSED)
        print(f"== {p.path}")
        print(f"  id header : {p.magic[:24]}...{p.magic[-8:]} (128 bytes, per-pack id)")
        print(f"  blocks    : {len(p.blocks)} (stored/raw: {stored})")
        extra = f", trailer: {p.trailer_len} bytes (unknown)" if p.trailer_len else ""
        print(f"  logical   : {p.logical_size:,} bytes{extra}")
    t = arc.toc
    dirs = sum(1 for e in t["entries"] if e["is_dir"])
    print(f"== TOC: {t['count']} entries ({dirs} dirs, {len(arc.members)} file "
          f"members), records end at {t['end_offset']:#x}")


def cmd_list(arc, args):
    if args.json:
        json.dump(arc.toc["entries"], sys.stdout, indent=1)
        print()
        return
    for m in arc.members:
        print(f"{m['stream_offset']:>12}  {m['size']:>11}  "
              f"{m['attrs']:#04x}  {m['name']}")


def _safe_relpath(name):
    return name.replace("\\", os.sep)


def cmd_extract(arc, args):
    outdir = args.output or "."
    wanted = [m["name"] for m in arc.members] if args.all else args.names
    by_name = {m["name"]: m for m in arc.members}
    by_name_ci = {m["name"].lower(): m for m in arc.members}
    rc = 0
    for name in wanted:
        m = by_name.get(name) or by_name_ci.get(name.lower())
        if m is None:
            print(f"unpac: no such member: {name}", file=sys.stderr)
            rc = 2
            continue
        dest = os.path.join(outdir, _safe_relpath(m["name"]))
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        tmp = dest + ".part"
        got = 0
        with open(tmp, "wb") as out:
            while got < m["size"]:
                chunk = arc.read(m["stream_offset"] + got,
                                 min(1 << 20, m["size"] - got))
                out.write(chunk)
                got += len(chunk)
        os.replace(tmp, dest)
        print(f"unpac: {m['name']} -> {dest} ({got:,} bytes)")
    sys.exit(rc)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="list/extract EA ROTK data_N.pac install archives")
    ap.add_argument("command", choices=["list", "info", "extract"])
    ap.add_argument("pacs", nargs="+",
                    help="data_N.pac files in order (TOC is read from the first)")
    ap.add_argument("-o", "--output", help="output directory (extract)")
    ap.add_argument("--all", action="store_true", help="extract every member")
    ap.add_argument("--json", action="store_true", help="dump TOC as JSON (list)")
    ap.add_argument("names", nargs="*", help="member paths, e.g. Game\\fro\\Ring.txw")
    args = ap.parse_args(argv)

    arc = Archive(args.pacs)
    if args.command == "info":
        cmd_info(arc, args)
    elif args.command == "list":
        cmd_list(arc, args)
    else:
        if not args.all and not args.names:
            ap.error("extract needs member names or --all")
        cmd_extract(arc, args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""geo2obj.py — convert ROTK (LotR: ROTK, EA 2003) .GEO meshes to Wavefront OBJ.

Format: docs/formats/geo-txw.md (MOEG geometry). Dependency-free (stdlib only).

Usage:
    python3 tools/geo2obj.py Ring.GEO [-o out.obj] [--json]

Header layout (observed on Ring.GEO, all offsets from file start):
    +0x00  u32 magic 'MOEG'
    +0x04  u32 version (=1)                     [observed]
    +0x08  u32 mesh_count (=1 on sample)        [observed value; semantics inferred]
    +0x0C  u32 vertex_count (=784)              [observed: 0x10+N*0x20 lands on idx table]
    +0x10  vertex array, stride 0x20:
              f32[3] position                   [observed: bbox +-13.11 matches ring mesh]
              f32[3] normal (unit length)       [observed: min/max norm 1.0000]
              f32[2] uv                         [observed: values tile beyond 0..1]
    +vertex_end  u32 index_count (=2112=3*704)  [observed: exact file-size arithmetic]
    +0x04  u16[index_count] triangle list       [observed: max index = vertex_count-1]
"""
import argparse
import json
import struct
import sys


def parse_geo(data: bytes):
    if len(data) < 16:
        raise ValueError("file too small for MOEG header")
    if data[:4] != b"MOEG":
        raise ValueError(f"bad magic {data[:4]!r} (expected b'MOEG')")
    version, mesh_count, vertex_count = struct.unpack_from("<3I", data, 4)
    verts = []
    off = 0x10
    for _ in range(vertex_count):
        px, py, pz, nx, ny, nz, u, v = struct.unpack_from("<8f", data, off)
        verts.append((px, py, pz, nx, ny, nz, u, v))
        off += 0x20
    (index_count,) = struct.unpack_from("<I", data, off)
    off += 4
    if off + index_count * 2 != len(data):
        print(
            f"warning: index table size mismatch: off {off} + 2*{index_count} "
            f"!= file size {len(data)}",
            file=sys.stderr,
        )
    indices = list(struct.unpack_from("<%dH" % index_count, data, off))
    if indices and max(indices) >= vertex_count:
        raise ValueError("index out of range — misparsed")
    return {
        "version": version,
        "mesh_count": mesh_count,
        "vertex_count": vertex_count,
        "index_count": index_count,
        "triangle_count": index_count // 3,
        "vertices": verts,
        "indices": indices,
    }


def to_obj(m, name="rotk_geo"):
    lines = [
        f"# {name} — exported by geo2obj.py (ROTK MOEG format)",
        f"# verts={m['vertex_count']} tris={m['triangle_count']}",
        "o " + name,
    ]
    for x, y, z, nx, ny, nz, u, v in m["vertices"]:
        lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
    for x, y, z, nx, ny, nz, u, v in m["vertices"]:
        lines.append(f"vn {nx:.6f} {ny:.6f} {nz:.6f}")
    for x, y, z, nx, ny, nz, u, v in m["vertices"]:
        lines.append(f"vt {u:.6f} {1.0 - v:.6f}")  # flip V for OBJ convention
    for i in range(0, m["index_count"] - 2, 3):
        a, b, c = m["indices"][i], m["indices"][i + 1], m["indices"][i + 2]
        lines.append(f"f {a+1}//{a+1} {b+1}//{b+1} {c+1}//{c+1}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("geo")
    ap.add_argument("-o", "--out")
    ap.add_argument("--json", action="store_true", help="print parsed header stats as JSON")
    a = ap.parse_args()
    data = open(a.geo, "rb").read()
    m = parse_geo(data)
    if a.json:
        print(json.dumps({k: v for k, v in m.items() if k not in ("vertices", "indices")}, indent=2))
        return
    out = a.out or (a.geo.rsplit(".", 1)[0] + ".obj")
    open(out, "w").write(to_obj(m, name=__import__("os").path.basename(a.geo)))
    print(
        f"{a.geo}: v={m['vertex_count']} n={m['vertex_count']} t={m['triangle_count']} "
        f"(index_count={m['index_count']}) -> {out}"
    )


if __name__ == "__main__":
    main()

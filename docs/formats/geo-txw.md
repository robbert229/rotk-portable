# `.GEO` (MOEG) geometry and `.txw` (TXW) texture container

C7/D7 deliverable ([spec](../deliverables.md)). Reverse-engineered from the only samples on
disk — `Data/Game/fro/Ring.GEO` (29,332 B) and `Data/Game/fro/Ring.txw` (24,800 B) — both
extractable with [`tools/unpac.py`](../../tools/unpac.py) and kept locally in
[`assets/samples/`](../../assets/samples/) (copyrighted — gitignored, not committed;
see [index.md](index.md) for the regeneration commands). Every field is tagged
**observed** (byte/value evidence at the cited offset), **inferred**, or **unknown**.
⚠️ Single-sample caution: all conclusions come from one mesh + one texture bank; other
assets may contain values/branches not exercised here.

Tools: [`tools/geo2obj.py`](../../tools/geo2obj.py) (→ OBJ),
[`tools/txw2png.py`](../../tools/txw2png.py) (→ PNG). Proof renders (local outputs under
`assets/samples/` / `out/`, not committed):
`Ring_render.png` (shaded 704-tri rasterization),
`ring.png`, `ringglos.png` — the golden band is covered in
fiery Elvish runes and its glow map has matching alpha lettering, which validates the
vertex/UV and DXT layouts end-to-end.

## `.GEO` — MOEG mesh

File = 16-byte header + vertex array + index-count + u16 index array; size arithmetic is
exact with no padding (`0x10 + 784×0x20 + 4 + 2112×2 = 29,332` = file size) [observed].

| Offset | Type | Value (Ring.GEO) | Meaning | Tag |
|---|---|---|---|---|
| +0x00 | char[4] | `MOEG` | magic ("GEOM" reversed) | observed |
| +0x04 | u32 | 1 | format version | observed value, inferred name |
| +0x08 | u32 | 1 | mesh count (single-mesh file) | inferred |
| +0x0C | u32 | 784 | vertex count | observed (array end lands on index table) |
| +0x10 | struct[784] | — | vertex array, stride **0x20** | observed |
| vertex +0x00 | f32[3] | bbox ±13.107, ±3.146 | position | observed (ring radius 13.1, z ±3.1) |
| vertex +0x0C | f32[3] | ‖n‖ ∈ [1.0000, 1.0000] | unit normal | observed (all 784 normalized) |
| vertex +0x18 | f32[2] | 0.30–0.50 (some |uv|>1) | texture coords, tiling | observed |
| +0x6210 | u32 | 2112 | index count (= 3 × 704 triangles) | observed (exact size arithmetic) |
| +0x6214 | u16[2112] | max = 783 | CCW? triangle list | observed (max idx = verts−1; winding **unknown**) |

Notes:
- No material/texture-name table in the standalone `.GEO`; the game must bind
  `Ring.txw`→`ring`/`ringglos` externally (by naming convention — the file pair shares the
  stem `Ring`) [inferred].
- Per-mesh sub-mesh table (if `mesh_count > 1` is ever used): **unknown**.
- Likely the bulk of game geometry is embedded inside `.scw` files (no other `.GEO` on
  disk) — revisit during D5.

## `.txw` — TXW texture bank

File = `TXW ` header + sequence of RIFF-like chunks (`char[4] type`, u32 size, payload).
Layout below fully reconciles: chunk stream ends exactly at EOF [observed].

```
+0x00  u32 'TXW '   magic                                   [observed]
+0x04  u32 528      version (0x210)                         [observed value]
+0x08  chunk HEAD, size 8:  u32 0x00020000
            u16 @+0x02 = 2  texture count (matches TXHE entries)  [inferred]
       chunk TXHE, size 80×N: entry array (see below)
       chunk CLHE, size 0:   palette header (empty)               [unknown]
       chunk TXDA, size 24,584: raw block payload for ALL entries [observed]
            (declared size = 24,576 used + 8 trailing bytes; the
             declared-size field appears to count 8 header bytes)  [inferred]
       chunk CLDA, size 0:   palette data (empty)                 [unknown]
```

### TXHE entry (80 bytes)

| Offset | Type | ringglos / ring | Meaning | Tag |
|---|---|---|---|---|
| +0x00 | char[8] | `ringglos` / `ring` | texture name (NUL-padded) | observed |
| +0x08 | u32 | 0x0000 / 0x4000 | byte offset into TXDA payload | observed (0 / 16,384 = size of DXT3 first tex) |
| +0x0C | u16 | 1024 / 512 | block count | observed (= payload/16 and payload/8) |
| +0x0E | u16 | 0xFFFF / 0xFFFF | palette id? (-1 = none) | **unknown** |
| +0x10 | u32 | 0x00040000 ×2 | ? | **unknown** |
| +0x38 | u16 | 256 / 256 | width | observed (decode exact) |
| +0x3A | u16 | 64 / 64 | height | observed (decode exact) |
| +0x3C | u8 | 2 / 1 | pixel format | observed mapping below |
| +0x3D | u8 | 1 / 1 | ? | unknown |
| +0x3F | u8 | 8 / 8 | bpp? | unknown |
| +0x40 | u8 | 6 / 6 | ? | unknown |
| +0x41 | u8 | 7 / 0 | mip count? (but no mip data present) | **unknown** |
| +0x42 | u8 | 3 / 3 | ? | unknown |
| +0x48 | u32 | 0 / 1 | entry index | inferred |

### Pixel formats

| id | bytes/block | codec | Evidence |
|---|---|---|---|
| 1 | 8 | **DXT1/BC1** | 256×64 → 8,192 B = entry size; decodes to opaque gold rune band [observed visual] |
| 2 | 16 | **DXT3/BC2** | 256×64 → 16,384 B = entry size; alpha nibbles form the glow lettering [observed visual] |
| 5 | 16 | DXT5/BC3 | **inferred** (not in sample; `txw2png.py` implements it defensively) |
| other | — | unknown → tool errors with the id | — |

Alpha values in `ringglos` land exactly on 17·n multiples — the signature of DXT3's 4-bit
alpha ramp [observed]. No mipmaps are stored (total TXDA = sum of level-0 sizes) [observed].

## Open questions (for more samples)

1. `mesh_count > 1` files and sub-mesh tables.
2. Index-buffer winding and whether strips ever occur.
3. Semantics of TXHE `+0x0E/+0x10/+0x3D/+0x40/+0x41/+0x42`; palette (CLHE/CLDA) usage.
4. Whether `.txw` ever embeds mips or larger palettes.
5. GIM/.geo siblings — none exist in the install; may appear in `.pac` (D6) or `.scw` (D5).

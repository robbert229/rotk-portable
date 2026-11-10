# Format spec — `.pac` install archives (D6)

EA LOTR: Return of the King (2003) PC — installer payload containers `data_1.pac`
(Install Disc 1), `data_2.pac` (Install Disc 2), `data_3.pac` (PlayDisc).

Evidence base (all **observed** unless tagged): retail EN ISOs
`EA-LOTR-ReturnOfTheKing-EngWin98-InstallDisc1/2.iso`, `PlayDisk.iso01.iso`;
sizes data_1 = 608,151,456 B / data_2 = 660,595,281 B / data_3 = 603,761,773 B.
**Acceptance test passed**: every one of the 83 TOC members extracted by
`tools/unpac.py` is byte-identical (SHA-256) to the installed file under
`Data/`, including the two members that straddle pack boundaries.

## Mental model

The three packs concatenate into **one logical byte stream**. `data_1` carries
the whole-game TOC followed by all 83 member files concatenated in TOC order
(raw, uncompressed, no padding); each pack supplies a window of that stream:

```
data_1 logical: [TOC 0x0..0xb96][bla01.scw .. min02.scw][min04.scw 0..34,480,374)
data_2 logical: [min04 tail][osg01.scw .. isenfmv1.avi 0..14,041,334)
data_3 logical: [isenfmv1 tail .. slidspc3.avi]   (+4 B trailer in file)
```

Split members observed: `Game\min\min04.scw` (data_1→data_2) and
`Movies\isenfmv1.avi` (data_2→data_3) [observed]. Files are not aligned or
padded between members — each begins at exactly the previous member's end
[observed: member sizes sum exactly to the logical-stream lengths].

## File layout (each pack)

| Offset | Size | Field | Notes |
|---|---|---|---|
| 0x00 | 128 | ASCII id header | `'x' + 126 chars + 'x'`. Hex-ish; identical prefix `xa37dd45ffe1…` and suffix `…eaff312x` on all three packs, middle differs per pack. Role **unknown** (per-disc id or checksum — inferred) |
| 0x80 | 1 | `0x00` pad | [observed] |
| 0x81 | — | block stream | repeats until EOF |

### Block stream

```
block := u32 uncompressed_size   ; nominally 0x8000
        u32 compressed_size
        u8[compressed_size] data
```

* `compressed_size < 0x8000`: `data` is a zlib stream (`78 9c`), inflates to
  `uncompressed_size` [observed across 65,246 blocks].
* `compressed_size == 0x8000 == uncompressed_size`: `data` stored raw
  [observed: 1,886 blocks in data_2, 4,498 in data_3, 0 in data_1 — they
  coincide with the pre-compressed DivX `.avi` payloads; inferred mapping].
* The **last block** of a pack may inflate short (e.g. data_1's final block →
  26,368 B); treat `uncompressed_size` as a nominal cap [observed].
* data_3 has a 4-byte `00 00 00 00` remainder after its final block;
  data_1/data_2 end exactly on a block boundary. Role **unknown** [observed].

## TOC (logical stream of data_1 only)

```
toc := u32 count                        ; 99 [observed]
      count * {
        char path[];                    ; NUL-terminated ASCII, backslash separators
        u8   attrs;                     ; 0x00 or 0x80 (meaning unknown — both occur
                                        ;   on dirs and files; possibly FILE_ATTRIBUTE)
        u48  filetime_low;              ; low 7 bytes of Windows FILETIME
                                        ;   (100 ns since 1601); high byte always 0
        u32  size;                      ; exact installed byte size
      }
```

Record body is fixed 12 bytes after the NUL [observed: parses all 99 records,
83 file sizes match installed corpus exactly]. Records end at logical 0xb96
[observed]. `size == 0` marks the 16 directory entries (`Game`, `Game\<lvl>`,
`Movies`, `Player`, `Special`) [observed]. Members then start immediately at
the record end (0xb96) — no alignment [observed: `Game\bla\bla01.scw` first
byte at 0xb96 equals installed file byte 0].

The TOC lists **all 83 payload files of the whole game** in every context
it appears; it does not encode which pack holds a member — the packs are
simply sequential windows over the concatenation [observed]. `attrs` is not a
presence flag [observed: mixed 0x80/0x00 within a single pack's members].

## Member inventory (this disc set)

| Pack | Logical bytes | Members (TOC index range) |
|---|---|---|
| data_1 | 749,535,232 | files[0..12): `Game\bla\bla01.scw` … `Game\min\min04.scw` (partial) |
| data_2 | 776,175,616 | min04 tail … `Movies\isenfmv1.avi` (partial), incl. `LoadOnce.scw`, `Movies\*` |
| data_3 | 612,243,210 | isenfmv1 tail … `Special\slidspc3.avi`, incl. all `Player\*` |

[observed via `tools/unpac.py list` + SHA-256 member verification vs installed tree]

## Relationship to installer metadata

`filelist.txt` / `common_filelist.txt` list `data_N.pac` as type-5 entries
assigned to discs 1/2/3 (see [misc.md](misc.md)); they describe top-level
installer files only, not TOC members [observed].

## Tool

```bash
python3 tools/unpac.py info    data_1.pac data_2.pac data_3.pac
python3 tools/unpac.py list    data_1.pac [data_2.pac data_3.pac] [--json]
python3 tools/unpac.py extract data_1.pac [data_2.pac data_3.pac] -o OUT NAME [NAME...]
python3 tools/unpac.py extract data_1.pac ... --all
```

Stdlib-only (`zlib`, `struct`). Names use the TOC's backslash form; matching is
case-insensitive. Single-pack operation works for members wholly inside that
pack.

## Unknowns

1. Meaning of the 128-byte ASCII id header contents (per-pack id? checksum?).
2. Semantics of the `attrs` byte.
3. The 4-byte trailer at end of data_3.
4. Whether other locales/builds keep the TOC in data_1 identically (single disc set examined).

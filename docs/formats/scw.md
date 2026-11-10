# `.scw` scene files — COTS (mission) and LRTC (global) containers

C7/D5 deliverable ([spec](../deliverables.md)). Dumper:
[`tools/scwdump.py`](../../tools/scwdump.py) (`--json` for machine output).
Corpus: 44 files, ~1.3 GB (`Data/**/*.scw`). Validated: `LoadOnce.scw` (64 KB, kept locally
in `assets/samples/` — copyrighted, gitignored; extract with `tools/unpac.py`),
`Game/GlobScen.scw` (5.5 MB), `Game/fro/fro03.scw` (104 MB),
`Game/osg/osg01.scw` (115 MB), `Game/pel/pel02.scw` (65 MB), `Game/cir/cir01.scw`.
Claims tagged **observed** / **inferred** / **unknown**.

> ⚠️ This is a **container-level** spec: header, TOC, name pools, and region arithmetic are
> decoded with exact evidence. Zone payload internals (entities, geometry, audio streams)
> are **not yet decoded** — see Unknowns. The tag vocabulary (`TADS→SDAT`, `CNYS→SYNC`,
> `ONOS→SONO`, `DAPS→SPAD`, `tadR→Rdat`, `xtrc→crtx`, `pmas→samp`, `gfxt→txfg`) reads as
> reversed ASCII, consistent with EA's contemporary UAT asset pipeline [inferred].

## COTS — per-mission scene (majority of `Data/Game/*/*.scw`)

| Offset | Type | Value (validated files) | Meaning | Tag |
|---|---|---|---|---|
| +0x00 | char[4] | `COTS` | magic | observed |
| +0x04 | u32 | 308 fro / 716 osg / 416 pel / — cir | global resource count? | **unknown** |
| +0x08 | u32[2] | 0 | — | observed zero |
| +0x10 | char[4] | `COTS` | inner chunk tag | observed |
| +0x14 | u32 | 288/696/396/… | TOC chunk size S (covers table + name pool) | observed |
| +0x18 | u32 | 8/20/11/7 | entry count N | observed (matches names) |
| +0x1C | u32 | 1 | TOC version | observed value |
| +0x20 | u32[2] | 0 | — | observed zero |
| +0x28 | 16 B | (N, pool_off, 0x10000, x) | **TOC header record** — record 0, name = `initial_load` | observed |
| +0x38 | 16 B × (N−1) | below | zone/bank records | observed |
| pool_off | char[] | `initial_load\0zone_…\0igc_…_bank\0…` | NUL-separated names | observed |

Record layout (16 B): `(u32 kind, u32 name_off, u32 f3, u32 f4)`.

**Key semantic (observed, all 4 mission files):** `f3` = file **offset** of an embedded
sub-document, `f4` = its **size**, and records tile the file contiguously:
`f3[i] + f4[i] == f3[i+1]` for every i, from `0x10000` to the last record end
(fro03 → 0x1170000, osg01 → 0x1790000, pel02 → 0xec0000, cir01 → 0xa80000).
Missing zones are literally named `_missingZone_NN` with `f4 = 0` (fro03 zones 01/02/05)
[observed — corroborates the offset/size reading].

**Embedded sub-document (observed at every record's `f3`):**

```
+0x00 char[4] 'RVWS'   sub-document directory        [observed]
+0x04 u32     size     directory region size         [observed]
+0x08 'ELIF' + char[]  entry name ("FILE" reversed): matches the TOC record name
                       (e.g. initial_load, zone_pel02_zone1, igc_pele_igc1_b…)
+0x24 'LRTC' …         full embedded LRTC stream (same shape as standalone .scw files,
                       incl. CNYS/COHS chunks)       [observed for initial_load;
                       zones: LRTC marker not located within dir region — [unknown]]
```

Record `kind` values [observed]: first zone = 1, most zones/first igc bank = 2,
remaining igc banks = 3, `_missing` zones = 0 or 2. Semantics of 0/1/2/3: **unknown**.

After the TOC follows a `LLIF` chunk (tag at TOC-declared end − 4):

| | Value | Tag |
|---|---|---|
| Tag position | TOC declared end − 4 | observed (4 B gap also between table_end and pool_off) |
| `LLIF` size | 65,228 / 64,820 / 65,120 / 65,256 across 4 files | observed — near-constant ~64 KB blob |
| Payload | starts with many zeros; tail region (~+0xFE84) contains sub-records: `SVWS` (size 0x24), reversed `ELIF` = "FILE" markers, names like `initial_load`, and script strings `PLAY, 0, 1, 255, 0` (seen in fro03 at ≈0x10128) | observed bytes; structure **unknown** |

Body region records (offsets ≈ f3 of the zone/bank records): aligned 4-char record tags
with unknown record framing; census in the first 2 MB, e.g. fro03: `tadR`×246, `COHS`×242,
`gfxt`×227, `LLIF`×31, `xtrc`×18, `RDHS`×9, `zfxt`×9, `TADS`×4. A sample record at
0x17fc0 (fro03): `COHS` size 0x1ffc, payload of `(tag, u32 ×5)` rows, e.g.
`tadR 0 0x12fc80 0x405008 0x4ab018 4 0x12fdb0`, `gfxt 9 0x12fe74 0x4033a1 0x12feb4…`
[observed bytes; fields **unknown**].

### Interpretation notes

- Zone names + `PLAY, …` script strings + the `_missingZone_` fallback ⇒ records 1.. are
  gameplay **zones** loaded by the `initial_load` script [inferred].
- `igc_*_bank` records are **in-game-cinematic audio banks** — ROTK's FMV `.avi`s carry no
  audio (D3 evidence), so this is where cutscene/speech audio lives [inferred,
  consistent]; format inside = **unknown** (likely Fronteset-era EA sample banks; `pmas`→
  `samp` supports a sample directory [inferred]).
- `TADS` payload begins with the bytes `"SDAT""\r\n\r\n "`-style text (`22 22 0d 0a 0d 0a 20`)
  — resembles a RenderWare-style `SDAT` section header [observed bytes; format unknown].

## LRTC — global/boot scene (`GlobScen.scw`, `LoadOnce.scw`)

| Offset | Type | Value | Meaning | Tag |
|---|---|---|---|---|
| +0x00 | char[4] | `LRTC` | magic | observed |
| +0x04 | u32 | 0x18 | header size (chunks start here) | observed (both files) |
| +0x08 | u32[4] | 0 | — | observed zero |
| +0x18 | chunk | `COHS`, size 0x40 | first chunk; payload = index of `(tag, u32)` pairs: `RDHS 1`, `SNPR 1`, `COHS 0x44` | observed |
| after | | zeros to 16 B, then `TADS` whose "size" field contains ASCII | walker stops; deeper nesting undecoded | **unknown** |

Both LRTC files walk identically to offset 0x60 [observed]; `scwdump.py` reports the stop
point honestly instead of guessing.

## Size-arithmetic reconciliation (acceptance criterion)

- COTS: `TOC = 8(hdr) + 16(N+1) + 4(gap) + pool` — validated on 4 files
  (`table_end` = pool_off − 4 exactly; see `scwdump.py` output).
- Offset/size chain contiguity: **True on all 4 validated mission files** (tool-computed).
- `LLIF` chunk at `TOC_declared_end − 4`, size ≈ 64 KB in every file.

## Unknowns / follow-ons

1. Zone payload record framing (entity/spawner/geometry/AI) — needs deeper record-walking
   from the f3 offsets; `xtrc`/`tadR`/`gfxt`/`zfxt` field meanings.
2. `u32@0x04` meaning; kind 0/1/2/3 semantics; f3/f4 unit scale (likely raw bytes —
   offsets fit file span for smaller missions).
3. LRTC full chunk stream beyond 0x60 (GlobScen/LoadOnce only).
4. Whether zone payloads embed `.GEO`-like geometry (no standalone .GEO outside `fro/`).
5. Audio bank internal format (`pmas`/`ONOS`) — the FMV-audio answer from D3 likely lives
   here.

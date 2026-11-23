# SCW scene files

[observed: all 44 SCW rows in the retail install
[`assets_scw.csv`](../../re/corpus/assets_scw.csv)] There are 26 standalone
LRTC files (`Data/LoadOnce.scw`, `Data/Game/GlobScen.scw`, and the 24
`Data/Player/*.scw` files) and 18 COTS mission files under `Data/Game/*/`.
All multibyte integers below are little-endian.

[observed: `scwdump.py --json`, `--chunks-csv` and `--summary-csv`]
[`scwdump.py`](../../tools/scwdump.py) prints the standalone LRTC chunk
walk or the COTS TOC and aligned tag census. The detailed inventory covers the
bounded chunk streams in both families.

## LRTC header

| Offset | Type | Field | Evidence |
|---|---|---|---|
| +0x00 | char[4] | `LRTC` | [observed: all 26 standalone files and all 18 COTS initial-load regions] |
| +0x04 | u32 | Header byte length, 0x18. The first chunk starts at this displacement from the LRTC tag. | [observed: same 44 headers] |
| +0x08 | u32[2] | Both zero | [observed: same 44 headers; meaning unknown] |
| +0x10 | char[4] | `CNYS` | [observed: same 44 headers; role unknown] |
| +0x14 | u32 | Zero | [observed: same 44 headers; meaning unknown] |

## Shared chunk stream

[observed: all 26 standalone LRTC files and all 211 nonempty COTS TOC
regions across 18 missions] Chunk offsets and lengths are multiples of 4.
The size word counts bytes from the tag. The next tag starts at
`offset + size` with no additional rounding. Resource chunks stay within
a 0x10000-byte file page. The walk ends exactly at EOF for standalone files
and exactly at the TOC region end for COTS.

| Offset | Type | Field | Evidence |
|---|---|---|---|
| +0x00 | char[4] | `COHS`, `ONOS`, `DDAP`, or `LLIF` | [observed: corpus chunk walks] |
| +0x04 | u32 | Total chunk size, including the tag and size word. The 4-byte LLIF form has only a tag. | [observed: corpus chunk walks, including `GlobScen.scw` at file+0x51fffc] |
| +0x08 | u32[2] | Both zero in COHS and ONOS | [observed: all resource chunks in the corpus; meaning unknown] |
| +0x10 | char[4] | Payload tag. COHS starts with `RDHS`, `TADS`, or `tadR`. ONOS starts with `RDHS` or `TADS`. | [observed: all COHS and ONOS chunks in the corpus] |
| +0x14 | bytes | Payload fields and data | [unknown: layouts depend on payload tag] |

- [observed: all corpus DDAP chunks] DDAP has zero bytes after the 8-byte
  header and ends at a 64-byte file boundary. [inferred: zero payload and
  boundary arithmetic] It pads the stream before the next chunk.
- [observed: all corpus stream LLIF chunks] LLIF ends at a 0x10000-byte
  file boundary. The size-bearing form has zero bytes after its header.
  At the final word of a page, LLIF consists of the tag alone and the
  next chunk starts on the next page. Examples include `GlobScen.scw`
  file+0x51fffc, `Char_SaC.scw` file+0xcfffc, and `fro03.scw`
  file+0xeffffc. [inferred: zero payload and boundary arithmetic]
  These forms fill the rest of the page.
- [observed: all 26 standalone files] The initial COHS at file+0x18
  spans 0x40 bytes. The next COHS starts at file+0x58 and its `TADS`
  payload starts at file+0x68. `LoadOnce.scw` has 9 chunks and ends
  with LLIF spanning file+0x2f4 through EOF at 0x10000.
  `GlobScen.scw` has 758 chunks through EOF at 0x540000. The 26
  standalone streams contain 4,609 chunks in total.

### RDHS payload prefix

[observed: the first COHS in every standalone LRTC and embedded initial-load
LRTC, later COHS in `LoadOnce.scw`, ONOS in `GlobScen.scw`, and the first
COHS after the RVWS header of every nonempty COTS region after initial load]
The following two tagged words are printed as `index` by the dumper.

| Offset from COHS/ONOS tag | Type | Field | Evidence |
|---|---|---|---|
| +0x10 | char[4] | `RDHS` | [observed: RDHS-prefixed chunks] |
| +0x14 | u32 | Initial LRTC value 1. Later examples include 2 in `LoadOnce.scw` at chunk 0x1a4 and 5 in `fro03.scw` at chunk 0xeb0024. | [observed: example chunks; meaning unknown] |
| +0x18 | char[4] | `SNPR` in the first LRTC chunk. Later examples include `nidc` at `LoadOnce.scw` chunk 0x9c, `rdhs` at `GlobScen.scw` chunk 0xc0, and `efxt` at `fro03.scw` chunk 0xeb0024. | [observed: example chunks; resource type inferred from variation] |
| +0x1c | u32 | Value paired with the preceding tag. First standalone LRTC value 1. | [observed: example chunks; meaning unknown] |
| +0x20 onward | bytes | Remaining descriptor fields or inline data | [unknown: structure and any index-table boundaries] |

[inferred: tag spelling] Several tags read as reversed ASCII, including
`RDHS` (SHDR), `TADS` (SDAT), and `LLIF` (FILL).
[unknown: RDHS values and payload layouts] A resource count or index-table
interpretation for the RDHS words remains unverified. The same applies to
embedded `tadR`, `gfxt`, `xtrc`, and `pmas` record fields.

## COTS mission container

[observed: all 18 retail COTS files, `assets_scw.csv`] The TOC points to
bounded regions. The regions start at file+0x10000 and tile contiguously
through the last TOC entry. A separate unclassified tail extends from there
to EOF.

| File offset | Type | Field | Evidence |
|---|---|---|---|
| +0x00 | char[4] | `COTS` | [observed: all 18 mission headers] |
| +0x04 | u32 | Equals the LLIF file offset | [observed: all 18 mission headers; stored offset interpretation inferred] |
| +0x08 | u32[2] | Zero | [observed: all 18 mission headers; meaning unknown] |
| +0x10 | char[4] | Inner `COTS` tag | [observed: all 18 mission headers] |
| +0x14 | u32 | TOC size measured from file+0x14 to LLIF | [observed: all 18 mission headers] |
| +0x18 | u32 | Number of 16-byte TOC entries, including `initial_load` | [observed: all 18 TOCs] |
| +0x1c | u32 | 1 | [observed: all 18 TOCs; version interpretation inferred] |
| +0x20 | u32[2] | Zero | [observed: all 18 TOCs; meaning unknown] |
| +0x28 | u32[4] per entry | Kind, absolute name offset, absolute region offset, region byte length | [observed: all 18 TOCs; meaning of kind values unknown] |
| After entries | 4 bytes, then char[] | 4-byte gap, then NUL-separated name pool | [observed: all 18 TOCs] |
| LLIF offset | char[4], u32, bytes | `LLIF`, total size through file+0x10000, payload | [observed: all 18 missions; payload layout unknown] |

[observed: all 18 TOCs, including `fro03.scw` slots 01/02/05] Entry 0
has a kind equal to the entry count and is named `initial_load`. Other
entries have kinds 0–3. The `_missingZone_NN` slots have length zero.
[inferred: labels in the TOC] `zone_*` entries correspond to gameplay
zones. Some `igc_*_bank` labels suggest cinematic audio banks.
[unknown: contents of individual named banks and zone resources]

### RVWS regions

[observed: 211 nonempty entries across all 18 mission TOCs] Each region
starts with an RVWS header. The initial-load region has an embedded LRTC
header at file+0x10024. The other 193 nonempty regions start their first
COHS directly after RVWS. The shared stream walk reaches each region's TOC
end, including in named bank regions.

| Offset from RVWS tag | Type | Field | Evidence |
|---|---|---|---|
| +0x00 | char[4] | `RVWS` | [observed: all 211 regions] |
| +0x04 | u32 | Header size 0x24 including tag and size | [observed: all 211 regions] |
| +0x08 | u32[2] | Both zero | [observed: all 211 regions; meaning unknown] |
| +0x10 | char[4] | `ELIF` | [observed: all 211 regions] |
| +0x14 | char[16] | NUL-terminated name, sometimes shortened relative to the TOC name | [observed: all 211 regions, e.g. `fro03.scw` file+0xeb0014] |

[unknown: COTS tail framing] The remaining bytes begin at the last TOC
region end recorded in `assets_scw.csv` for each mission. For example,
`fro03.scw` has a zero-filled page at file+0x1170000 followed by a
nonzero page at 0x1180000. Its tail extends to EOF at 0x6340000.
[observed: `fro03.scw` at the listed offsets]

## Chunk inventory

[observed: [scw_chunk_summary.csv](../../re/corpus/scw_chunk_summary.csv) and the
detailed retail walk] The inventory has 92,419 rows. Counts include structural
headers. Root headers are at depth zero. The deepest rows in COTS belong to
streams within embedded LRTC headers at depth four. Standalone LRTC files reach
depth one and EOF. COTS walks cover the contiguous TOC regions and leave
10,354,688–98,697,216 bytes per file. [unknown: framing of the COTS tails.]

| Tag | COTS files | Standalone LRTC files | Total |
|---|---:|---:|---:|
| COTS | 36 | 0 | 36 |
| LRTC | 18 | 26 | 44 |
| RVWS | 211 | 0 | 211 |
| COHS | 77,757 | 3,023 | 80,780 |
| ONOS | 5,538 | 1,205 | 6,743 |
| DDAP | 70 | 100 | 170 |
| LLIF | 4,154 | 281 | 4,435 |
| **Total** | **87,784** | **4,635** | **92,419** |

`make scw-summary` regenerates the committed per-file CSV.
`make scw-chunks` writes the detailed inventory to `out/corpus/scw_chunks.csv`.
Set `ROTK_GAME_DIR` to choose the install.

In the detailed CSV, `path` is install-relative. `offset` and `parent` are absolute
file offsets in hex. `size` is a decimal byte length and `index` is the zero-based
ordinal within the stream, or the TOC ordinal for RVWS. A parent points to the
header for the stream or TOC. Empty parents mark root rows. `notes` labels the
observed payload tag, filler, or header role. The inner COTS row spans its tag,
TOC and name pool up to the leading LLIF.

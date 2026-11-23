# Retail install format coverage

[observed: `make corpus-formats` and the resulting
[`formats.csv`](../../re/corpus/formats.csv)] The inventory covers all 120 install
rows in [`manifest.csv`](../../re/corpus/manifest.csv). The generator verifies
each file's size and SHA-256 against the manifest and keeps the original
extension spelling. The `magic_hex` column records up to eight bytes from
file+0. Detection also uses the PE signature at the DOS header's pointer, the
AVI form type at file+0x08, and the header fields for BMP and ICO.
[inferred: text rules in `tools/corpus_formats.py`] XML, INI and plain text are
classified from a decoded prefix using markup, section/assignment syntax and
printable characters.

[observed: parser commands in `tools/corpus_formats.py`] Each repository parser
runs in isolated Python with a 30-second timeout. Success measures whether
the selected tool parses its supported part of the format. `n/a` marks files
with no probe configured for this audit. The asset index separately parses AVI
headers [observed: `tools/assetindex.py`, `assets_avi.csv`]. Regenerate with `make corpus-formats` and set
`ROTK_GAME_DIR` to select the installation.

## Counts and parse rates

| Detected format | Files | OK / attempted | Without a probe | Evidence |
|---|---:|---:|---:|---|
| RIFF/AVI | 37 | — | 37 | [observed: `formats.csv`, RIFF/AVI rows] |
| SCW LRTC | 26 | 26/26 (100%) | 0 | [observed: `formats.csv`, SCW LRTC rows] |
| SCW COTS | 18 | 18/18 (100%) | 0 | [observed: `formats.csv`, SCW COTS rows] |
| PE | 15 | 15/15 (100%) | 0 | [observed: `formats.csv`, PE rows] |
| XML | 13 | — | 13 | [observed: `formats.csv`, XML rows] |
| plain text | 4 | — | 4 | [observed: `formats.csv`, plain text rows] |
| BMP | 2 | — | 2 | [observed: `formats.csv`, BMP rows] |
| GEO | 1 | 1/1 (100%) | 0 | [observed: `formats.csv`, GEO row] |
| TXW | 1 | 1/1 (100%) | 0 | [observed: `formats.csv`, TXW row] |
| INI | 1 | — | 1 | [observed: `formats.csv`, INI row] |
| HLP | 1 | — | 1 | [observed: `formats.csv`, HLP row] |
| ICO | 1 | — | 1 | [observed: `formats.csv`, ICO row] |
| **Total** | **120** | **61/61 (100%)** | **59** | [observed: all `formats.csv` rows] |

- [observed: `scwdump.py --json`, `formats.csv` SCW rows] The COTS probe
  parses the TOC. All 26 standalone LRTC walks reach EOF and account for 4,609
  stream chunks. The corpus walk separately covers the bounded TOC regions of
  all 18 COTS files [observed: `scw_chunk_summary.csv`]. COTS tails beyond those
  regions remain unclassified [unknown: [SCW spec](../formats/scw.md)].
- [observed: `geo2obj.py --json` and `txw2png.py --list`] The GEO probe
  parses the vertex and index tables. The TXW probe lists the texture table.
- [observed: `richhdr.py --json`, `formats.csv` PE rows] Rich records
  decode in all 15 PE files. Fourteen pass the checksum check.
  `SECDRV.SYS` reports a checksum mismatch and returns decoded records.
  See [Rich-header analysis](../research/toolchain.md#per-binary-results).

## Unknown formats and parser failures

[observed: `formats.csv` has no `unknown` detections or `fail` statuses]
All install rows classified, and every attempted parser returned its supported
result. The table above records the 59 files without a configured probe by format.

## Extension and content mismatches

[observed: `formats.csv` BMP rows and
[`misc.md`](../formats/misc.md#00000000016-307324-b-and-00000000256-308278-b--bmp-bitmaps)]
These are the two mismatches in this install when extensions are compared
case-insensitively and `.exe`, `.dll` and `.sys` are treated as PE extensions.

| Path | Extension | Detected content | Evidence |
|---|---|---|---|
| `00000000.016` | `.016` | BMP | [observed: `BM` at file+0 and BMP header fields] |
| `00000000.256` | `.256` | BMP | [observed: `BM` at file+0 and BMP header fields] |

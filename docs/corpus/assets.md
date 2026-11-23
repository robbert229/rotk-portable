# Installed asset index

[observed: install rows in `re/corpus/manifest.csv` and their SHA-256-matched files.]
The index contains 105 of the 120 manifest install rows, including 44 SCWs
and 37 AVIs. The 15 files with DOS and PE signatures are catalogued in
[binaries.csv](../../re/corpus/binaries.csv). The three CSVs share `path` and
`sha256` as join keys. Paths are relative to the game directory.

| Format | Files |
|---|---:|
| SCW, COTS | 18 |
| SCW, LRTC | 26 |
| AVI | 37 |
| XML | 13 |
| TXT | 4 |
| INI | 1 |
| GEO | 1 |
| TXW | 1 |
| BMP | 2 |
| ICO | 1 |
| HLP | 1 |

[observed: `assets.csv` format and container columns.] BMP, ICO and HLP rows
record identity and size, with the reason structural fields are absent.

## Regeneration and fields

Run `make assetindex` with the manifest's retail install. Override
`ROTK_GAME_DIR` to select its location. For a separate output directory, run
`python3 -BI tools/assetindex.py --out-dir out/assetindex`. Regeneration
verifies the manifest's sizes and hashes before replacing the CSVs.

The `details` field uses semicolon-separated `key=value` pairs with
percent-encoded values. Decode each value after splitting the pairs.
Vertical bars separate items in list-valued fields. Empty CSV cells
denote unavailable or inapplicable fields.

[observed: the XML element tree, decoded CR/LF-delimited text, MOEG vertex
and index arrays, and TXHE entries.] XML counts include the root. Child tags
are distinct immediate children of the root. Text line counts include blank
and comment lines, and section counts tally bracketed headers. The readme
decodes as Windows-1252 [inferred: its bytes fail UTF-8 decoding and are
Windows-1252-compatible]. The remaining text files contain ASCII. GEO
extents are max minus min on each of X, Y and Z in model units. TXW entries
list name, dimensions and format ID in file order.

## Mission scenes

[observed: COTS TOC records at file+0x28 and the associated name pools and
RVWS directories, `assets_scw.csv`.] The table counts nonzero-size `zone_`
records as gameplay zones [inferred: role from the names]. Missing slots use
`_missingZone_`. The bank column counts `igc_` names ending in `bank`,
including names without a separating underscore. Other `igc_` records have
their own count [unknown: content or audio role of individual cinematic records].

The parallel record lists in `assets_scw.csv` preserve TOC order, with offsets
and sizes in hex. Empty list positions preserve alignment with the TOC.
Embedded names come from the RVWS/ELIF directory at each nonempty record
offset. They can differ from the longer TOC names. The asset index reports two top-level COTS entries per file, the inner TOC
and its following LLIF. For standalone LRTC, `chunk_count` counts
every stream chunk after the header and `walk_end` equals EOF in all 26
files. Counts range from 9 to 758 and sum to 4,609 [observed: LRTC walks,
`assets_scw.csv`]. The `cohs_index` column lists the two tagged words in
each RDHS-prefixed COHS. [unknown: purpose of those words]
[observed: `scw_chunk_summary.csv`] Across the 18 COTS files, all 211
nonempty TOC regions contribute 87,501 stream chunks to the separate
[SCW inventory](../formats/scw.md#chunk-inventory). The 26 standalone LRTC
files and the COTS files together contribute 92,419 rows including headers.
Run `make scw-chunks` to generate the detailed local inventory.

| Mission | Zones | Missing slots | Named banks | Other cinematic records |
|---|---:|---:|---:|---:|
| bla01 | 3 | 0 | 0 | 5 |
| cir00 | 17 | 0 | 0 | 3 |
| cir01 | 5 | 0 | 0 | 1 |
| cra01 | 5 | 0 | 1 | 0 |
| fro03 | 3 | 3 | 1 | 0 |
| hel01 | 5 | 0 | 2 | 2 |
| ise01 | 15 | 0 | 0 | 0 |
| min00 | 15 | 0 | 0 | 0 |
| min02 | 6 | 0 | 0 | 0 |
| min04 | 6 | 0 | 0 | 0 |
| osg01 | 16 | 0 | 3 | 0 |
| pal01 | 7 | 0 | 0 | 0 |
| pal02 | 7 | 0 | 0 | 0 |
| pat01 | 20 | 0 | 1 | 1 |
| pat02 | 4 | 0 | 0 | 1 |
| pat03 | 12 | 0 | 1 | 0 |
| pel02 | 5 | 0 | 5 | 0 |
| she01 | 11 | 0 | 0 | 4 |

## Videos

[observed: `hdrl/avih`, video `strl/strh` and `strf`, and top-level RIFF
chunks in all 37 files, `assets_avi.csv`.] Each AVI has one `DXGM` video
stream, zero audio streams and an `idx1` index. The video stream and main
header frame counts agree. Duration is video stream length × scale ÷ rate.
The first RIFF form ends before a final `JUNK` chunk in all 37 files,
leaving 84–2,042 bytes beyond the declared RIFF extent including that
chunk's header. The index walks the declared form and skips the media
payload.

The only 512×448 files are `Movies/attrfmv1.avi` and
`Special/makespc1.avi`. The other 35 are 512×480. Those two files and
`Movies/rtsvid.avi` use 30,000/1,001 fps. The other 34 use 24,000/1,001 fps
[observed: video stream `strh` timing and `strf` dimensions].

| Path below `Data/` | Duration (s) |
|---|---:|
| Movies/attrfmv1.avi | 156.490 |
| Movies/crakfmv1.avi | 24.107 |
| Movies/endfmv1.avi | 100.058 |
| Movies/gatefmv1.avi | 46.755 |
| Movies/gatefmv2.avi | 31.198 |
| Movies/helmfmv1.avi | 207.499 |
| Movies/helmfmv2.avi | 35.202 |
| Movies/helmfmv3.avi | 155.906 |
| Movies/isenfmv1.avi | 73.240 |
| Movies/isenfmv2.avi | 49.216 |
| Movies/logos.avi | 18.310 |
| Movies/mtwlfmv1.avi | 111.111 |
| Movies/mtydfmv2.avi | 33.867 |
| Movies/osgifmv1.avi | 131.590 |
| Movies/osgifmv2.avi | 77.119 |
| Movies/pat1fmv1.avi | 84.084 |
| Movies/pat1fmv2.avi | 28.529 |
| Movies/pat2fmv1.avi | 3.003 |
| Movies/pelefmv1.avi | 56.556 |
| Movies/rtsvid.avi | 91.892 |
| Movies/shelfmv1.avi | 28.695 |
| Special/faraspc1.avi | 36.578 |
| Special/faraspc2.avi | 46.046 |
| Special/frodspc1.avi | 63.814 |
| Special/gandspc1.avi | 80.831 |
| Special/gollspc1.avi | 109.359 |
| Special/hobtspc1.avi | 83.417 |
| Special/makespc1.avi | 174.207 |
| Special/meryspc1.avi | 45.045 |
| Special/meryspc2.avi | 46.004 |
| Special/pipnspc1.avi | 31.782 |
| Special/pipnspc2.avi | 36.703 |
| Special/samgspc1.avi | 76.076 |
| Special/saruspc1.avi | 56.932 |
| Special/slidspc1.avi | 103.478 |
| Special/slidspc2.avi | 103.478 |
| Special/slidspc3.avi | 101.393 |

## Variation in unresolved fields

- [Unknown: COTS u32 at file+0x04.] Across all 18 COTS headers its value is
  236–824 and exactly equals the LLIF tag offset. It also equals the TOC
  chunk size at file+0x14 plus 20 [observed: `u32_04_unknown`, `llif_offset`,
  `toc_bytes` in `assets_scw.csv`]. A stored offset to LLIF is a candidate
  interpretation [inferred: corpus-wide equality].
- [Unknown: COTS record-kind semantics.] The TOC kind varies across 0, 1, 2
  and 3 after `initial_load`. In `fro03.scw`, kind 0 occurs on both a
  missing slot and data-bearing zones. The three missing slots use kinds
  1, 0 and 2. Kind 3 occurs on both bank-named and zone-named cinematic
  records [observed: TOC at file+0x28, parallel names, kinds and sizes in
  `assets_scw.csv`].
- [Unknown: full COTS LLIF payload layout.] LLIF sizes vary from 64,712 to
  65,300. Its tag offset plus declared size equals file+0x10000 in every
  mission [observed: `llif_offset`, `llif_size` and the first TOC record
  offset in `assets_scw.csv`]. This arithmetic is consistent with size
  measured from the tag [inferred].
- [Unknown: COTS layout beyond the contiguous TOC record chain.] For all
  18 missions, the byte-offset/size interpretation lands on an RVWS tag
  for each nonempty record and the chain begins at file+0x10000. The
  recorded chain is contiguous and leaves 10,354,688–98,697,216 bytes to
  EOF [observed: COTS TOC and RVWS signatures, `bytes_after_chain` in
  `assets_scw.csv`]. The offsets are useful landmarks for examining
  the rest of each file.
- [Unknown: LRTC resource payload formats.] COHS and ONOS payloads start
  with `RDHS`, `TADS`, or `tadR` [observed: `out/corpus/scw_chunks.csv`].
  The TOC region walks use the same framing, with a nested LRTC header
  at file+0x10024 for each `initial_load` [observed: all 18 COTS missions].
- [Unknown: TXHE byte at entry+0x41.] It is 7 for `ringglos` (format ID 2)
  and 0 for `ring` (format ID 1), both 256×64 [observed:
  `Data/Game/fro/Ring.txw`, TXHE entries 0 and 1, `txhe_41_unknown` in
  `assets.csv`]. This is the varying unknown entry field identified by the
  TXW spec in this sample.
- [Unknown: semantics of the two `filelist.txt` integer columns.] Observed
  pairs are (0, 0), (1, 1), (1, 5), (2, 5) and (3, 5) [observed:
  `filelist.txt` leading columns, `integer_pairs` in `assets.csv`].

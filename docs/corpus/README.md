# ROTK retail corpus

The corpus uses the retail Windows installation identified by the
[install manifest](../../re/corpus/manifest.csv). Run `make corpus` to
regenerate the install-derived tables and `make corpus-check` to compare
fresh output with Git `HEAD`. The [CSV index](../../re/corpus/README.md)
lists schemas, row counts and local outputs.

- [observed: `formats.csv`] All 120 install files have a format
  classification. All 61 configured probes succeeded over the structures
  they support. [Format coverage](formats.md)
- [observed: `binaries.csv`, `pe_sections.csv`, `pe_imports.csv`] The
  15 PE32 x86 images contain 66 section headers and 2,019 import thunks.
  The packed main executable exposes 10 ordinary and 21 delay-load imports.
  [PE catalogue](binaries.md)
- [observed: `assets.csv`, `assets_scw.csv`, `assets_avi.csv`] The 105
  non-PE files include 44 SCWs and 37 AVIs. Each AVI contains a single
  DXGM video stream with zero audio streams. [Asset index](assets.md)
- [observed: `filerefs.csv` and `listed_files.csv`] The packed binaries
  expose 142 path-shaped references. The two install lists explicitly name
  96 distinct installed files and cover 118 with the wildcard.
  [File references](filerefs.md)
- [observed: `media.csv` and the PAC spec] There are 27 published PC track
  records in the catalogue. An earlier retail comparison matched all 83
  file members to the installed `Data/` tree by SHA-256.
  [unknown: results of the current verifier on the owner's discs.]
  [Retail media and PAC verification](media.md)
- [observed: `libraries.csv`] The scan records 200 fingerprints, including a
  D3DX8 reference data match in packed ROTK.exe and zlib 1.1.4 and MiniZip
  0.15 banners in `eauninstall.exe`. [unknown: exact retail D3DX8 SDK release
  and the linked CRT object count.] [Library fingerprints](libraries.md)
- [observed: `editions.csv` and its cited records] The catalogue contains 67
  edition and engine-reference entries, including two US English three-CD
  pressings with different disc hashes. [unknown: whether their game
  executables differ.] [Editions and engine leads](editions.md)
- [observed: `samples.csv`] Fifty-two retail sample paths are pinned by
  SHA-256. Three also serve as flat regression inputs.
  [Sample selection](samples.md)
- [observed: `scw_chunk_summary.csv`] The inventory covers 92,419 headers
  and chunks. All 26 standalone LRTC walks reach EOF. The 18 COTS walks
  cover 211 nonempty TOC regions. [unknown: the framing of the COTS tails.]
  [SCW walk and per-tag totals](../formats/scw.md#chunk-inventory)

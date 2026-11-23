# Retail corpus samples

[re/corpus/samples.csv](../../re/corpus/samples.csv) pins the original files by
SHA-256 and byte size. [observed: all 52 sample rows join to install rows in
`manifest.csv` and to detections in `formats.csv`.] The canonical files occupy
999,169,829 bytes. The three flat regression copies add 119,668 bytes.

## Fetch and verify

```sh
make samples
python3 -I tools/samples.py check
make test
```

Set `ROTK_GAME_DIR` to use a different install. Set `ROTK_SAMPLES_DIR` to use a
different destination and test directory. The CLI also accepts
`--game-dir`, `--samples-dir` and `--manifest`.

[observed: `tools/samples.py` and `tests/test_samples.py`.] The tool copies
each file to `assets/samples/<format>/<source_path>`. Format directory names
use lowercase ASCII with hyphens for spaces and slashes, so `RIFF/AVI` becomes
`riff-avi`. Original path components and case are preserved. A fetch reuses a
verified local copy and publishes a replacement only after its size and hash
match. Either command exits nonzero if any required file cannot be obtained
or verified. Keep the local sample tree out of git.

The checked-in list uses paths relative to the installation. For a custom
manifest with `pac` rows, use slash-separated archive member paths and pass
`--pac-dir` pointing to a tree already extracted with `tools/unpac.py`. A
fetch reports missing PAC members individually and still processes other
rows. [unknown: representatives for disc-only data, pending a retail PAC
inventory.]

[observed: `tests/test_tools.py`, `tests/expected.json` and the three
`used_by_tests=yes` rows.] The flat copies are `LoadOnce.scw` for both
`scwdump` outputs, `Ring.GEO` for `geo2obj`, and `Ring.txw` for `txw2png`.
`check` verifies those copies too. Use the canonical paths to probe other
variants in agent work. The sample CLI tests use synthetic files in
temporary directories.

## Selection

Start with the smallest and largest file by byte size for each
`detected_format` in `formats.csv`. Also take those endpoints within each
non-PE variant below. Break size ties by ascending case-sensitive source
path, and count a selected file only once. Keep the additional named
examples below. Copy sizes and hashes from `manifest.csv` and sort rows by
format and then source path. The sample ID is the lowercased format and
source path with runs of non-alphanumerics replaced by hyphens and edge
hyphens removed.

[observed: `samples.csv` for counts and byte ranges, and the named indexes
for the variant evidence.]

| Format | Files | Size range in bytes | Selection and evidence |
| --- | ---: | ---: | --- |
| BMP | 2 | 307,324–308,278 | Both indexed bitmaps. The `.016` uses a partial palette and the `.256` has 256 entries [observed: BMP headers and palette sizes in [misc.md](../formats/misc.md)]. |
| GEO | 1 | 29,332 | The sole MOEG v1 mesh, `Ring.GEO` [observed: `assets.csv`]. |
| HLP | 1 | 507,358 | The sole WinHelp file, `en-us_eahelp.hlp` [observed: `formats.csv`]. |
| ICO | 1 | 3,262 | The sole icon, `ROTK.ico` [observed: `formats.csv`]. |
| INI | 1 | 34,157 | The sole input map, `Input.ini`, with 25 sections [observed: `assets.csv`]. |
| PE | 15 | 12,528–2,874,240 | Keep the complete catalogue from `SECDRV.SYS` to `ROTK.exe`. These files cover PE32 drivers, DLLs and executables, including the Rich-header checksum mismatch, packed overlay, delay imports, exports and debug records [observed: [binaries.md](binaries.md) and `formats.csv`]. |
| RIFF/AVI | 5 | 51,200–64,032,768 | Group by codec, width, height and stream rate/scale. DXGM appears at 512×448 with 30000/1001 fps and at 512×480 with 24000/1001 or 30000/1001 fps [observed: `assets_avi.csv`]. |
| SCW COTS | 10 | 26,345,472–116,981,760 | Group by presence of missing zone slots, named banks and other `igc_` records. Keep `pat01.scw` for the most TOC records and `pel02.scw` for the most named banks. The selected TOCs include record kinds 0–3 [observed: `assets_scw.csv`]. |
| SCW LRTC | 6 | 65,536–5,505,024 | Keep `LoadOnce.scw` and `GlobScen.scw` individually and group the remaining packages by `Char_` and `Foll_` filenames [observed: `assets_scw.csv` paths]. [unknown: structural differences after the common COHS prefix.] |
| TXW | 1 | 24,800 | The sole TXW, `Ring.txw`, includes both observed TXHE format IDs, 1 and 2 [observed: `assets.csv`]. |
| XML | 5 | 897–7,971 | Group by root and element count. The set covers the registration config, 61-element dictionaries and the 63-element Swedish dictionary. Keep the Korean dictionary for multibyte UTF-8 text [observed: `assets.csv` XML tree summaries and bytes in `Support/ereg-dict-ko.xml`]. |
| plain text | 4 | 364–18,638 | Keep the ASCII installer CSV, path list and EULA, plus the CP1252-compatible readme [observed: `assets.csv` encodings and line counts, and [misc.md](../formats/misc.md)]. |

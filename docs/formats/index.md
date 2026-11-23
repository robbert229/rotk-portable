# Format registry — ROTK (EA 2003) PC data files

C7/D9 deliverable ([spec](../deliverables.md)). Single index of every reverse-engineered
on-disk format, its spec, its tool, and honest coverage. Evidence tags inside each spec:
**observed** / **inferred** / **unknown**.

| Format | Where | Spec | Tool | Corpus | Status |
|---|---|---|---|---|---|
| `.scw` **COTS** (mission scene) | `Data/Game/<lvl>/<lvl>NN.scw` | [SCW spec](scw.md) | [scwdump.py](../../tools/scwdump.py) | [formats.csv](../../re/corpus/formats.csv), [scw_chunk_summary.csv](../../re/corpus/scw_chunk_summary.csv) | [observed: re/corpus/formats.csv and re/corpus/scw_chunk_summary.csv] 18 files, with all 211 nonempty TOC regions walked. [unknown: tail framing and resource payload layouts.] |
| `.scw` **LRTC** (global/boot/character) | `Data/Game/GlobScen.scw`, `Data/LoadOnce.scw`, `Data/Player/{Char,Foll}_*.scw` | [SCW spec](scw.md) | [scwdump.py](../../tools/scwdump.py) | [formats.csv](../../re/corpus/formats.csv), [scw_chunk_summary.csv](../../re/corpus/scw_chunk_summary.csv) | [observed: re/corpus/formats.csv and re/corpus/scw_chunk_summary.csv] All 26 standalone streams walk to EOF. [unknown: resource payload layouts.] |
| `.GEO` **MOEG** mesh | `Data/Game/fro/Ring.GEO` | [geo-txw.md](geo-txw.md) | [geo2obj.py](../../tools/geo2obj.py) | [assets.csv](../../re/corpus/assets.csv), [formats.csv](../../re/corpus/formats.csv) | [observed: re/corpus/assets.csv and GEO spec] The single installed mesh has 784 vertices and 704 triangles. [unknown: multi-mesh layout and winding.] |
| `.txw` **TXW** texture bank | `Data/Game/fro/Ring.txw` | [geo-txw.md](geo-txw.md) | [txw2png.py](../../tools/txw2png.py) | [assets.csv](../../re/corpus/assets.csv), [formats.csv](../../re/corpus/formats.csv) | [observed: re/corpus/assets.csv and TXW spec] The single installed bank has two 256×64 textures, ID 1 (DXT1) and ID 2 (DXT3). [unknown: palettes, mips and other IDs.] |
| `.avi` FMVs | `Data/Movies/*.avi` (21), `Data/Special/*.avi` (16) | [FMV pipeline](../analysis/fmv-pipeline.md#container-facts-measured-from-the-shipped-fmvs-observed) | [assetindex.py](../../tools/assetindex.py) | [assets_avi.csv](../../re/corpus/assets_avi.csv) | [observed: re/corpus/assets_avi.csv] Single `DXGM` video stream at 512×480 or 512×448 and 23.976 or 29.97 fps, with `idx1` and zero audio streams. [unknown: exact FMV audio source.] |
| `.pac` archives | Retail ISOs, `data_1.pac` through `data_3.pac` | [pac.md](pac.md) | [unpac.py](../../tools/unpac.py) | [media.csv](../../re/corpus/media.csv), [manifest.csv](../../re/corpus/manifest.csv) | [observed: re/corpus/media.csv, PAC spec and re/corpus/manifest.csv] The media table catalogues the discs. The PAC spec records a 128 B ASCII ID header and a stream of blocks prefixed by uncompressed and stored sizes. The three packs form one logical stream with 99 TOC entries and 83 file members matched by SHA-256 to the installed `Data/` tree. Two members cross pack boundaries. [unknown: ID header and attribute semantics, and the 4-byte final trailer.] |
| `Input.ini` | Install root | [misc.md](misc.md#inputini-34157-b-dated-2003-10-03-in-box) | — | [assets.csv](../../re/corpus/assets.csv) | [observed: re/corpus/assets.csv and INI spec] 25 sections, with bindings and token grammar catalogued. [unknown: parser semantics.] |
| `filelist.txt` / `manifest.txt` | Install root | [misc.md](misc.md) | [filerefs.py](../../tools/filerefs.py) | [listed_files.csv](../../re/corpus/listed_files.csv) | [observed: re/corpus/listed_files.csv] Installer list includes the three PAC names. The installed-payload list resolves to installed files. [unknown: integer column semantics.] |
| `00000000.016` / `.256` | Install root | [misc.md](misc.md) | — | [formats.csv](../../re/corpus/formats.csv) | [observed: re/corpus/formats.csv and BMP headers] Uncompressed 8-bpp 640×480 BMPs. [inferred: SafeDisc provenance.] |
| `SECDRV.SYS` / `DrvMgt.dll` | Install root | [misc.md](misc.md) | [pecat.py](../../tools/pecat.py) | [binaries.csv](../../re/corpus/binaries.csv) | [observed: re/corpus/binaries.csv and companion scan] SafeDisc security driver and helper DLL with three export slots, including `Setup` and `Remove`. |
| `Support/*` (EReg, EasyInfo, readme, EULA, config.xml) | `Support/` | [misc.md](misc.md) | [pecat.py](../../tools/pecat.py), [assetindex.py](../../tools/assetindex.py) | [binaries.csv](../../re/corpus/binaries.csv), [assets.csv](../../re/corpus/assets.csv) | [observed: re/corpus/binaries.csv, re/corpus/assets.csv and support file contents] EA registration and support payloads. [inferred: individual roles where based on filenames.] |
| DivX middleware PE trio | Install root | [companion-dlls.md](../analysis/companion-dlls.md) | [pecat.py](../../tools/pecat.py) | [binaries.csv](../../re/corpus/binaries.csv), [pe_imports.csv](../../re/corpus/pe_imports.csv) | [observed: re/corpus/binaries.csv and re/corpus/pe_imports.csv] 16, 22 and 4 export slots for FileParser, DivxMediaLib and DivxDecoder respectively. Import edges and API roles are covered in the dossier. |

[observed: re/corpus/formats.csv] The full install audit classifies all 120
files and reports 61 successful probes across the structures covered by the
configured tools. See [format coverage](../corpus/formats.md) for the probe
breakdown.

## Toolchain entry points

```bash
# Samples are copyrighted and NOT distributed with this repo (gitignored).
# Extract them from your own retail discs/ISOs first:
python3 tools/unpac.py extract <iso-dir>/data_1.pac -o assets/samples \
    'Game\fro\Ring.GEO' 'Game\fro\Ring.txw'
python3 tools/unpac.py extract <iso-dir>/data_1.pac <iso-dir>/data_2.pac <iso-dir>/data_3.pac \
    -o assets/samples 'LoadOnce.scw'

python3 tools/geo2obj.py assets/samples/Ring.GEO -o out/Ring.obj
python3 tools/txw2png.py assets/samples/Ring.txw -o out/
python3 tools/scwdump.py <file>.scw [--json]          # COTS TOC/records or LRTC chunk walk
python3 tools/unpac.py info <iso-dir>/data_1.pac [data_2.pac data_3.pac]
```

All tools are stdlib-only `python3 ≥3.8`.

## Samples (`assets/samples/` — local only, gitignored)

Copyrighted game data; never committed. Expected local set used by the specs:
`Ring.GEO` · `Ring.txw` · `LoadOnce.scw` (64 KB), plus tool outputs
`Ring.obj` · `ring.png` · `ringglos.png` · `Ring_render.png` (under `out/`).

## Cross-cutting unknowns (next targets)

1. ~~`.pac` container (D6)~~ — **done** (retail ISOs; `docs/formats/pac.md`; remaining pac unknowns are minor: id-header, attrs, 4 B trailer).
2. [unknown: COTS tail framing and the internal format of `igc_*_bank` audio.]
3. [unknown: `COHS` and `ONOS` resource payload layouts in COTS and LRTC.]
4. Unpacked `ROTK.exe` → resolves `Input.ini` parsing, `.vid` question, output-format
   enums, `u32@0x04`, TXW entry filler fields (`docs/research/safe-disc.md` plan).

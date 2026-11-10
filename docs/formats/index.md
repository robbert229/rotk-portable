# Format registry — ROTK (EA 2003) PC data files

C7/D9 deliverable ([spec](../deliverables.md)). Single index of every reverse-engineered
on-disk format, its spec, its tool, and honest coverage. Evidence tags inside each spec:
**observed** / **inferred** / **unknown**.

| Format | Where | Spec | Tool | Status |
|---|---|---|---|---|
| `.scw` **COTS** (mission scene) | `Data/Game/<lvl>/<lvl>NN.scw` (41 files) | [scw.md §COTS](scw.md) | [`tools/scwdump.py`](../../tools/scwdump.py) | Container decoded: header, TOC (16 B records `kind/name_off/offset/size`, contiguous tiling verified on 4 files), name pool, embedded `RVWS`/`ELIF`/`LRTC` sub-docs, ~64 KB `LLIF` blob. Zone payload records (`tadR`/`gfxt`/`xtrc`/`pmas`/…): framing **unknown** |
| `.scw` **LRTC** (global/boot/character) | `Data/GlobScen.scw`, `Data/LoadOnce.scw`, `Data/Player/{Char,Foll}_*.scw` (24) | [scw.md §LRTC](scw.md) | same | Header + first `COHS` index chunk decoded; walk stops at 0x60 — deeper chunk stream **unknown** |
| `.GEO` **MOEG** mesh | `Data/Game/fro/Ring.GEO` (only sample) | [geo-txw.md](geo-txw.md) | [`tools/geo2obj.py`](../../tools/geo2obj.py) | Fully decoded on the single sample: 16 B header, 0x20-stride verts (pos/nrm/uv), u32 count + u16 tris; exact size arithmetic. Multi-mesh/winding **unknown** |
| `.txw` **TXW** texture bank | `Data/Game/fro/Ring.txw` (only sample) | [geo-txw.md](geo-txw.md) | [`tools/txw2png.py`](../../tools/txw2png.py) | Chunks `HEAD/TXHE/CLHE/TXDA/CLDA` + 80 B entries decoded; formats id 1=DXT1, 2=DXT3 verified visually (gold rune band + glow). Palettes/mips/other ids **unknown** |
| `.avi` FMVs | `Data/Movies/*.avi` (21), `Data/Special/*.avi` (16) | [fmv-pipeline.md §Container](../analysis/fmv-pipeline.md) | (headers parsed ad hoc; no extractor needed — stock AVI) | Video-only DivX5 `DXGM` 512×480/448 23.976/29.97 fps, `00dc` + `idx1`; FMV audio lives in game banks, not the AVIs [observed] |
| `.pac` archives | retail ISOs: `data_1.pac` (Disc 1), `data_2.pac` (Disc 2), `data_3.pac` (PlayDisc) | [pac.md](pac.md) | [`tools/unpac.py`](../../tools/unpac.py) | **Fully decoded + acceptance-met**: 128 B ASCII id header; `[u32 uncomp][u32 clen][zlib-or-stored]` block stream; 3 packs = one logical stream; 99-entry TOC (path/attrs/FILETIME-low7/size) then 83 raw members in TOC order, 2 split across pack edges; all members SHA-256-identical to `Data/`. id-header/attrs semantics + 4 B data_3 trailer **unknown** |
| `Input.ini` | install root | [misc.md §Input.ini](misc.md) | — | Schema + full token grammar + default bindings [observed]; parser semantics in packed exe **unknown** |
| `filelist.txt` / `manifest.txt` | install root | [misc.md](misc.md) | — | Installer manifest (incl. `data_N.pac` evidence) + post-expand inventory [observed]; column ints **unknown** |
| `00000000.016` / `.256` | install root | [misc.md](misc.md) | — | Plain 8-bpp 640×480 BMPs [observed]; producer = SafeDisc resources [inferred] |
| `SECDRV.SYS` / `DrvMgt.dll` | install root | [misc.md](misc.md) | — | SafeDisc 3 driver + loader (`Setup`/`Remove` exports) [observed] |
| `Support/*` (EReg, EasyInfo, readme, EULA, config.xml) | `Support/` | [misc.md](misc.md) | — | EA Reg 2.0 + support payloads identified; per-file roles of `go_ez.exe` etc. inferred |
| DivX middleware PE trio | install root | [companion-dlls.md](../analysis/companion-dlls.md) + `include/rotk/*.h` | — | Complete export tables (16+22+4), call graph, verdicts (C8, done) |

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
2. COTS zone-payload record framing; `igc_*_bank` audio internal format (likely the
   missing FMV-audio answer from D3; `pmas`/`ONOS` tags suggest a sample directory).
3. LRTC chunk stream beyond the first `COHS` index (affects GlobScen/LoadOnce/Player).
4. Unpacked `ROTK.exe` → resolves `Input.ini` parsing, `.vid` question, output-format
   enums, `u32@0x04`, TXW entry filler fields (`docs/research/safe-disc.md` plan).

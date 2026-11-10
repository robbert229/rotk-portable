<img src="assets/icon.svg" width="64" height="64" alt="">

# rotk-portable

Reverse-engineering effort to decompile and reimplement **The Lord of the Rings: The Return of the King** (EA Games, 2003) PC release, with the goal of a portable, modern reimplementation of the game engine.

## Target

| | |
|---|---|
| Executable | `ROTK.exe` (PE32, x86, image base `0x400000`) |
| SHA-256 | `95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2` |
| Build timestamp | 2003-10-05 19:26 UTC (release v1.0, readme dated 2003-11-05) |
| Install path | `EA GAMES/LOTR The Return of the King tm/` (Wine prefix) |
| Analysis tool | REA 6.7.0 / Ghidra 12.1.4 (Evidence `ev_4ec57b43…`) |

## Original build toolchain (findings)

Established from PE headers, CodeView debug directory, embedded source paths, and string inventory:

- **Compiler: Microsoft Visual C++ .NET 2002 (MSVC 7.0 / cl 13.00)**
  - PE optional-header linker stamp **7.00** (`link.exe` 7.00 of VS .NET 2002); EA-built helpers (`eauninstall.exe`, `rotk_uninst.exe`) share the same 7.00 stamp, while bundled middleware is linker 6.00 (VS 6) — consistent, not SafeDisc noise.
  - Statically linked MSVC CRT (`Microsoft Visual C++ Runtime Library` asserts; `CorExitProcess` + `mscoree.dll` = VC7 CRT startup's managed-app probe, **not** evidence of .NET — CLR data directory is zero).
  - **Rich header (observed):** C compiler `Utc13_C` build **13.00.9466** (VS .NET 2002 RTM) × 563 objects, C++ × 10, MASM 7.00 × 43, linker 7.00.9466. Matching toolchain: VS .NET 2002 RTM, *not* SP1 (13.00.9955). The project recompiles with [`archaic-msvc/msvc700`](https://github.com/archaic-msvc/msvc700) (13.00.9466, fetched locally, never committed) and targets byte-matching functions. Details: [`docs/roadmap.md`](docs/roadmap.md) WP-0.6 / R-2.
  - PDB: `f:\EAThirdPerson\lotr\rotk\code\Project\VisualStudio\Win\EN\ROTK_EN_Fin_Win_DotNet.pdb` (RSDS, GUID `eced3210-3532-49d3-a2bb-a850a135a08a`, age 0x2f). "DotNet" here denotes the Visual Studio .NET build configuration; the image is fully native.
- **Engine: in-house "EAThirdPerson" engine (console-first, PC-ported)**
  - Recovered source tree `EAThirdPerson\lotr\rotk\code\` with modules: `Kernel` (EntityManager, VisualEntity, MessageManager, TriggerManager…), `Hi-Rendering` / `Lo-Rendering` (shader objects incl. `WeightedSkinCalc_SSE`), `Animation/ChrCntl_AnimLib` (SKA skeletal format), `Actors`, `Physics`, `Collision`, `SFX` (particle effects), `DTB` (data tables: Weapon, Abilities, Upgrade…), `UI` (Hud), `Camera`, `Lib` (UObject, UHeap, UMemPool, UBTree), `RCMP` (audio codec, `rcmp_mad_codec.c`), and a `LL` platform-abstraction layer with `_Win.c` backend variants (console `Memory_Card` layer ported to Win).
  - Sources are **C** (`.c` files throughout); dev roots `f:\EAThirdPerson\…` (build box) and `C:\Dev\lotr\rotk\`.
- **Graphics / input / audio:** Direct3D 8 (`Direct3DCreate8`, `IDirect3D*8` refcount errors), DirectInput 8, DirectSound 8 + DirectMusic; **Creative EAX Unified 8** via `eax.dll` (`EAXDirectSoundCreate8`, EAXUnified8 COM classes).
- **Video:** DivX FMVs through `DivxMediaLib.dll` + `DivxDecoder.dll` (`LLVideoDivX_Win.c`), not Bink.
- **DRM / install:** **SafeDisc** (`SECDRV.SYS` = Macrovision `secdrv.sys`, `DrvMgt.dll` loader, `stxt774`/`stxt371`/`tdb` sections, scrambled subsystem/OS fields, relocated+encrypted import dir, entry stub in `stxt371`); EA Reg 2 online activation (`Support/EReg.exe`, `GAME-LOTR-ROTK`).

### Supporting binaries

| File | Toolchain | Note |
|---|---|---|
| `eax.dll` | linker 6.00 (VS6), 2003-08-15 | Creative EAX Unified 8 wrapper over DirectSound8 |
| `DivxDecoder.dll`, `DivxMediaLib.dll`, `FileParser.dll` | linker 6.00, 2003-08-14 | In-game DivX playback stack |
| `DrvMgt.dll` | linker 6.00, 2003-07-25 | SafeDisc driver manager (installs/starts `SECDRV.SYS`) |
| `eauninstall.exe` | linker 7.00, 2003-10-02 | EA "incremental installer7" (`d:\installer\…\eauninstall7.pdb`), bundles zlib 1.1.4 |
| `rotk_uninst.exe` | linker 7.00, 2003-10-05 | EA PCExtras uninstaller (`c:\EAThirdPerson\lotr\PCExtras\…`) |

## Game data formats (specs in [`docs/formats/index.md`](docs/formats/index.md))

| Format | Status | Spec / tool |
|---|---|---|
| `Data/Game/**/*.scw` (COTS missions) | container decoded (TOC, zone/bank records, embedded docs) | `docs/formats/scw.md` · `tools/scwdump.py` |
| `GlobScen.scw`, `LoadOnce.scw`, `Data/Player/*.scw` (LRTC) | header + first chunk decoded | same |
| `.GEO` / `.txw` (Ring samples) | fully decoded on the single sample; OBJ/PNG exporters | `docs/formats/geo-txw.md` · `tools/geo2obj.py`, `tools/txw2png.py` |
| `data_1..3.pac` (retail ISOs) | fully specced: id header + zlib block stream; one continuous logical stream, 99-entry TOC in data_1, 83 raw members verified byte-identical to install | `docs/formats/pac.md` · `tools/unpac.py` |
| `Data/Movies`, `Data/Special` AVIs | video-only DivX5 `DXGM` containers measured | `docs/analysis/fmv-pipeline.md` |
| `Input.ini`, `filelist.txt`, `manifest.txt`, `00000000.*`, `Support/*` | provenance + schemas documented | `docs/formats/misc.md` |

## Companion DLLs (DivX stack)

Analyzed in [`docs/analysis/companion-dlls.md`](docs/analysis/companion-dlls.md)
(dossiers, export tables, call graph), [`docs/analysis/fmv-pipeline.md`](docs/analysis/fmv-pipeline.md)
(how `ROTK.exe` drives the stack), with reconstructed C headers in `include/rotk/`.
`FileParser.dll` verdict: AVI splitter of the DivX stack, **not** an archive reader.

## Decompilation status

Full plan, work packages and status board: [`docs/roadmap.md`](docs/roadmap.md). Rules for agents working on it: [`docs/agent-playbook.md`](docs/agent-playbook.md).


- [x] Target identity & toolchain identification (this document)
- [x] Companion DLL analysis — C8/D1–D4 (dossiers, headers, FMV pipeline, FileParser verdict)
- [x] Data format parsers — C7/D5 `.scw`, D7 `.GEO`/`.txw`, D8 misc (`tools/`, specs in `docs/formats/`)
- [x] `.pac` archive extraction — C7/D6 done from retail ISOs: spec in `docs/formats/pac.md`, extractor `tools/unpac.py` (all 83 members SHA-256-verified vs installed tree)
- [ ] Defeat SafeDisc wrapper for analysis: recover original entry point, real import table (IAT is trimmed to ~16 thunks; imports live in `stxt371`), unpack dump or runtime capture — plan in [`docs/research/safe-disc.md`](docs/research/safe-disc.md)
- [ ] Full Ghidra function recovery (only 58 procedures discovered so far due to packing)
- [ ] Zone-payload / LRTC / audio-bank deep formats (follow-ons in `docs/formats/index.md`)
- [ ] Engine reimplementation plan (EAThirdPerson module map above is the scaffold)

## Notes

- **No copyrighted game assets are committed.** Sample files (`Ring.GEO`, `Ring.txw`,
  `LoadOnce.scw`, renders) live under gitignored `assets/samples/` / `out/` and are
  regenerated from your own retail discs with `tools/unpac.py`
  (commands in [`docs/formats/index.md`](docs/formats/index.md)).
- SafeDisc (`secdrv.sys`) is unsupported on modern Windows/Wine without third-party shim; analysis so far is static.
- The real code is encrypted/packed by SafeDisc; meaningful decompilation requires an unpacked image (e.g., dumped from a running process under a SafeDisc-compatible layer).
- Reported as **SafeDisc v3** (GameCopyWorld, PCGamingWiki); no plaintext `SD2`/`SafeDisc` marker on disk corroborates v3 in-place encryption. No public tool auto-unpacks v3 — the plan is *run then dump* (SafeDiscLoader2 / SafeDiscShim on a Windows VM → x32dbg to OEP → Scylla dump + IAT rebuild; validate ≈ 2,874,232 bytes, the size of the known no-CD exe). Full source-cited research: [`docs/research/safe-disc.md`](docs/research/safe-disc.md).

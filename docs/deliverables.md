# ROTK Portable — Deliverables: Companion DLLs (C8) → Data Formats (C7)

Concrete deliverables for the unprotected-assets track (no SafeDisc dependency).
Each deliverable lists its artifact, acceptance criteria, and evidence discipline.
Status: `[ ]` planned · `[~]` in progress · `[x]` done · `[B]` blocked.

Conventions:
- Every claim in a spec carries a tag: **observed** (byte/string/provider evidence, with REA Evidence ID or file offset), **inferred**, or **unknown**.
- Tools are dependency-free `python3` scripts in `tools/`; they never write into the game prefix (read-only corpus).
- Large corpus files stay in the Wine prefix (referenced by path + SHA-256); small samples (<1 MB) are kept locally under `assets/samples/` and are **never committed** (copyrighted, gitignored) — regenerate with `tools/unpac.py`.

Corpus baseline (installed retail v1.0):

| Asset | Count / size | Notes |
|---|---|---|
| `ROTK.exe` | 2,874,240 B | SafeDisc-locked, deferred to dump phase |
| `FileParser.dll` | 86,016 B · sha256 `196fb53a…` | 16 **named** `divx*` exports (AVI splitter — see D4), VS6, 2003-08-14 |
| `DivxMediaLib.dll` | 86,016 B · sha256 `ed2c45bc…` | named `Divx*/divx*` exports, VS6, 2003-08-14 |
| `DivxDecoder.dll` | 397,312 B · sha256 `cc68db04…` | `DivxDecode`, `InitializeDivxDecoder`, VS6, 2003-08-14 |
| `Data/**/*.scw` | 44 files, ~1.3 GB | scenes (`GlobScen.scw`, `LoadOnce.scw`, 13 mission dirs) |
| `Data/Game/fro/Ring.GEO` | 32 KB | only GEO sample on disk |
| `Data/Game/fro/Ring.txw` | 28 KB | only TXW sample on disk |
| `Data/{Movies,Special}/*.avi` | 37 files, ~775 MB | DivX FMVs (consumer of the DLLs) |
| `data_*.pac` | **0 — absent** | expanded by installer; original disc/ISO required |

## Phase C8 — Companion DLL analysis

- [x] **D1 — DLL dossiers.** `docs/analysis/companion-dlls.md`: per DLL — identity (hash/headers), complete export table with per-function role, imports, string-derived feature map, REA/Ghidra evidence IDs. *Accept: all 3 DLLs covered; every export has a role tag; no untagged claims.*
- [x] **D2 — Reconstructed API headers.** `include/rotk/divx_media.h`, `include/rotk/divx_decoder.h`, `include/rotk/file_parser.h`: C prototypes per export (calling convention where inferable, params/return from stack analysis), plus recovered structs. *Accept: 31 exports (16+15+5+…) each documented or marked unknown; structs carry byte-offset evidence.*
- [x] **D3 — FMV pipeline note.** `docs/analysis/fmv-pipeline.md`: how `ROTK.exe` (`LLVideoDivX_Win.c`, `LLVideo.c`) drives the stack — call order `OpenDivxFile → DivxGetContentInfo → DivxSetVideoBuffer → DivxNextFrame/DivxDoFrame → CloseDivxFile`, codec/container expectations (DivX 4/5 + audio), EAX/DirectSound interplay pointers. *Accept: sequence diagram + per-call evidence from both sides (caller strings/imports, callee exports).*
- [x] **D4 — FileParser.dll verdict.** Determine whether `FileParser.dll` is (a) an extra DivX-stack component (same build date/size as DivxMediaLib), (b) an archive/`.pac` reader (name + installer-era build), or (c) something else; document its 16 functions. **Result: (a) — AVI splitter/demuxer of the DivX stack** (12/16 exports imported by DivxMediaLib; AVI diagnostic strings; see dossier). *Accept: a supported verdict with evidence and confidence; per-function one-line purpose.*

## Phase C7 — Data format specs + tools

- [x] **D5 — `.scw` scene format + `tools/scwdump.py`.** Header (magic/version/section table), entity/spawner records, texture/geometry/AI references, region blocks; validated against `GlobScen.scw`, `LoadOnce.scw`, and ≥2 mission files. *Accept: `tools/scwdump.py <file>` prints named fields; every documented field cites file-offset evidence; size arithmetic reconciles (record counts × stride ≈ region size).* ~~Commit `GlobScen.scw` to `assets/samples/` if <1 MB~~ — superseded: samples are copyrighted, now gitignored (see ground rules).
- [x] **D6 — `.pac` archive format + `tools/unpac.py`.** **[DONE — user-supplied retail ISOs]** Three-pack layout spec'd: 128-byte ASCII id header + `[u32 uncomp][u32 clen][zlib-or-stored]` block stream; the three packs form one continuous logical stream — `data_1` holds the 99-entry TOC (path/attrs/FILETIME-low7/size) followed by all 83 members concatenated raw in TOC order, split mid-file across pack edges at `min04.scw` and `isenfmv1.avi` (see [formats/pac.md](formats/pac.md)). `tools/unpac.py` (stdlib) lists/dumps/extracts. **Acceptance met: all 83 members SHA-256-identical to installed `Data/` files.**
- [x] **D7 — `.GEO`/`.txw` + exporters.** `docs/formats/geo-txw.md`, `tools/geo2obj.py`, `tools/txw2png.py` — parse headers, vertex/index buffers, texture blocks; export the Ring. *Accept: both tools run on the only samples; header table with offsets; single-sample limits flagged as unknowns; exported OBJ/PNG visually plausible (screenshots kept locally — gitignored).*
- [x] **D8 — Misc file provenance & formats.** `docs/formats/misc.md`: `Input.ini` schema, `00000000.016`/`.256` (SafeDisc-generated vs game cache — determine producer with evidence), `filelist.txt`/`manifest.txt` semantics, `Support/` XML/EREg artifacts. *Accept: each top-level file has an identified producer + purpose tag.*
- [x] **D9 — Format registry + README sync.** `docs/formats/index.md` summarizing all specs with status; README "Decompilation status" checklist updated to reference deliverable IDs. *Accept: README + index consistent with actual doc set.*

## Dependencies & ordering

```
D1 ─→ D2, D3, D4          (dossiers first; everything else cites them)
D5 ─→ (feeds exe phase)   (largest data payload; independent of C8)
D6 done (retail ISOs supplied)
D7 independent            (tiny samples, quick win)
D8 anytime                D9 last, after each spec lands
```

Recommended order: **D1 → D4 (FileParser verdict) → D7 (quick win) → D5 (core) → D8 → D9**; D6 landed with the user-supplied ISOs.

## Explicitly out of scope (this plan)

- SafeDisc dump phase (see `docs/research/safe-disc.md`) — separate track.
- `.avi` reimplementation (standard DivX 4/5; only D3 documents usage).
- DTB data-table semantics (Weapon/Abilities/Upgrade) — needs the unpacked exe to see the readers; recorded as a known follow-on.

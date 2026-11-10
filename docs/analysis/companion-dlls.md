# Companion DLL dossiers — FileParser / DivxMediaLib / DivxDecoder

C8/D1 deliverable ([spec](../deliverables.md#phase-c8--companion-dll-analysis)).
All three DLLs are unprotected VS6 x86 PEs (linker 6.00, timestamp 2003-08-14), analyzed
statically with REA/Ghidra 12.1.4. Every claim is tagged **observed** / **inferred** / **unknown**.

## Call graph

```
ROTK.exe  (LLVideoDivX_Win.c / LLVideo.c)
   │  OpenDivxFile, DivxPlay/Pause/Resume/Stop, DivxNextFrame, DivxDoFrame,
   │  DivxGetContentInfo, DivxSetVideoBuffer/AudioBuffer/OutputVideoFormat, …   [observed: ROTK.exe strings]
   ▼
DivxMediaLib.dll          player/orchestrator (threads, buffering, play control)
   ├──► FileParser.dll    AVI container splitter + frame/buffer manager          [observed: import table]
   │       12 of its 16 exports are imported by DivxMediaLib
   └──► DivxDecoder.dll   DivX 4/5 video codec (Decode/Init/Uninit/SetOutputFormat)
           4 exports imported by DivxMediaLib
```
**Observed**: import tables (pefile) of each DLL; DivxMediaLib imports `DivxDecode`,
`InitializeDivxDecoder`, `UnInitializeDivxDecoder`, `SetOutputFormat` from
`DivxDecoder.dll` and 12 `divx*` functions from `FileParser.dll`.
The game never imports FileParser/DivxDecoder directly (no such strings in ROTK.exe imports).

## Identity

| | FileParser.dll | DivxMediaLib.dll | DivxDecoder.dll |
|---|---|---|---|
| SHA-256 | `196fb53afbf15c02ffc27cba3b4b7ad66b632e70ad68427d042813a8996acf67` | `ed2c45bcb3beab5fd64e51acd7cefc06f3cdb888f21f03d19ae16836dee35ecd` | `cc68db0409234d3cd2d2282b0e09dff95acb98ea07fddf08f503ec95d17c4971` |
| Size | 86,016 | 86,016 | 397,312 |
| Linker | 6.00 (VS6), 2003-08-14 16:59 | 6.00, 2003-08-14 16:59 | 6.00, 2003-08-14 16:59 |
| Image base | 0x10000000 | 0x10000000 | 0x10000000 |
| Sections | .text 48K, .rdata 8K, .data 25K, .reloc, **tdb** | .text 44K, .rdata 12K, .data 28K, .reloc, **tdb** | .text 232K, .rdata 76K, .data 82K, .reloc, **tdb** |
| Ghidra procs / strings | 341 / 203 | 303 / 234 | 467 / 132 |
| REA Evidence | `ev_7bbf06882e42bc25…` | `ev_bbbfa1074e47a3d3…` | `ev_b570f9bef37e9948…` |
| CRT | static MSVC6 CRT (R60xx strings, `Microsoft Visual C++ Runtime Library`) | same | same |

> **Observation (cross-cutting):** all three unprotected DLLs contain a 4 KB `tdb`
> section — the same oddly-named section seen in the SafeDisc-wrapped `ROTK.exe`.
> Therefore `tdb` is an artifact of EA's build/post-link pipeline, **not** of SafeDisc.
> Its producer/purpose: **unknown**.

## FileParser.dll — AVI splitter / demuxer + buffer manager

**D4 verdict (this document closes D4):** FileParser.dll is **not** an archive/`.pac`
reader. It is the **AVI container parser ("splitter") and frame-buffer manager of the
DivX playback stack**. Confidence: high.
Evidence: (a) 12 of 16 exports imported by DivxMediaLib.dll [observed-import table];
(b) its private strings are AVI-parsing diagnostics: `"Not an AVI file"`,
`"AVI file has no MOVI list (corrupted?)"`, `"AVI file has no header list (corrupted?)"`,
`"AVI file has no video data"`, `"Not DIVX 5.0 encoded"`, `"operation needs an index"`,
`"Error writing index (file may still be useable)"` [observed-strings, ev_7bbf0688…];
(c) export names `divxSplitterFileParse/Init/Uninitialise`, `divxBufManager*`,
`divxLocate{Video,Audio}Frame`, `divxReadFrame`, `divxFill{Video,Audio}DecodeBuffer` [observed].

### Exports (16) — roles

| Export | RVA | Role | Tag |
|---|---|---|---|
| `divxSplitterInit` | 0x3B50 | Initialize splitter state | inferred (name+call order) |
| `divxSplitterFileParse` | 0x3A90 | Open+parse AVI (`RIFF`/`AVI ` LIST hdrstr/movi/idx1), build frame index | inferred (strings: hdr list/MOVI/index errors) |
| `divxSplitterUninitialise` | 0x3DB0 | Teardown | inferred |
| `divxBufManagerInit` / `UnInit` | 0x2680 / 0x2A90 | Create/destroy circular audio+video decode buffers | inferred (name + `DivxSetNumAudVidBuffers` link) |
| `divxSetAudVidBuffers` | 0x2660 | Configure buffer count/sizes | inferred |
| `divxFrameReady` | 0x2C10 | Test next frame availability | inferred |
| `divxReadFrame` | 0x2BA0 | Read next compressed frame chunk from file | inferred |
| `divxLocateVideoFrame` / `divxLocateAudioFrame` | 0x3E60 / 0x3E30 | Seek by frame/sample to file offset | inferred |
| `divxFillVideoDecodeBuffer` / `divxFillAudioDecodeBuffer` | 0x3E90 / 0x3EF0 | Copy compressed frame into decoder buffer | inferred |
| `divxGetContentInfo` | 0x3F50 | Fill size/fps/frame-count/audio-info struct | inferred |
| `divxGetLastError` | 0x4030 | Last error code | inferred |
| `divxGetErrorMessage` | 0x4170 | Error code → message (table of AVI strings above) | observed (message table in .rdata) |
| `divxSetToStart` | 0x3DF0 | Rewind to first frame | inferred |

Imports: KERNEL32 only (68: file I/O incl. **overlapped** `ReadFileEx`/`CancelIo`/
`WaitForSingleObjectEx` → async file reads **observed**; heap; threads) + static CRT.

## DivxMediaLib.dll — playback orchestrator (game-facing API)

### Exports (22) — roles

| Export | Role | Tag |
|---|---|---|
| `OpenDivxFile` / `CloseDivxFile` | Open/close playback session (wraps splitter) | inferred (game strings + wrapper role) |
| `DivxGetSDKVersion` | SDK version string/code | observed-name |
| `DivxGetContentInfo` | Pass-through/extension of splitter content info | inferred |
| `DivxSetVideoBuffer` / `DivxSetAudioBuffer` / `DivxSetOutputVideoFormat` | Register destination RGBA/surface + audio format | inferred (game strings `DivxSetOutputVideoFormat`) |
| `DivxSetNumAudVidBuffers` | Buffer depth config → `divxSetAudVidBuffers` | observed (import edge) |
| `DivxPlay`/`DivxPause`/`DivxResume`/`DivxStop` | Transport control (threaded play) | inferred; threading **observed** (`CreateThread`, `WaitForMultipleObjects` imports) |
| `DivxNextFrame` / `DivxDoFrame` | Pull/advance one video frame (decode via DivxDecoder) | inferred |
| `DivxNextAudioChunk` | Pull next audio block (game feeds DirectSound) | inferred |
| `DivxGotoFrame` / `DivxGotoFrameEx` | Seek | inferred |
| `DivxModeSet` / `DivxProfile` | Playback mode / profile query | unknown |
| `DivxSetCallBackFn` | Progress/completion callback | inferred |
| `DivxGetLastError` / `DivxFormatErrorMessage` | Errors (`"%s - %s"` formatter, "Free Play stopped…" strings) | observed-strings |

Extra strings: `"Error occurred while opening the file. Probable system error"`,
`"Error occured while reading the input file."`, `"Free Play stopped due to unexpected
error."`, `"Function: DivxDoFrame"` [observed]. Imports: KERNEL32 (65, threads/events/
critical sections/clock), `FileParser.dll` (12), `DivxDecoder.dll` (4) [observed].

## DivxDecoder.dll — DivX 4/5 video codec

Exports (4): `InitializeDivxDecoder`, `UnInitializeDivxDecoder`, `SetOutputFormat`,
`DivxDecode` [observed]. 467 functions in 232 KB `.text` — consistent with a software
codec core [inferred]. Strings are CRT-only (no branding) [observed-ev_b570f9be…];
`SetOutputFormat` + game's `DivxSetOutputVideoFormat` imply a pixel-format-agnostic
RGB/blit output [inferred]. Audio is **not** decoded here (no audio imports/strings) —
MP3/audio path lived in the game's own DirectSound stack [inferred].
Exact codec lineage (OpenDivX-derived? licensed On2?): **unknown**.

## FMV consumer evidence (ROTK.exe side)

Observed in ROTK.exe strings: `OpenDivxFile`, `CloseDivxFile`, `DivxDoFrame`,
`DivxNextFrame`, `DivxNextAudioChunk`(?) , `DivxGetContentInfo`, `DivxGetLastError`,
`DivxFormatErrorMessage`, `DivxModeSet`, `DivxProfile`, `DivxSetNumAudVidBuffers`,
`DivxSetOutputVideoFormat`, `DivxSetVideoBuffer`, `DivxDecoder.dll`, `DivxMediaLib.dll`,
plus source path `LL\Win\LLVideoDivX_Win.c`. (Full caller-side sequencing → [fmv-pipeline.md](fmv-pipeline.md), D3.)

## Unknowns / next probes

- `tdb` section producer (EA pipeline) — compare `Support/*.exe` (also EA-built) for the same section.
- Per-export parameters/ABI → D2 headers via targeted Ghidra decompiles.
- `DivxModeSet`/`DivxProfile` semantics.
- Audio codec + timestamping model (game-side; needs unpacked exe or runtime trace).

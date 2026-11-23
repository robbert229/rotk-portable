# Companion DLL dossiers — FileParser / DivxMediaLib / DivxDecoder

C8/D1 deliverable ([spec](../deliverables.md#phase-c8--companion-dll-analysis)).
All three DLLs are x86 PEs with linker version 6.00 and COFF timestamps dated
2003-08-14 [observed: re/corpus/binaries.csv]. The static analysis used
REA and Ghidra 12.1.4. Claims are tagged **observed** / **inferred** / **unknown**.

## Call graph

```
ROTK.exe  (LLVideoDivX_Win.c / LLVideo.c)
   │  12 delay-load imports including OpenDivxFile, DivxNextFrame and DivxDoFrame
   ▼
DivxMediaLib.dll          player/orchestrator (threads, buffering, play control)
   ├──► FileParser.dll    AVI container splitter + frame/buffer manager
   │       12 imports from a DLL with 16 export slots
   └──► DivxDecoder.dll   DivX 4/5 video codec (Decode/Init/Uninit/SetOutputFormat)
           4 imports from a DLL with 4 export slots
```
[observed: re/corpus/pe_imports.csv and re/corpus/binaries.csv] DivxMediaLib imports
`DivxDecode`, `InitializeDivxDecoder`, `UnInitializeDivxDecoder` and `SetOutputFormat`
from `DivxDecoder.dll`, and 12 `divx*` functions from `FileParser.dll`. Neither
companion appears in the packed executable's ordinary or delay-load import directory.

## Identity

[observed: re/corpus/binaries.csv, re/corpus/pe_sections.csv, and the REA evidence
below] Section sizes are raw / virtual in bytes (hex). Export counts are address-table slots.

| | FileParser.dll | DivxMediaLib.dll | DivxDecoder.dll |
|---|---|---|---|
| SHA-256 | `196fb53afbf15c02ffc27cba3b4b7ad66b632e70ad68427d042813a8996acf67` | `ed2c45bcb3beab5fd64e51acd7cefc06f3cdb888f21f03d19ae16836dee35ecd` | `cc68db0409234d3cd2d2282b0e09dff95acb98ea07fddf08f503ec95d17c4971` |
| Size | 86,016 | 86,016 | 397,312 |
| Linker | 6.00 (VS6), 2003-08-14 16:59 | 6.00, 2003-08-14 16:59 | 6.00, 2003-08-14 16:59 |
| Image base | 0x10000000 | 0x10000000 | 0x10000000 |
| `.text` | `0xc000 / 0xbb76` | `0xb000 / 0xa0ea` | `0x3a000 / 0x39c0c` |
| `.rdata` | `0x2000 / 0x1386` | `0x3000 / 0x2670` | `0x13000 / 0x120a9` |
| `.data` | `0x4000 / 0x64b4` | `0x4000 / 0x6fac` | `0x11000 / 0x14780` |
| `.reloc` | `0x2000 / 0x130a` | `0x2000 / 0x13fe` | `0x2000 / 0x1ade` |
| Ordinary imports | 68 | 81 | 60 |
| Delay-load imports | 0 | 0 | 0 |
| Export slots | 16 | 22 | 4 |
| Ghidra procs / strings | 341 / 203 | 303 / 234 | 467 / 132 |
| REA Evidence | `ev_7bbf06882e42bc25…` | `ev_bbbfa1074e47a3d3…` | `ev_b570f9bef37e9948…` |
| CRT | MSVC 6.0 family [observed: re/corpus/libraries.csv]. Static linkage [inferred: runtime strings and import list] | same | same |

> Superseded: the earlier `tdb` section and EA post-link attribution. The three
> DLLs each have the four sections above, and the packed executable's eight
> section names also exclude `tdb` [observed: re/corpus/pe_sections.csv].

## FileParser.dll — AVI splitter / demuxer + buffer manager

**D4 verdict (this document closes D4):** FileParser.dll is **not** an archive/`.pac`
reader. It is the **AVI container parser ("splitter") and frame-buffer manager of the
DivX playback stack**. Confidence: high.
Evidence: (a) 12 imports by DivxMediaLib.dll from the 16-slot export table
[observed: re/corpus/pe_imports.csv and re/corpus/binaries.csv];
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

Imports: 68 from `KERNEL32.dll`, including `ReadFileEx`, `CancelIo` and
`WaitForSingleObjectEx` [observed: re/corpus/pe_imports.csv]. [inferred: overlapped
file reads from these APIs.]

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
| `DivxNextAudioChunk` | Pull next audio block | inferred |
| `DivxGotoFrame` / `DivxGotoFrameEx` | Seek | inferred |
| `DivxModeSet` / `DivxProfile` | Playback mode / profile query | unknown |
| `DivxSetCallBackFn` | Progress/completion callback | inferred |
| `DivxGetLastError` / `DivxFormatErrorMessage` | Errors (`"%s - %s"` formatter, "Free Play stopped…" strings) | observed-strings |

Extra strings: `"Error occurred while opening the file. Probable system error"`,
`"Error occured while reading the input file."`, `"Free Play stopped due to unexpected
error."`, `"Function: DivxDoFrame"` [observed]. Imports: KERNEL32 (65, threads/events/
critical sections/clock), `FileParser.dll` (12), `DivxDecoder.dll` (4) [observed: re/corpus/pe_imports.csv].

## DivxDecoder.dll — DivX 4/5 video codec

Exports (4): `InitializeDivxDecoder`, `UnInitializeDivxDecoder`, `SetOutputFormat`,
`DivxDecode` [observed]. 467 functions in 232 KB `.text` — consistent with a software
codec core [inferred; raw size observed: re/corpus/pe_sections.csv]. The string
scan records CRT fingerprints and the `DivxDecode` SDK anchor
[observed: re/corpus/libraries.csv].
`SetOutputFormat` + game's `DivxSetOutputVideoFormat` imply a pixel-format-agnostic
RGB/blit output [inferred]. The decoder imports 60 functions, all from `KERNEL32.dll`
[observed: re/corpus/pe_imports.csv]. [inferred: video-only role based on its
exports and the shipped AVIs.]
Exact codec lineage (OpenDivX-derived? licensed On2?): **unknown**.

## FMV consumer evidence (ROTK.exe side)

The packed executable's 12 delay-load imports from `DivxMediaLib.dll` are listed in
[fmv-pipeline.md](fmv-pipeline.md#caller-side-rotkexe--evidence). The earlier call
sketch included threaded transport functions and tentatively identified
`DivxNextAudioChunk`. The visible import directories contain none of those names
[observed: re/corpus/pe_imports.csv]. [unknown: additional runtime-resolved calls.]

## Unknowns / next probes

- Meaning of the packed executable’s `tdb` overlay string hits (see [SafeDisc research](../research/safe-disc.md#packed-section-map)).
- Per-export parameters/ABI → D2 headers via targeted Ghidra decompiles.
- `DivxModeSet`/`DivxProfile` semantics.
- Audio codec + timestamping model (game-side; needs unpacked exe or runtime trace).

# ROTK FMV playback pipeline (D3)

How `ROTK.exe` drives the DivX stack (`DivxMediaLib.dll` → `FileParser.dll` +
`DivxDecoder.dll`) to play Full Motion Videos. Companion to
[companion-dlls.md](companion-dlls.md) (dossiers) and the reconstructed headers in
`include/rotk/`. Claims tagged **observed** / **inferred** / **unknown**.

## TL;DR

The packed executable declares 12 delay-load imports from `DivxMediaLib.dll`,
including open/close, buffer and format setup, and the two frame functions.
The visible DivX entries omit the threaded transport API
[observed: re/corpus/pe_imports.csv]. [inferred: synchronous frame-pull playback.]
All 37 retail AVIs contain one `DXGM` video stream and zero audio streams
[observed: re/corpus/assets_avi.csv]. [unknown: FMV audio source and playback path.]

## Call sequence

```
setup                                                 [inferred: timing]
  DivxSetNumAudVidBuffers(nvid, naud)                  [observed-import] → FileParser divxSetAudVidBuffers

per FMV play ("Data/Movies/%s.avi")                    [observed: format string in ROTK.exe]
  OpenDivxFile(path) ────────────────────────────────► divxSplitterFileParse(path,…,slot,…)  [observed: callee decompile]
                                                     └► divxBufManagerInit(slot, path)        [observed: callee decompile]
  DivxGetContentInfo(h, &info)                         [observed-import] → splitter divxGetContentInfo [observed decompile]
  DivxSetOutputVideoFormat(h, fmt)                     [observed-import] → decoder SetOutputFormat(slot,fmt,w,h) [observed decompile]
  DivxSetVideoBuffer(h, dst)                           [observed-import] stores dst at session-slot+0x32C [observed decompile]
  DivxModeSet(…) / DivxProfile(…)                      [observed-import; semantics unknown]
  frame loop                                          [inferred: timing and call order]
      DivxNextFrame(h)  ─────────────────────────────► divxFrameReady/divxReadFrame
      │                                                 → divxFillVideoDecodeBuffer   [inferred: import edges, dossier]
      │                                                 → DivxDecode(slot,out,in)     [observed: DivxMediaLib imports DivxDecode]
      DivxDoFrame(h)      // present/convert to RGB    [observed-import]
  error checks any step:
      DivxGetLastError() / DivxFormatErrorMessage(err) [observed-import]
  CloseDivxFile(h)                                     [observed-import] → splitter + decoder teardown
```

The sketch combines delay-load names [observed: re/corpus/pe_imports.csv]
with callee-side observations and inferred caller sequencing.

## Caller side (ROTK.exe) — evidence

The packed executable exposes 10 ordinary imports across six DLLs and 21 delay-load
imports across five DLLs. `KERNEL32.dll` supplies five ordinary imports, including
`GetModuleHandleA` and `GetProcAddress`. All 12 DivX imports are declared in the
delay-load directory under `DivxMediaLib.dll`
[observed: re/corpus/binaries.csv, re/corpus/pe_imports.csv]. This supersedes the
string-only interpretation that the game binds the twelve functions manually.

| Delay-load imports [observed: re/corpus/pe_imports.csv] | Role [inferred] |
|---|---|
| `OpenDivxFile`, `CloseDivxFile` | Session open/close |
| `DivxGetContentInfo` | Mode/dimensions query |
| `DivxSetVideoBuffer`, `DivxSetOutputVideoFormat` | Destination registration |
| `DivxNextFrame`, `DivxDoFrame` | Per-frame pull and presentation |
| `DivxModeSet`, `DivxProfile`, `DivxSetNumAudVidBuffers` | Configuration |
| `DivxGetLastError`, `DivxFormatErrorMessage` | Error reporting |

The visible directories omit `DivxPlay`, `DivxPause`, `DivxResume`, `DivxStop`,
`DivxNextAudioChunk`, `DivxGotoFrame*`, `DivxSetCallBackFn`, `DivxSetAudioBuffer`
and `DivxGetSDKVersion` [observed: re/corpus/pe_imports.csv]. The frame entries
suggest that the game paces playback [inferred].

Supporting source-path strings [observed]:
`\EAThirdPerson\lotr\rotk\code\LL\LLVideo.c`,
`...\code\LL\Win\LLVideoDivX_Win.c`, `...\code\LL\SoftwareVideo\LLPictInt.c`
⇒ dedicated Windows DivX video module + a software fallback renderer.

FMV path + names [observed]: `Data/Movies/%s`, `data\movies\blakfmv1.vid`, FMV ids
`ENDFMV1 OSGIFMV2 PAT1FMV2 GATEFMV2 MTYDFMV2 HELMFMV2 ISENFMV1 ATTRFMV1 …`
(matching `Data/Movies/*.avi` stems). The `.vid` string has no install match [observed: re/corpus/filerefs.csv].
[unknown: whether it is a legacy alias or an unfinished asset path.]

## Container facts (measured from the shipped FMVs) [observed]

Parsed `RIFF/AVI ` headers of `Data/Movies/*.avi` (21 files) and `Data/Special/*.avi`
(16) [observed: re/corpus/assets_avi.csv, supplemented by the earlier AVI scan]:

| Field | Value |
|---|---|
| `strh` fccType / fccHandler | `vids` / **`DXGM`** (DivX 5.x w/ GMC family) |
| `strf` | BITMAPINFOHEADER 40 B, `biCompression='DXGM'`, bpp=24 |
| Resolution | 512×480 in 35 files. `Movies/attrfmv1.avi` and `Special/makespc1.avi` are 512×448 |
| Frame rate | 30000/1001 fps in the two 512×448 files and `Movies/rtsvid.avi`. The other 34 use 24000/1001 fps |
| Streams | **video only** — zero audio `strf`; `movi` contains only `00dc` chunks (e.g. endfmv1.avi: 2399 chunks = strh length 2399) |
| Index | `idx1` present in every declared RIFF form. A final `JUNK` chunk follows the declared form in every file (84–2,042 bytes including its header) |

[inferred: the shipped AVIs give the splitter’s audio-side exports no embedded audio to read.]

## Audio path

- The executable declares delay-load imports `acmStreamOpen`, `acmStreamSize`,
  `acmStreamPrepareHeader`, `acmStreamConvert`, `acmStreamUnprepareHeader` and
  `acmStreamClose` from `MSACM32.dll`, plus ordinal `#11` from `DSOUND.dll`
  [observed: re/corpus/pe_imports.csv]. `EAXDirectSoundCreate8` is a string
  fingerprint in `ROTK.exe` [observed: re/corpus/libraries.csv].
- The shipped AVIs have no audio streams [observed: re/corpus/assets_avi.csv]. The
  earlier `.scw` sound-bank and ACM explanation remains a hypothesis
  [inferred: candidate source and decoder from bank names and the ACM imports].
  [unknown: exact FMV audio container, codec and call path.]

## Codec / pixel-format model

- `DivxSetOutputVideoFormat(h, fmt)` forwards to `SetOutputFormat(slot, fmt, w, h)` in
  `DivxDecoder.dll`, which allocates a 0x34-byte context for `fmt==3`, else 0x28
  [observed: decompile] ⇒ at least two output formats; which FourCC/RGB layout `fmt`
  selects is **unknown** (runtime trace or deeper decompile needed).
- `DivxDecode(slot, out, in)` = dispatcher op 5; init = op 1 [observed: dossier].
- Decoder core: 467 functions, 232 KB `.text`, codec lineage **unknown** (see dossier). Raw section size is
  corroborated by re/corpus/pe_sections.csv.

## Known gaps

1. Exact caller order and delay-load resolution sites in the unpacked executable.
2. FMV audio container + codec (ACM payload location) — likely resolved by D5 `.scw` spec.
3. Meaning of `fmt` values and `DivxModeSet`/`DivxProfile` arguments.
4. Whether `.vid` files exist on the original disc (with the ISO for D6 this is checkable).

## Evidence index

| ID / source | Covers |
|---|---|
| `ev_bbbfa107…` | DivxMediaLib overview + export decompiles (OpenDivxFile, DivxNextFrame, DivxGetContentInfo, DivxSetVideoBuffer, DivxSetOutputVideoFormat, CloseDivxFile) |
| `ev_7bbf0688…` | FileParser overview, AVI strings, splitter/bufmanager decompiles |
| `ev_b570f9be…` | DivxDecoder overview + 4-export decompiles |
| `ev_4ec57b43…` | ROTK.exe PE overview (SafeDisc layout, linker 7.00) |
| [PE imports](../../re/corpus/pe_imports.csv) | Ordinary and delay-load imports for the executable and middleware |
| [AVI inventory](../../re/corpus/assets_avi.csv) | Stream, timing, dimension, index and RIFF extent data for all 37 AVIs |
| AVI header scan (this session) | strh/strf/movi/idx1 table above, all 37 shipped FMVs |

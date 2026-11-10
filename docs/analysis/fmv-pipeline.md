# ROTK FMV playback pipeline (D3)

How `ROTK.exe` drives the DivX stack (`DivxMediaLib.dll` → `FileParser.dll` +
`DivxDecoder.dll`) to play Full Motion Videos. Companion to
[companion-dlls.md](companion-dlls.md) (dossiers) and the reconstructed headers in
`include/rotk/`. Claims tagged **observed** / **inferred** / **unknown**.

## TL;DR

The game **late-binds** `DivxMediaLib.dll` (via `GetModuleHandleA`/`GetProcAddress` — the
SafeDisc outer import table only exposes those two KERNEL32 thunks), and drives playback in
a **synchronous pull model** with 12 imported functions: it opens the file, queries content
info, registers an output buffer + pixel format, then per displayed frame calls
`DivxNextFrame` + `DivxDoFrame`. It never uses the library's threaded transport
(`DivxPlay/Pause/Resume/Stop` are **not** imported). FMV `.avi` files on disk are
**video-only DivX 5-GMC**; the game's audio (incl. FMV audio) runs through its own
EAX/DirectSound + MSACM stack.

## Call sequence

```
game start (once)
  LoadLibrary("DivxMediaLib.dll")                      [inferred: name string observed; LoadLibrary not
                                                       visible in SafeDisc outer IAT — late-bind pattern]
  DivxSetNumAudVidBuffers(nvid, naud)                  [observed-import] → FileParser divxSetAudVidBuffers

per FMV play ("Data/Movies/%s.avi")                    [observed: format string in ROTK.exe]
  OpenDivxFile(path) ────────────────────────────────► divxSplitterFileParse(path,…,slot,…)  [observed: callee decompile]
                                                     └► divxBufManagerInit(slot, path)        [observed: callee decompile]
  DivxGetContentInfo(h, &info)                         [observed-import] → splitter divxGetContentInfo [observed decompile]
  DivxSetOutputVideoFormat(h, fmt)                     [observed-import] → decoder SetOutputFormat(slot,fmt,w,h) [observed decompile]
  DivxSetVideoBuffer(h, dst)                           [observed-import] stores dst at session-slot+0x32C [observed decompile]
  DivxModeSet(…) / DivxProfile(…)                      [observed-import; semantics unknown]
  loop every vsync (~23.976/29.97 fps)                 [observed: strh rate/scale]
      DivxNextFrame(h)  ─────────────────────────────► divxFrameReady/divxReadFrame
      │                                                 → divxFillVideoDecodeBuffer   [inferred: import edges, dossier]
      │                                                 → DivxDecode(slot,out,in)     [observed: DivxMediaLib imports DivxDecode]
      DivxDoFrame(h)      // present/convert to RGB    [observed-import]
  error checks any step:
      DivxGetLastError() / DivxFormatErrorMessage(err) [observed-import]
  CloseDivxFile(h)                                     [observed-import] → splitter + decoder teardown
```

Tagged evidence for each arrow is in the sections below.

## Caller side (ROTK.exe) — evidence

`ROTK.exe` (SafeDisc-packed; outer IAT = 6 DLLs / 10 thunks incl. only
`GetModuleHandleA`, `GetProcAddress` from KERNEL32 [observed: pefile import dump]).
The DivX bindings are therefore done at runtime with `GetProcAddress` [inferred from
SafeDisc packing + contiguous hint/name block].

Contiguous hint/name block in `.rdata` (string-cache lines 5643–5667, rebuildable with
`strings -n 5 ROTK.exe`) — **observed**:

| String | Role |
|---|---|
| `DivxMediaLib.dll` | module to late-bind (only DivX DLL named on the game side; `FileParser.dll`/`DivxDecoder.dll` names never appear in the exe — the library owns them [observed]) |
| `OpenDivxFile`, `CloseDivxFile` | session open/close |
| `DivxGetContentInfo` | mode/dims query |
| `DivxSetVideoBuffer`, `DivxSetOutputVideoFormat` | destination registration |
| `DivxNextFrame`, `DivxDoFrame` | per-frame pull + present |
| `DivxModeSet`, `DivxProfile`, `DivxSetNumAudVidBuffers` | config |
| `DivxGetLastError`, `DivxFormatErrorMessage` | error reporting |

Exactly **12** `Divx*` names — notably **absent**: `DivxPlay`, `DivxPause`, `DivxResume`,
`DivxStop`, `DivxNextAudioChunk`, `DivxGotoFrame*`, `DivxSetCallBackFn`,
`DivxSetAudioBuffer`, `DivxGetSDKVersion` [observed]. ⇒ the game runs its own pacing loop
(pull model), not the library's threaded player [inferred, high confidence].

Supporting source-path strings [observed]:
`\EAThirdPerson\lotr\rotk\code\LL\LLVideo.c`,
`...\code\LL\Win\LLVideoDivX_Win.c`, `...\code\LL\SoftwareVideo\LLPictInt.c`
⇒ dedicated Windows DivX video module + a software fallback renderer.

FMV path + names [observed]: `Data/Movies/%s`, `data\movies\blakfmv1.vid`, FMV ids
`ENDFMV1 OSGIFMV2 PAT1FMV2 GATEFMV2 MTYDFMV2 HELMFMV2 ISENFMV1 ATTRFMV1 …`
(matching `Data/Movies/*.avi` stems). The `.vid` extension string has no on-disk match —
**unknown** whether it is a legacy alias or an unfinished asset path.

## Container facts (measured from the shipped FMVs) [observed]

Parsed `RIFF/AVI ` headers of `Data/Movies/*.avi` (21 files) + `Data/Special/*.avi` (16):

| Field | Value |
|---|---|
| `strh` fccType / fccHandler | `vids` / **`DXGM`** (DivX 5.x w/ GMC family) |
| `strf` | BITMAPINFOHEADER 40 B, `biCompression='DXGM'`, bpp=24 |
| Resolution | 512×480 (cutscenes) or 512×448 (speech bubbles in `Special/`) |
| Frame rate | 24000/1001 = 23.976 or 30000/1001 = 29.97 fps |
| Streams | **video only** — zero audio `strf`; `movi` contains only `00dc` chunks (e.g. endfmv1.avi: 2399 chunks = strh length 2399) |
| Index | `idx1` present at EOF (splitter string: "operation needs an index") |

⇒ `FileParser.dll`'s audio-side exports (`divxLocateAudioFrame`,
`divxFillAudioDecodeBuffer`) are dead weight for ROTK's shipped FMVs [observed + inferred].

## Audio path

- Game imports `MSACM32.dll` `acmStreamOpen/PrepareHeader/Convert/Size/Close` and
  `DSOUND.dll`, plus `EAXDirectSoundCreate8` [observed: ROTK.exe strings], and its audio
  engine logs `audio: play ig stream`, `prime vo`, `play primed by name` [observed].
- FMV `.avi`s carry **no audio** [observed]. FMV audio is therefore stored elsewhere —
  most plausibly in the `.scw` sound banks (`Data/LoadOnce.scw` etc.) and decoded via
  ACM [inferred; exact container = **unknown**, a target of the D5 `.scw` work].
- `DivxNextAudioChunk` exists in DivxMediaLib but is not imported by the game [observed].

## Codec / pixel-format model

- `DivxSetOutputVideoFormat(h, fmt)` forwards to `SetOutputFormat(slot, fmt, w, h)` in
  `DivxDecoder.dll`, which allocates a 0x34-byte context for `fmt==3`, else 0x28
  [observed: decompile] ⇒ at least two output formats; which FourCC/RGB layout `fmt`
  selects is **unknown** (runtime trace or deeper decompile needed).
- `DivxDecode(slot, out, in)` = dispatcher op 5; init = op 1 [observed: dossier].
- Decoder core: 467 functions, 232 KB `.text`, no branding strings — codec lineage
  **unknown** (see dossier).

## Known gaps

1. Exact `GetProcAddress` site names/order — needs unpacked exe (`docs/research/safe-disc.md`).
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
| pefile dump (this session) | outer IAT (10 thunks incl. GetProcAddress), 3-DLL DivX import graph of the middleware |
| AVI header scan (this session) | strh/strf/movi/idx1 table above, all 37 shipped FMVs |

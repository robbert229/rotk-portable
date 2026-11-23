# Third-party library corpus

[observed: the retail install yielded 14 EXE/DLL files and one driver.
The packed ROTK.exe SHA-256 is
`95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2`.
All offsets below and in [libraries.csv](../../re/corpus/libraries.csv)
are file offsets. The file hashes for the shipped middleware references
are in [reference_sources.csv](../../re/corpus/reference_sources.csv).]

`make libscan` scans the install read-only using `ROTK_GAME_DIR`. The CSV
records each anchor at its byte offset. A literal, table, import or linker
record proves the corresponding bytes are present. Its provenance and runtime
role may require other evidence. The `import` rows cover named modules in the
ordinary PE import directory. The packed main EXE's API strings are recorded
as strings.

## Main executable

| Library | Evidence and version |
| --- | --- |
| Microsoft CRT | [observed: runtime banner at file+0x146f04 and Linker700 9466 at file+0xf8.] [inferred: static VC7.0 RTM CRT, consistent with `libcmt.lib`; see the startup landmarks in the [toolchain notes](../research/toolchain.md).] |
| D3DX8 | [observed: 288 bytes at file+0x14b260 match the SHA-256 of section 3 (`.rdata`) in `d3dxmathx3d.obj` from the pinned `d3dx8.lib`; `DisableD3DXPSGP` is at file+0x14b230.] [inferred: statically linked D3DX8 math code.] [unknown: exact retail SDK release. The reference math member is stamped C++ 13.00.9177, while the game records C++ 9178 and 9466 and an older VC6 object.] |
| DXErr8 | [observed: `DMUS_E_INVALID_CONTAINER_OBJECT` at file+0x14bf2c and `D3DXERR_CANNOTATTRSORT` at file+0x14cb5c also occur in the pinned `dxerr8.lib`. A local COFF comparison found hundreds of matching 32-byte windows in the diagnostic pool.] [inferred: linked DXErr8 error lookup.] [unknown: retail archive build.] |
| dxguid | [observed: the `DS3DALG_HRTF_LIGHT` and `IID_IDirectInput8A` data at file+0x14b3cc and file+0x14b4fc match their 16-byte sections in the pinned `dxguid.lib`.] [inferred: the run of adjacent DirectSound and DirectInput GUIDs is compatible with linked `dxguid` data.] [unknown: whether the definitions came from this archive or a different build or source.] |
| DirectX / Windows audio | [observed: `Direct3DCreate8` and `DirectInput8Create` at file+0x1586ca and file+0x1586dc, and `DSOUND.dll` / `MSACM32.dll` at file+0x158310 / file+0x1582e0.] [inferred: DirectX 8 API and Windows ACM dependencies.] [unknown: exact DirectX SDK release and a stable official installer URL.] |
| libmad | [observed: game source path `RCMP/rcmp_mad_codec.c` at file+0x13dc88.] [inferred: game wrapper for a MAD MPEG audio decoder.] [unknown: compiled decoder provenance and exact version. The 0.15.0b reference table hashes returned zero matches in the packed image.] |
| DivX playback SDK and EAX Unified | [observed: `OpenDivxFile` at file+0x158848 and `EAXDirectSoundCreate8` at file+0x138760.] [inferred: dependencies on shipped `DivxMediaLib.dll` and `eax.dll`, supported by the [FMV pipeline](../analysis/fmv-pipeline.md).] |
| SafeDisc | [observed: section names `stxt774` and `stxt371` at file+0x300 and file+0x328.] [inferred: the SafeDisc wrapper documented in the [target summary](../../README.md#original-build-toolchain-findings).] [unknown: exact wrapper build.] |

## Companion binaries and helpers

[inferred: CRT versions below use the runtime banner, the image's Rich
compiler/linker family and the ordinary import table. The banner occurs in
both VC6 and VC7. Exact VC6 CRT builds and CRT archive selections are unknown.]

| Binary | Third-party content and evidence |
| --- | --- |
| `DivxDecoder.dll` | [observed: `DivxDecode` at file+0x4d060 and CRT banner at file+0x4c67c.] [inferred: DivX 4/5 decoder family and static VC6-family CRT.] [unknown: exact codec release.] |
| `DivxMediaLib.dll` | [observed: DivX playback SDK with `DivxDecoder.dll` and `FileParser.dll` imports at file+0xdf0a and file+0xe034. `DivxGetSDKVersion` at file+0xe56a maps to file+0x2bc0, where the getter writes 6 to a non-null output pointer.] [inferred: SDK interface value 6; static VC6-family CRT, banner at file+0xd9ec.] [unknown: product release corresponding to that interface value.] |
| `FileParser.dll` | [observed: `divxSplitterFileParse` export and `Not DIVX 5.0 encoded` diagnostic in the [DLL dossier](../analysis/companion-dlls.md#fileparserdll--avi-splitter--demuxer--buffer-manager); CRT banner at file+0xd918.] [inferred: DivX SDK AVI splitter and static VC6-family CRT.] [unknown: splitter build.] |
| `eax.dll` | [observed: Creative EAX Unified file version **3.066** at file+0x1f1c4, `EAXDirectSoundCreate8` at file+0x1959e, CRT banner at file+0x189b4. Version resources cross-checked in REA evidence `ev_1adb30c87bf731983eacf7883c710e4aceef86cd1e53c2ce4c39a1584389c177`.] [inferred: static VC6-family CRT.] |
| `DrvMgt.dll` | [observed: `SECDRV.SYS` at file+0x68cd, service-control imports and CRT banner at file+0x5c4c.] [inferred: SafeDisc driver manager and static VC6-family CRT.] [unknown: driver manager build.] |
| `SECDRV.SYS` | [observed: Macrovision version **3.19.000** at file+0x2884 and `ntoskrnl.exe` kernel import.] [unknown: additional library provenance.] |
| `eauninstall.exe` | [observed: zlib **1.1.4** inflate banner at file+0x28149, IEEE CRC-32 table at file+0x27c88, MiniZip **0.15** unzip banner at file+0x27c49.] [inferred: static VC7 CRT, MFC 7.0 and ATL 7.0 from the CRT banner, `AfxWnd70s` and ATL RTTI at file+0x2a754, file+0x2868c and file+0x31a14.] |
| `rotk_uninst.exe` | [inferred: static VC7 CRT, MFC 7.0 and ATL 7.0 from the same markers at file+0x19214, file+0x180a4 and file+0x1d424.] |
| `Support/EReg.exe` | [observed: version literal **1.1.3** at file+0x154cc and inflate diagnostics at file+0x15624 and file+0x15778.] [inferred: zlib 1.1.3, static VC6-family CRT and Microsoft C++ COM support from the CRT banner at file+0x12fb4 and `_com_error` RTTI at file+0x19698.] [unknown: COM support build.] |
| `Support/EasyInfo.exe` | [observed: DirectDraw and DirectSound imports at file+0x40c7c and file+0x40c86.] [inferred: static VC7 CRT and VC7 C++ standard library from the CRT banner at file+0x3b1bc, `ios_base::failbit set` at file+0x3a0f0 and the 9466 Rich compiler records.] |
| `Support/LOTR The Return of the King tm_EZ.exe` | [inferred: static VC7 CRT, MFC 7.0 and ATL 7.0 from the markers at file+0x4d968, file+0x4996c and file+0x5c4dc.] |
| `Support/LOTR The Return of the King tm_code.exe` | [inferred: static VC7 CRT, MFC 7.0 and ATL 7.0 from the markers at file+0x20d0c, file+0x1f55c and file+0x2910c.] |
| `Support/LOTR The Return of the King tm_uninst.exe` | [inferred: static VC6-family CRT from the runtime banner at file+0x6404 and VC6 Rich records.] |
| `Support/go_ez.exe` | [inferred: static VC6-family CRT from the runtime banner at file+0x5368 and VC6 Rich records.] |

[observed: no additional Miles, Bink, Smacker, STLport, libpng, IJG JPEG,
or MD5/SHA fingerprint rows in this scan of the installed files.]
[unknown: code whose identifying strings and tables are packed, were discarded
by the linker, or fall outside the current fingerprints.]

## Reference material

- [observed: `make refs` verifies or fetches three archives into `out/refs/`.
  The [zlib fossil archive](https://zlib.net/fossils/) supplies 1.1.3 and 1.1.4.
  The latter includes MiniZip's matching `contrib/minizip/unzip.c` banner
  and labels it 0.15 beta. The [MAD 0.15.0b release](https://sourceforge.net/projects/mad/files/libmad/0.15.0b/)
  is pinned from the [VideoLAN source mirror](https://downloads.videolan.org/pub/pub/vlc/0.6.2/contrib/),
  whose archive was reachable and verified locally.] [inferred: libmad 0.15.0b
  is a comparison candidate.] [unknown: retail MAD license terms.]
- [observed: the manifest pins individual library files from the D-1
  `archaic-msvc/msvc700` checkout at
  `97fe4cdeaeb0bb934591d4b05eb52c2e8ab3e34b`.
  `make refs` verifies those files when the default toolchain exists or
  `MSVC700_DIR` points to a checkout. `make toolchain` remains the checkout
  entry point. The DirectX references are in `Vc7/PlatformSDK/lib/prerelease`.]
- [observed: proprietary DivX, EAX and SafeDisc files are pinned by installed
  path and SHA-256. The manifest leaves their upstream download URLs empty.]
  [unknown: a matching vendor archive for these retail binaries.]

[observed: the scanner matches four-byte-aligned, little-endian data by the
SHA-256 of both a 16-byte prefix and the full window. CRC-32 uses all 256
entries from reflected polynomial `0xedb88320`. MD5/SHA fingerprints are the
standard initialization vectors, with the first four MD5/SHA-1 words shared.
The libmad fingerprints use 0.15.0b's full `rq_table.dat` serialized as packed
27+5-bit or separate MSVC containers, and `D.dat` signed 32-bit values in
the three `PRESHIFT` layouts from `synth.c`. DirectX window provenance is
listed above.] [inferred: shared algorithm tables can identify an algorithm
family; library attribution needs surrounding evidence.]

## ROTK.exe object accounting

[observed: the Rich header has 563 C objects at build 9466, 4 C objects at
build 9178, and 12 C++ objects at build 9178. The pinned `libcmt.lib` has 543
C candidates stamped 9466. The [module inventory](../modules/README.md)
records 71 distinct readable game-tree C paths.]

[inferred: this scan supports the existing 71–562 estimate for game C units
in the 9466 batch. Under the estimate's assumptions, the implied non-game
pool is 1–492 of 563 objects (about 0.18–87.4%). The ends come from assuming
at least one static CRT C object and treating the 71 paths as distinct units.
The D3DX8 reference anchor is from a C++ object. The helper-only zlib and
MiniZip hits contribute no measured share of the main executable's batch.]

[unknown: the number of linked CRT, DXErr8, dxguid and libmad members in
the 9466 batch, the library attribution of the 9178 entries, and total
third-party `.text` coverage. This corpus does not narrow the object-count
range; function and archive-member matches in the repaired unpacked image
are needed for that.]

# Packed ROTK.exe module map

Image SHA-256 `95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2`.

[observed: 73 distinct paths in .rdata
(ascii). See the [path inventory](../../re/strings/source_paths.txt)
for offsets, packed-image VAs, and raw spellings].

[observed: 71 distinct `.c` paths in the inventory versus 563 C objects compiled
by cl 13.00.9466 in the retail Rich header, as recorded in
[WP-0.6](../roadmap.md) and the [README toolchain findings](../../README.md)].
[inferred: 563 is an upper bound for game units from that compiler build. It
includes static CRT objects. Game units may lack source-path literals, or their
literals may only be visible after unpacking SafeDisc-protected regions].
[unknown: how much of the gap each cause accounts for and which readable paths
have assert or `__FILE__` xrefs for WP-2.3].

## Source directories and expected units

[inferred: one expected unit per distinct observed `.c` path under `code/`. Each
top-level directory is a candidate case-sensitive symdb module. Use its recovered
spelling as the CSV stem and remove the extension from the full module-relative
path, including the module prefix, to get the qualified unit ID].

[observed: compare the recovered directories below with the Engine bullet in the
[README](../../README.md). `Project/` is represented in the inventory by the
`VisualStudio/Win/EN` PDB path].

| Module | Expected units | Recovered subtree or example | README comparison |
| --- | ---: | --- | --- |
| `Actors/` | 2 | [observed: `Actors/ActorManager.c`, .rdata file+0x001362F4] | Listed |
| `Animation/` | 4 | [observed: `ChrCntl_AnimLib/app_rotk/Character.c`, .rdata file+0x00137F50] | Listed |
| `Audio/` | 1 | [observed: `Engine/Utils/UAudMemStack.c`, .rdata file+0x001388E0] | Additional top-level directory |
| `Camera/` | 2 | [observed: `PoleCam.c`, .rdata file+0x00138A1C] | Listed |
| `Collision/` | 2 | [observed: `CollisionBroadPhase.c`, .rdata file+0x00138B10] | Listed |
| `DTB/` | 6 | [observed: `AbilitiesDTB.c`, .rdata file+0x00146858] | Listed |
| `Hi-Rendering/` | 6 | [observed: `Camera.c`, .rdata file+0x00139D80] | Listed |
| `IGC/` | 1 | [observed: `IGC.c`, .rdata file+0x0013A008] | Additional top-level directory |
| `Kernel/` | 9 | [observed: `ControlFunction.c`, .rdata file+0x0013A0E0] | Listed |
| `Lib/` | 7 | [observed: `UBTree.c`, .rdata file+0x0013A4A0] | Listed |
| `LL/` | 12 | [observed: `LLFont.c`, .rdata file+0x0013A9F4] | Listed |
| `Lo-Rendering/` | 6 | [observed: `Shader/ShaderObject/ShaderObjectCommon/Win/ShaderObjectCommon_TexAnimManager_Win.c`, .rdata file+0x0013BB80] | Listed |
| `Memory_Card/` | 2 | [observed: `MC_Common.c`, .rdata file+0x0013C47C] | Mentioned under LL. The path places it beside LL |
| `Physics/` | 2 | [observed: `App_Interface.c`, .rdata file+0x0013CC48] | Listed |
| `RCMP/` | 1 | [observed: `rcmp_mad_codec.c`, .rdata file+0x0013DC88] | Listed |
| `SFX/` | 4 | [observed: `Effect_LineTrail.c`, .rdata file+0x0013DD8C] | Listed |
| `SPECIF/` | 2 | [observed: `UFont.c`, .rdata file+0x0013E5F0] | Additional top-level directory |
| `Stream/` | 1 | [observed: `memorySlot.c`, .rdata file+0x0013E794] | Additional top-level directory |
| `UI/` | 1 | [observed: `Hud.c`, .rdata file+0x0013EC2C] | Listed |

## Windows porting seam

[inferred: these `LL*_Win.c` paths identify candidate Windows backends
for WP-2.7, including the memory-card implementation].

- [observed: `LL/Win/LLDisSt_Win.c`, .rdata file+0x0013AB60]
- [observed: `LL/Win/LLGraph_Win.c`, .rdata file+0x0013ACAC]
- [observed: `LL/Win/LLInput_Win.c`, .rdata file+0x0013B13C]
- [observed: `LL/Win/LLObj_Win.c`, .rdata file+0x0013B580]
- [observed: `LL/Win/LLPict_Win.c`, .rdata file+0x0013B5B4]
- [observed: `LL/Win/LLTex_Win.c`, .rdata file+0x0013B60C]
- [observed: `LL/Win/LLVideoDivX_Win.c`, .rdata file+0x0013B644]
- [observed: `Memory_Card/Win/LLMC_Win.c`, .rdata file+0x0013CB7C]

[unknown: per-section encryption coverage and the location of any
source paths still hidden by packing].

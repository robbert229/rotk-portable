# Rich headers and original Windows toolchain

[observed: installed game tree, with ROTK.exe SHA-256
`95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2`.
Reproduce with `make richhdr` or run `python3 -I tools/richhdr.py --json`
with quoted PE paths. All offsets below are file offsets.]

## Per-binary results

[observed: the installed tree contains the 15 PEs below. Tuple notation is
`prodid/build/count`, in on-disk order. The stored key matches the computed
checksum in each valid row. DanS is at file+0x80 in all 15 images.]

| Binary | Rich offset | PE offset | Key | Checksum | Records |
| --- | ---: | ---: | ---: | --- | --- |
| `DivxDecoder.dll` | `0xd0` | `0xf0` | `0x3ee32fbc` | valid | 11/8047/1, 14/7299/21, 10/8047/98, 0/0/15, 1/0/73, 19/8034/3, 48/9044/48, 4/8447/1 |
| `DivxMediaLib.dll` | `0xd0` | `0xe8` | `0x1c4a518a` | valid | 11/8047/1, 14/7299/21, 10/8047/101, 19/8034/3, 1/0/96, 48/9044/2, 49/9044/1, 4/8447/5 |
| `DrvMgt.dll` | `0xc8` | `0xd8` | `0x3cbf6c4b` | valid | 11/8047/1, 14/7299/20, 10/8047/61, 19/8034/7, 1/0/99, 10/8966/6, 4/8447/1 |
| `FileParser.dll` | `0xd8` | `0xe8` | `0x456122b6` | valid | 12/7291/1, 11/8047/1, 14/7299/21, 10/8047/106, 19/8034/3, 1/0/83, 48/9044/4, 49/9044/1, 4/8447/1 |
| `ROTK.exe` | `0x100` | `0x118` | `0x2f195187` | valid | 25/9210/9, 11/8799/1, 39/9162/3, 28/9178/4, 1/0/156, 18/8444/1, 29/9178/12, 0/0/8, 29/9466/10, 64/9466/43, 28/9466/563, 63/9466/1, 69/9466/1, 61/9466/1 |
| `SECDRV.SYS` | `0xa0` | `0xb0` | `0x000c0d88` | invalid (computed `0x885b4129`) | 6/1668/1, 0/0/31 |
| `Support/EReg.exe` | `0xe8` | `0x100` | `0x7f3138a6` | valid | 11/8798/3, 14/7299/23, 11/8047/8, 10/8047/95, 10/8966/8, 0/0/35, 19/8022/15, 19/8034/15, 1/0/190, 11/8966/3, 6/1735/1 |
| `Support/EasyInfo.exe` | `0xd8` | `0xf8` | `0x181d3983` | valid | 39/9162/2, 64/9466/28, 25/9111/4, 28/9466/142, 93/2179/19, 1/0/125, 29/9466/53, 69/9466/1, 61/9466/1 |
| `Support/LOTR The Return of the King tm_EZ.exe` | `0xf0` | `0x100` | `0xe40f0489` | valid | 39/9162/1, 37/8755/2, 28/9178/7, 64/9466/29, 28/9466/153, 39/8491/9, 25/9210/29, 1/0/590, 29/9177/1, 29/9466/142, 69/9466/1, 61/9466/1 |
| `Support/LOTR The Return of the King tm_code.exe` | `0xd8` | `0xe8` | `0xc019d16c` | valid | 37/8755/2, 28/9178/7, 25/9210/21, 1/0/530, 64/9466/28, 28/9466/134, 29/9466/100, 69/9466/1, 61/9466/1 |
| `Support/LOTR The Return of the King tm_uninst.exe` | `0xc8` | `0xd8` | `0x9a32337b` | valid | 11/8047/1, 14/7299/14, 10/8047/46, 1/0/48, 19/8034/5, 48/9044/1, 6/1735/1 |
| `Support/go_ez.exe` | `0xc8` | `0xe0` | `0x288f76ba` | valid | 11/8047/1, 10/8047/26, 14/7299/12, 37/8755/3, 1/0/40, 11/8966/2, 6/1735/1 |
| `eauninstall.exe` | `0xe0` | `0xf0` | `0x1641cd22` | valid | 39/9162/3, 37/8755/2, 28/9178/8, 64/9466/29, 28/9466/186, 25/9210/23, 1/0/569, 29/9466/113, 69/9466/1, 61/9466/1 |
| `eax.dll` | `0xd8` | `0xe8` | `0x87782c55` | valid | 11/8047/8, 14/7299/28, 10/8047/84, 95/2190/1, 93/2179/9, 1/0/85, 49/9044/12, 6/1735/1, 4/8447/1 |
| `rotk_uninst.exe` | `0xd8` | `0xf0` | `0xa99a74a6` | valid | 37/8755/2, 28/9178/7, 25/9210/21, 1/0/531, 64/9466/27, 28/9466/140, 29/9466/95, 69/9466/1, 61/9466/1 |

[observed: product names and VS release families for these IDs are catalogued
in the [prodid enum](https://gist.github.com/skochinsky/07c8e95e33d9429d81a75622b5d24c8b)
and [richprint comp.id list](https://github.com/dishather/richprint/blob/master/comp_id.txt).
The decoder retains the exact build even where the release label is only a family.]

| Prodid | Product | Release family |
| ---: | --- | --- |
| 0 | `Unknown` | Unmarked (old) |
| 1 | `Import0` | Unmarked |
| 4 | `Linker600` | Visual C++ 6.0 |
| 6 | `Cvtres500` | CVTRES 5.00 |
| 10 | `Utc12_C` | Visual C++ 6.0 |
| 11 | `Utc12_CPP` | Visual C++ 6.0 |
| 12 | `AliasObj60` | Visual C++ 6.0 |
| 14 | `Masm613` | MASM 6.13 |
| 18 | `Masm614` | MASM 6.14 |
| 19 | `Linker512` | Linker 5.12 |
| 25 | `Implib700` | Visual Studio .NET 2002-era |
| 28 | `Utc13_C` | Visual Studio .NET 2002-era |
| 29 | `Utc13_CPP` | Visual Studio .NET 2002-era |
| 37 | `Linker620` | Linker 6.20 |
| 39 | `AliasObj70` | Visual Studio .NET 2002-era |
| 48 | `Utc12_2_C` | Visual C++ 6.0 Processor Pack |
| 49 | `Utc12_2_CPP` | Visual C++ 6.0 Processor Pack |
| 61 | `Linker700` | Visual Studio .NET 2002-era |
| 63 | `Export700` | Visual Studio .NET 2002-era |
| 64 | `Masm700` | Visual Studio .NET 2002-era |
| 69 | `Cvtres700` | Visual Studio .NET 2002-era |
| 93 | `Implib710` | Visual Studio .NET 2003 family |
| 95 | `Utc1310_C` | Visual Studio .NET 2003 family |

[observed: ROTK.exe's DOS header and stub at file+0x00–0x7f (with file+0x3c–0x3f
zeroed for the calculation) and decoded records at file+0x90–0xff produce
`0x2f195187`. The packed image retains a self-consistent Rich header at file+0x80–0x107.]
[unknown: whether SafeDisc rewrote any covered bytes and regenerated the key.
The checksum establishes consistency of the shipped bytes.]

[observed: SECDRV.SYS stores `0x000c0d88` at file+0xa4. Including the DOS
bytes at file+0x00–0x7f gives `0x885b4129`. Adding just the DanS offset
(file+0x80) and the rotated comp.ids from file+0x90–0x9f gives the stored
`0x000c0d88`.]
[inferred: the resource-converter and unmarked-only records and the matching
record-only result point to a legacy checksum convention.]
[unknown: which linker generated this header and whether its DOS region changed.]

## ROTK.exe object provenance

- [observed: ROTK.exe file+0x90–0xff records Linker700 build 9466, the same
  build seen in the two EA uninstallers. The matching release family is VS .NET
  2002 RTM. Utc13_C and Utc13_CPP build 9466 are cl 13.00.9466.]
- [inferred: game C code dominates the candidate pool in Utc13_C 9466, given
  the matching toolchain and the source paths under the game tree. The same
  comp.id also marks C objects in the static CRT. The C++, MASM, and AliasObj
  batches likewise share comp.ids with the reference archive. The executable's
  CRT runtime strings and startup landmarks are recorded in the
  [README](../../README.md).] [unknown: the per-member division between game,
  CRT, and other libraries.]
- [observed: richprint identifies 13.00.9178 as the Windows XP SP1 DDK compiler
  build. ROTK.exe has 4 C and 12 C++ records from that build, and the two EA
  uninstallers also have 9178 C objects.]
  [inferred: the repeated older build across different applications is
  consistent with prebuilt library inputs.]
  [unknown: which libraries contributed these objects. DirectX use alone
  cannot identify the batch as DirectX SDK or middleware.]
- [observed: the VC6-era Utc12_CPP 8799 and MASM 6.14 build 8444 each contribute
  one record. Implib700 9210, AliasObj70 9162, Export700 9466 and Cvtres700
  9466 describe import, alias, export and resource tool contributions. The
  zero-build IDs 0 and 1 are richprint's unmarked buckets.]
  [unknown: the originating library for each VC6-era object and the language
  or provenance of the unmarked objects.]

## Game C unit estimate

[observed: the pinned [reference libcmt.lib](https://github.com/archaic-msvc/msvc700/blob/97fe4cdeaeb0bb934591d4b05eb52c2e8ab3e34b/Vc7/lib/libcmt.lib)
has SHA-256 `8815af7b9b6e0e28b77708ede25ab7ecfc4b05e1d8811f092c516cff5ce19d94`.
A COFF archive walk counted 716 object members by absolute `@comp.id` symbol.
Skip the linker indexes and long-name table (members named `/` and `//`), read
each COFF symbol table using its offset/count at object+0x08/+0x0c, and count
the value of `@comp.id` (section −1), skipping auxiliary symbols. Advance each
archive member by its 60-byte header and even-rounded payload size.]

| Prodid | Build | Product | Reference members |
| ---: | ---: | --- | ---: |
| 28 | 9466 | Utc13_C | 543 |
| 29 | 9466 | Utc13_CPP | 45 |
| 39 | 9162 | AliasObj70 | 44 |
| 64 | 9466 | Masm700 | 84 |

[unknown: which archive members were selected at link time. A local scan for
unique exact 32-byte-or-longer relocation-free runs from the 9466 C members'
`.text` sections produced zero matches in packed ROTK.exe. This does not
measure what will match after unpacking.]

[inferred: **71–562 game C units in the 9466 batch** is a conservative working
range. Assume at least one C object from the static CRT and at most the 543
reference candidates. Subtracting that interval from 563 leaves 20–562
objects before accounting for other libraries. The
[WP-0.5 inventory](../modules/README.md) observes 71 distinct game-tree
`.c` paths in the packed executable. Using those as a lower bound assumes
they represent distinct linked translation units from the main build. In
this model the path evidence permits at most 492 combined CRT and other
non-game objects. The upper bound assumes every remaining 9466 C object
could be game code. If the four 9178 C objects also belong to the game,
the upper bound for the two marked C batches becomes 566.]

[unknown: the number of game units with no readable path, any repeated or
included source paths, and whether either unmarked bucket contains game C.
The range is a planning estimate conditional on the assumptions above.
Revisit it after WP-2.2 library identification and WP-2.3 source-path xrefs.]

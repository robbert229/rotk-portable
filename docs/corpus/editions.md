# Return of the King editions and engine references

The [edition catalogue](../../re/corpus/editions.csv) records retail pressings,
reissues, demos, and related-engine leads for R-1. Redump IDs refer to disc
records, with PC sets listed in disc order. Executable hashes are explicitly
labelled. A row's evidence tag describes the edition or claim in the source.
An expected boot filename, inferred protection status, or unknown field may
appear within an observed edition row. Release dates refer to retail availability
where documented. EA announced US shipping on November 4 and store availability
on November 6, 2003. [observed: [EA press release](https://www.nintendoworldreport.com/pr/9104/ea-ships-the-return-of-the-king).]

## Local Windows baseline

[observed: local retail install, identified in the [file manifest](../../re/corpus/manifest.csv).]
The playbook's default install path was used because `ROTK_GAME_DIR` was unset.

| File | Evidence |
| --- | --- |
| `Support/readme.txt` | [observed: lines 4–5 give `Version 1.0` and `November 5, 2003`.] |
| `ROTK.exe` | [observed: PE COFF timestamp `0x3f807074` = 2003-10-05 19:26:44 UTC, linker 7.00, 2,874,240 bytes. The exposed resource tree has no RT_VERSION entry. SHA-256 `95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2`.] |
| `ROTK.exe` CodeView | [observed: the debug directory timestamp is one second earlier, `0x3f807073`. RSDS names `ROTK_EN_Fin_Win_DotNet.pdb`, GUID `eced3210-3532-49d3-a2bb-a850a135a08a`, age 47 decimal. The EN label identifies the executable's build configuration.][unknown: exact retail disc pressing for this install.] |
| `eauninstall.exe` | [observed: FileVersion and ProductVersion 1.2.0.189, also in the fixed version structure at file+0x35A20.] |
| `eax.dll` | [observed: FileVersion and ProductVersion strings 3.066; fixed versions 3.0.6.6, structure at file+0x1F088.] |
| `SECDRV.SYS` | [observed: FileVersion 3.19.000; ProductVersion begins 3.19.000 and includes 2003/03/19. Fixed file and product versions both decode to 3.19.0.0 (major/minor DWORD `0x00030013` at file+0x2630 and +0x2638). The driver version is a separate identifier from the game's protection version.] |
| `DrvMgt.dll` | [observed: the PE resource directory is absent.][unknown: file version, per the [WP-1.1 scan](../research/safe-disc.md#companion-files-and-search-coverage).] |

[unknown: a patch or rebuild between the executable and readme dates. The dates
identify two separate files.] [inferred: the local game uses SafeDisc 3.10.020,
from the [local fingerprint](../research/safe-disc.md#wp-11--static-fingerprint-of-the-retail-executable)
and matching protection revision in the [US retail disc metadata](http://redump.org/disc/64899/).]

## Windows pressings, labels, and patches

- [observed: two US English three-CD pressings use serials 1468707, 1468717 and
  1468727. The second is also catalogued under The EA Games Collection. Both
  play discs list SafeDisc 3.10.020 and the two sets have different disc hashes.]
  [unknown: whether the game executables differ.] [US original](http://redump.org/disc/64897/),
  [US original play disc](http://redump.org/disc/64899/),
  [collection pressing](http://redump.org/disc/40822/),
  [collection play disc](http://redump.org/disc/40820/).
- [observed: the multilingual European EA Classics discs list Dutch, English,
  Polish, Portuguese and Swedish. German Original/Classics and Italian
  Original/Classics have separate disc identifiers. Germany also has an EA
  Most Wanted pressing. French and Polish EA Games Classics packaging is
  documented.] [European Classics](http://redump.org/disc/133153/),
  [German Original/Classics](http://redump.org/disc/104498/),
  [Italian Classics](http://redump.org/disc/63151/),
  [German Most Wanted](http://redump.org/disc/88456/),
  [box scans](https://www.mobygames.com/game/10862/the-lord-of-the-rings-the-return-of-the-king/covers/).
- [observed: Redump identifies SafeDisc 2.90.040 on the Japanese Original/EA Best
  Selections disc 1 (also the play disc) and the mainland Chinese disc 1.
  PCGamingWiki reports Korean and Traditional Chinese retail in Korea and
  Taiwan respectively.] [unknown: exact executable fingerprints for these
  releases.] [Japan](http://redump.org/disc/35674/),
  [China](http://redump.org/disc/76184/),
  [PCGamingWiki localization table](https://www.pcgamingwiki.com/wiki/The_Lord_of_the_Rings%3A_The_Return_of_the_King#Localizations).
- [observed: Redump's publisher index has a US DVD re-release under 1490507
  and marks it missing from the disc database. PCGamingWiki describes DVD
  bonus content. A Dell Collector's Edition box has been photographed.]
  [unknown: DVD and Dell EXE identity and protection.] [EA publisher index](https://wiki.redump.info/Electronic_Arts_USA_-_Publisher_List),
  [PCGamingWiki](https://www.pcgamingwiki.com/wiki/The_Lord_of_the_Rings%3A_The_Return_of_the_King),
  [Dell box photos](https://www.ebay.com/itm/267074208539).
- [observed: the Kellogg's playable demo CD is catalogued as 1.2.0.0 and a
  September 2003 report describes a public PC demo with one playable mission.]
  [unknown: whether they contain the same executable, and whether either
  executable is SafeDisc-free.] [Kellogg's disc](http://redump.org/disc/58470/),
  [public demo coverage](https://www.golem.de/0309/27560.html).
- [unknown: official PC retail **v1.01**, any changes it made, and an official
  EA patch URL. Searches for EA release notes, patch and version references
  and the PCGamingWiki release history yielded no verified EA candidate.]
  [observed: Redump's 1.01 entries are Chinese-market and Korean PS2 discs.]
  [PCGamingWiki](https://www.pcgamingwiki.com/wiki/The_Lord_of_the_Rings%3A_The_Return_of_the_King),
  [Asia PS2](http://redump.org/disc/34359/), [Korea PS2](http://redump.org/disc/101146/).

## Console and Mac comparisons

| Platform | Disc families and analysis value |
| --- | --- |
| Xbox | [observed: xemu lists EA-062 as XBE title ID 4541003E. EA-062 spans USA media ID EA06201A and European masterings EA06202E through EA06206E. See the CSV for region and language per mastering.] [inferred: `default.xbe` is the closest console reference for Win32 code because both are 32-bit x86 and the Xbox build likely used the Microsoft XDK's MSVC-family toolchain. The XDK library stamps and compiler idioms can test that hypothesis.] [unknown: exact compiler revision and production map/symbol availability.] [US metadata](http://redump.org/disc/38327/), [EU metadata](http://redump.org/disc/14698/), [xemu title record](https://xemu.app/titles/4541003e/), [XBE analysis](https://github.com/sp00nznet/xboxrecomp/blob/main/docs/pipeline/01-xbe-parsing.md). |
| PlayStation 2 | [observed: the CSV covers SLUS-20770, SLES-52017 through 52021, SLAJ-25019, SLKA-25098, SLPM-65503 and the EA Best Hits SLPM-65727 reissue. The latter's executable identity is unknown.] [inferred: the MIPS ELF can cross-reference strings, data layouts and gameplay behavior. Read `SYSTEM.CNF` to confirm the boot filename.] [US disc](http://redump.org/disc/5796/), [PAL disc and Platinum](http://redump.org/disc/4843/), [release listing](https://gamefaqs.gamespot.com/mac/675411-lord-of-the-rings-return-of-the-king/data). |
| GameCube | [observed: the CSV covers GKLE (USA), GKLP (European multilingual), GKLD (German), GKLF (French), GKLS (Spanish), GKLI (Italian) and GKLJ (Japanese). Redump groups US and European Original/Player's Choice pressings under their respective disc IDs. The community port's US GKLE69 rev 0 reference has `main.dol` SHA-1 `86ff4c72e0f90be7bcd72d5ec9bef2f2fb20c473`.] [inferred: PowerPC function matching should start with strings, constants and structures.] [US disc](http://redump.org/disc/6853/), [Europe disc](http://redump.org/disc/6737/), [Japan disc](http://redump.org/disc/26435/), [DOL hash check](https://github.com/kenny08gt/rotk-native/blob/main/bootstrap.sh). |
| Mac OS X | [observed: Aspyr's native PowerPC DVD, developed by Beenox, is a port of the Windows game. Aspyr announced April 2, 2004 store availability.] [inferred: direct PC lineage makes it a useful second source for engine logic and data formats.] [unknown: binary name/revision, Mac disc checks, and symbols.] [Aspyr shipping report](https://www.macworld.com/article/170243/return-3.html), [store date](https://www.macworld.com/article/170129/return-2.html), [PowerPC compatibility](https://www.pcgamingwiki.com/wiki/The_Lord_of_the_Rings%3A_The_Return_of_the_King). |
| GBA | [observed: EA shipped a separate handheld action RPG by Griptonite.] [inferred: different engine, based on the distinct implementation and developer.] [EA release announcement](https://www.nintendoworldreport.com/pr/9104/ea-ships-the-return-of-the-king), [MobyGames handheld listing](https://www.mobygames.com/game/11115/the-lord-of-the-rings-the-return-of-the-king/credits/gameboy-advance/). |

[inferred: the Xbox XBE, PS2 ELF, GameCube DOL and PowerPC Mac application
are free of the Windows SafeDisc wrapper because they use native platform
formats. Platform signing and media checks are separate.] [unknown: any
verified SafeDisc-free official Windows retail build.] [XBE format](https://github.com/sp00nznet/xboxrecomp/blob/main/docs/pipeline/01-xbe-parsing.md),
[GameCube port analysis](https://github.com/kenny08gt/rotk-native),
[Mac port announcement](https://www.macworld.com/article/170243/return-3.html).

## Debug evidence

- [observed: the local Windows executable has the RSDS path above, embedded
  EAThirdPerson source paths including `Kernel\EntityManager.c` at
  file+0x13A1B4, and assertion text. The installed tree search found zero
  `.pdb`, `.map` or `.dbg` sidecars.] [unknown: a matching PDB or original
  map in any edition.] [Source-path inventory](../../re/strings/source_paths.txt).
- [observed: the GameCube community project publishes `decomp/rotk.map` and
  TSV function names for its US DOL reference, described as reverse-engineering
  results.] [unknown: any original Nintendo/EA linker map on the media.]
  [Community project documentation](https://github.com/kenny08gt/rotk-native#how-it-works).
- [observed: the Xbox game has a community recompilation project.]
  [unknown: original Xbox or PS2 symbol/map sidecars, and any verified
  publicly documented original console assertions.] [Xbox reference](https://github.com/Shagg88/Athelas).

## Related engine candidates

- **The Two Towers (Xbox, PS2, GameCube).** [observed: EA worked directly
  with Stormfront on the predecessor.] [unknown: how much runtime code or
  tooling carries forward into ROTK's EAThirdPerson tree.] Compare paths,
  assert text, container signatures and matching routines. US starter
  references are Xbox EA-016, PS2 SLUS-20578 and GameCube DL-DOL-GLOE-USA.
  [EA executive account](https://stvp.stanford.edu/wp-content/uploads/sites/3/2024/09/opportunity-assessment-two-towers-transcript.pdf),
  [Xbox](http://redump.org/disc/12147/), [PS2](http://redump.org/disc/1298/),
  [GameCube](http://redump.org/disc/2351/).
- **Tiger Woods PGA Tour.** [observed: Glen Schofield publicly described
  adapting a Tiger Woods engine for ROTK. Developer Nick Ferguson recalled
  LOTR VFX code in a Tiger Woods PSP game.] [inferred: the golf lineage is a
  candidate for shared streaming/scene code, and PSP for VFX naming.]
  [unknown: donor SKU, PSP SKU, and the modules retained across builds.]
  [Schofield interview](https://www.youtube.com/watch?v=TEXdJU9ZUX8),
  [Ferguson account quoted by Time Extension](https://www.timeextension.com/news/2022/12/random-this-lord-of-the-rings-game-apparently-shared-an-engine-with-tiger-woods).
- **The Third Age (Xbox, PS2, GameCube).** [observed: EA Redwood Shores
  describes using the same film-side asset blueprint as its earlier LOTR
  games.] [unknown: EAThirdPerson runtime reuse.] The shared asset pipeline
  makes the disc layouts worth comparing. [Developer interview](https://www.n-europe.com/news/interview-lord-of-the-rings-the-third-age/),
  [US Xbox retail](http://redump.org/disc/33667/).

## What the owner should check in their collection

- [ ] Look first for **Xbox EA-062**, especially **EA06201A**. Record the
  ring code, disc ID, and `default.xbe` SHA-256, XBE build timestamp, title
  ID and library version stamps from the owned copy.
- [ ] Look for the Windows **1490507 DVD**, **The EA Games Collection**,
  **Dell Collector's Edition**, **EA Classics / Most Wanted / Best
  Selections**, localized discs and **CPGLOTR1A** demo. Record disc serials,
  readme version and date, executable names, hashes and file versions, and
  protection evidence. Check for an EA-authored updater or patch readme on
  owned media.
- [ ] Check the **Aspyr Mac DVD**, **PS2** and **GameCube** discs. Record
  region, serial, program filename, hash and revision. For PS2 record the
  `SYSTEM.CNF` boot path and version.
- [ ] Check the same media for `.pdb`, `.map`, `.sym`, `.dbg` and
  separate debug executables. Record minimal metadata and embedded identifiers
  if present. Inventory owned copies of **The Two Towers**, **The Third Age**
  and period **Tiger Woods PGA Tour** for the engine comparison.

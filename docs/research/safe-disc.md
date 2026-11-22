# SafeDisc — pre-existing solutions research (ROTK 2003 PC)

Research note for the rotk-portable decompilation effort. Target: `ROTK.exe`
(PE32 x86, SHA-256 `95af128c…b2a5a2`, MSVC 7.0, SafeDisc-protected: `stxt371`/`stxt774`/`tdb`
sections, entry stub in `stxt371`, encrypted IAT, Ghidra sees only ~58 functions).

Goal of this note: find **pre-existing** tools/work that can get us an *unpacked*
image (OEP + rebuilt IAT) that Ghidra can decompile. Research only — no cracks were
downloaded or executed.

Date of research: 2026-11-09. All links verified accessible on that date unless noted.

---

## TL;DR — recommended path

**No publicly available tool automatically unpacks SafeDisc 3.x executables.** The
proven community workflow is *run then dump*:

1. **Run the legitimately-owned protected `ROTK.exe` on a real/virtual Windows**
   (XP/7 VM is simplest; disc or a mount of *your own* disc image). To get past
   secdrv on modern Windows, use [SafeDiscShim](https://github.com/RibShark/SafeDiscShim)
   (user-mode secdrv emulation, original disc still required) or
   [SafeDiscLoader2](https://github.com/nckstwrt/SafeDiscLoader2)
   (`version.dll` hijack, SafeDisc 2.0–4.9, no disc needed, works on modern Windows).
2. **Dump the process at OEP** with x32dbg + **Scylla** (or scan the running process
   with [PE-sieve](https://github.com/hasherezade/pe-sieve)), then **rebuild the IAT
   with Scylla**. This is the standard packed-PE workflow; SafeDisc is not special-cased
   by any automated unpacker ([UnpacMe](https://support.unpac.me/unpacme-service),
   unlicense, cat_unpackers, MalUnpack, ReversingLabs: no SafeDisc support found).
3. **Sanity-check the dump size ≈ 2,874,232 bytes** — that is the size of the 2003
   DEViANCE "Proper Fixed EXE" (a no-CD exe = historically a dumped+repaired original),
   and the size the Nemesis widescreen fix officially supports
   ([PCGamingWiki](https://www.pcgamingwiki.com/wiki/The_Lord_of_the_Rings:_The_Return_of_the_King)).
   A dump of that size with sane MSVC 7.0 imports is very likely the true unpacked image.
4. **Wine alone is not a path**: there is no kernel for `secdrv.sys` in Wine and the
   driver does not load there ([WineHQ forum](https://forum.winehq.org/viewtopic.php?t=30311)).
   Use a Windows VM for the dump; the resulting unpacked PE can then be fed to Ghidra
   on Linux.

**Version correction (important):** the project premise "SafeDisc 2.x" is likely wrong.
Two independent sources classify ROTK (2003) as **SafeDisc 3**: GameCopyWorld lists
"Protection: SafeDisc v3" ([GCW page](https://gamecopyworld.com/games/pc_lord_of_the_rings_rotk.shtml))
and PCGamingWiki lists "SafeDisc 3 DRM"
([game page](https://www.pcgamingwiki.com/wiki/The_Lord_of_the_Rings:_The_Return_of_the_King)).
This matches our binary observations: SafeDisc 3 integrates the loader stub *into* the
exe and encrypts it (no `.ICD` sidecar), unlike v1/v2
([Wikipedia: SafeDisc](https://en.wikipedia.org/wiki/SafeDisc)). Consequence: the
legacy static "unwrap" tools (SafeDiscCleaner/Safedisc2Cleaner ≤ v2.6/2.7, UnSafeDisc's
ICD decryptor) almost certainly **do not apply** to ROTK. Verify directly: search the
on-disk `ROTK.exe` for the SafeDisc version string (Wikipedia documents an `SD2` marker
followed by version/subversion/revision dwords) and record the exact version.

---

## 1. ROTK-specific pre-existing work

### GameCopyWorld — DEViANCE "Proper Fixed EXE" (no-CD)
- **What:** `LotR: The Return Of The King v1.0 [EN] Proper Fixed EXE`, released
  07-11-2003 by DEViANCE (648 KB archive), plus PlayFix no-CD and several trainers.
  Instructions: replace original `ROTK.EXE` after full install.
- **Protection handled:** listed as **SafeDisc v3** for this game (OBSERVED on the page).
- **Usable unpacked binary?** A "fixed EXE" is by scene convention a memory dump of the
  protected exe at OEP with the protection stubs removed and IAT repaired (INFERENCE —
  not stated on the page). It is patched to skip CD checks, so it is a *modified* exe,
  not a pristine unpacked image — but it is the closest thing to a pre-existing unpacked
  ROTK.exe and an excellent size/bytes cross-reference for our own dump.
- **Status:** historical (2003); page live as of 2026-11-09.
- **URL:** <https://gamecopyworld.com/games/pc_lord_of_the_rings_rotk.shtml>
- **Legal note:** downloading it = obtaining a crack. We did **not** download it. With a
  legitimately owned copy, dumping your own exe achieves the equivalent without it.

### My Abandonware — ROTK download page
- **What:** distributable abandonware listing; community comments confirm the retail
  `ROTK.exe` is SafeDisc-protected, does not run on Win10, and must be replaced by the
  NoCD exe; also documents XP compatibility mode for `Setup.exe`, widescreen fix usage.
- **Relevance:** confirms protection type and that the community's only known working
  modern path is the no-CD exe (i.e., an unpacked exe already existed in 2003).
- **URL:** <https://www.myabandonware.com/game/the-lord-of-the-rings-the-return-of-the-king-cbz>

### PCGamingWiki game page
- **What:** DRM table ("SafeDisc 3 DRM", disc check + CD key), warning that SafeDisc
  doesn't work on Vista+ with KB3086255 / Win10/11; links to the SafeDisc hub page,
  Wine AppDB entry (appdb id 3257), archive.org demo, and community fixes.
- **Key RE-relevant fact:** Nemesis 2000 widescreen fix supports "exe size:
  **2 874 232 bytes**" — the no-CD exe size (OBSERVED). Useful dump oracle.
- **Essential improvements:** "Fix Enhancers Fix" by Chip-Biscuit
  ([GitHub](https://github.com/Chip-Biscuit/Lord-of-the-Rings-the-Return-of-the-King-PC-Fix),
  [PCGW file 4006](https://community.pcgamingwiki.com/files/file/4006-the-lord-of-the-rings-the-return-of-the-king-pc-fix/))
  — FOV/FPS/borderless fixes; its video guide states it requires a no-CD exe because
  SafeDisc "removes the DRM from the .exe" being a prerequisite. Evidence that modern
  community DLL-injection fixes already target the *unprotected* exe shape.
- **URL:** <https://www.pcgamingwiki.com/wiki/The_Lord_of_the_Rings:_The_Return_of_the_King>

### Prior modding/RE efforts
- ModDB game page exists (<https://www.moddb.com/games/lord-of-the-rings-the-return-of-the-king>);
  known mods: Xbox controller mod (linked from PCGW), HD texture remaster (Dolphin/PS2
  oriented). No prior *decompilation* or SafeDisc-removal project found (OBSERVED: none
  in search results). The Chip-Biscuit fix (patching hardcoded values in the unprotected
  exe via wrapper) is the most RE-adjacent community artifact found.
- **Gap:** no GitHub/ModDB/NexusMods project publishing an unpacked ROTK.exe was found.

---

## 2. SafeDisc removal / stripping tools

### SafeDiscCleaner / "Safedisc 2 Cleaner" (bOOls eYe, r!sc et al., ~2000s)
- **What:** static "unwrapper" for SafeDisc/SafeCast-protected executables.
- **Versions handled:** **below v2.7** (OBSERVED — stated in SafeDiscLoader2's README:
  "Safedisc2Cleaner which can unwrap Safedisc executables below version 2.7"; Softpedia
  lists it as "unwrap files protected with SafeDisc or SafeCast 2").
- **Applicability to ROTK:** almost certainly **none**, since ROTK is reported SafeDisc 3
  (INFERENCE from version coverage). Also pre-dates the v3 exe-integrated encryption.
- **URLs:** mentioned in <https://github.com/nckstwrt/SafeDiscLoader2> ;
  <https://www.softpedia.com/get/Security/Security-Related/Safedisc-2-Cleaner.shtml>
  (Softpedia listing dated 2014; original download status unverified).

### UnSafeDisc / ICD decryption
- **What:** decrypts the `game.ICD` encrypted-executable archive into an EXE.
- **Versions handled:** SafeDisc v1-era layout (separate EXE loader + ICD) and early
  variants; "each program requires a specific patch" (OBSERVED, Wikipedia).
- **Applicability to ROTK:** **no** — in v2+ the loader was integrated into the exe and
  the `.ICD` file became obsolete; v3 encrypts the exe in place with a per-title key and
  a signature on the disc (OBSERVED, Wikipedia). ROTK ships no `.ICD` per its section
  layout. Kept here only to close the lead.
- **URL:** <https://en.wikipedia.org/wiki/SafeDisc> (secondary source; original UnSafeDisc
  distribution not located — treat as dead lead).

### Any modern "SafeDisc stripper that rebuilds IATs"?
- **OBSERVED: none found** on GitHub via searches for SafeDisc + unpack/strip/IAT. The
  SafeDisc tooling ecosystem today is about *running* games (shims/loaders), not
  producing unpacked binaries. This confirms the memory-dump route as the only current one.

---

## 3. Running the protected exe (so it can be dumped)

### SafeDiscShim — RibShark
- **What:** user-mode emulation of `secdrv.sys` IOCTLs; injects alongside the game, no
  kernel driver, explicitly a compatibility tool (original disc still required; "no
  security mechanisms are bypassed").
- **Versions handled:** SafeDisc games that use secdrv (v2/v3/v4 era; README doesn't
  enumerate; issue tracker shows v1 fixes too). PCGamingWiki's SafeDisc hub lists it as
  the primary "Restore SafeDisc support" method.
- **Output:** runs the game only — **not** an unpacked binary. But it is exactly the
  "get it running on modern Windows so you can attach a debugger" piece, and unlike
  loaders it leaves the exe's own code path intact (good for dumping the real stub
  behavior).
- **Maintenance:** actively developed — v0.1.0 Feb 2024, v0.1.1 Feb 2024,
  **v0.9.0 pre-release 29 Sep (2025)** with DLL-injection rework; 596 stars.
- **Windows 11 caveat:** may need Smart App Control disabled (OBSERVED, PCGW SafeDisc hub).
- **URLs:** <https://github.com/RibShark/SafeDiscShim> ;
  Windhawk port <https://github.com/RibShark/safediscshim-windhawk> ;
  hub: <https://www.pcgamingwiki.com/wiki/SafeDisc>

### SafeDiscLoader2 — nckstwrt (SafeDisc Discord community author)
- **What:** `version.dll` hijack + hooks that fully bypass SafeDisc's CD check; for SD3+
  just drop `version.dll` next to the game exe. Config for extra CD-check bypasses and
  verbose logging. GPL-3.0.
- **Versions handled:** **SafeDisc 2.0 → 4.9** (OBSERVED, README) — comfortably covers a
  v3.x ROTK. Tested-game list includes contemporaneous EA titles (BFME II 4.60.00,
  BFME 4.00.01, CoD, Sims 2, etc.), strong evidence the same SD3 generation is supported.
- **Output:** plays the game, no CD needed, on modern Windows — **does not** produce an
  unpacked exe. Its debug logging is useful for understanding the stub.
- **Maintenance:** recent (README/repo active; 83 stars, 30 commits, 5 open issues).
- **Legal framing (OBSERVED from README):** "not intended for Piracy but for users to
  exercise their Fair Use rights for the games they actually own".
- **URL:** <https://github.com/nckstwrt/SafeDiscLoader2>
  (its predecessor <https://github.com/nckstwrt/SafeDiscLoader> is obsolete; it credits
  Reloaded's obfuscated Universal SafeDisc Loader, SafeDiscCleaner, SafeDiscShim,
  BitCrackers' version-proxy.)

### Restoring secdrv.sys on Windows 10/11 (manual driver path)
- **What:** reinstall the original `secdrv.sys` (from a Windows 7 install media or the
  game disc) with test-signing/DSE-bypass tricks, or via ericwj's PowerShell module.
- **Maintenance:** PsSecDrv is a documented 2016-era helper; Microsoft removed/blocked the
  driver in Win10 and disabled it on Vista–8.1 via KB3086255 (OBSERVED, Microsoft Q&A,
  TechSpot, PCGW).
- **Verdict:** works but is the worst option security-wise; SafeDiscShim exists precisely
  to avoid it (OBSERVED, SafeDiscShim README).
- **URLs:** <https://github.com/ericwj/PsSecDrv> ;
  <https://learn.microsoft.com/en-us/answers/questions/3168378/safedisc-retail-drm-does-not-work-on-windows-10-an> ;
  <https://www.techspot.com/news/61790-windows-10-incompatible-securom-safedisc-drm.html>

### Virtual-drive emulation (Daemon Tools / Alcohol 120%)
- **What:** mount a rip of your disc; SD3 "supports Virtual Drives as long as the
  original CD/DVD is available" and v3 worked with Daemon Tools/Alcohol in their heyday,
  subject to blacklisting (OBSERVED, Wikipedia SafeDisc article).
- **Practical status:** only useful on an OS where secdrv still loads (≤8.1 unpatched, or
  XP/7 VM — cleanest). Vogons threads confirm v4-era games still need cloaking tricks on
  modern Windows (<http://www.vogons.org/viewtopic.php?t=83125>).
- **Verdict:** use XP/VM + your own image + (Alcohol/DT Lite or safe disc passthrough) as
  the reference "authentic" environment for dumping.

### Wine / Proton status
- **OBSERVED:** the `SecDrv` service fails under Wine (no kernel driver exists):
  <https://forum.winehq.org/viewtopic.php?t=30311>. SafeDiscShim's issue tracker notes a
  Wine-side failure mode hitting the same games
  (<https://github.com/RibShark/SafeDiscShim/issues/1>). PCGamingWiki links ROTK's Wine
  AppDB entry (id 3257) but appdb.winehq.org was bot-gated (Anubis) at research time —
  **could not read the ROTK AppDB rating directly** (honest gap).
- **Inference:** dumping the protected exe *under Wine* is not viable; SafeDisc's disc
  authentication relies on driver/IOCTL paths Wine does not implement. Plan the dump in
  a Windows VM, then do all static analysis (Ghidra) on Linux.
- **URL:** <https://appdb.winehq.org/objectManager.php?sClass=application&iId=3257> (unverified content)

### Related research-grade leads
- dosbox-x issue #211 — detailed reverse-engineered trace of SafeDisc/SecuROM IOCTL +
  disc-authentication sequence (TOC, PVD sector 16, subchannel reads). Excellent
  background for understanding what the ROTK stub asks the disc for at runtime:
  <https://github.com/joncampbell123/dosbox-x/issues/211>
- paavohtl blog — practical SafeDisc v2 installer-bypass writeup for preservation
  (secondary source, honest about limits):
  <https://blog.paavo.me/masa-copy-protection>

---

## 4. Generic unpacking workflow fit

| Tool | What it gives | Status | URL |
|---|---|---|---|
| **Scylla** (NtQuery) | x86/x64 process dumper + IAT autosearch/rebuild; x64dbg's built-in plugin | Last release v0.9.8 (2015-era, diStorm3 Jan 2015) but bundled/patched by x64dbg; maintained fork with fixes: ergrelet/Scylla | <https://github.com/NtQuery/Scylla> / <https://github.com/ergrelet/Scylla> |
| **PE-sieve / Hollows Hunter / MalUnpack** (hasherezade) | scan a running process, dump the in-memory main module & modified regions, reconstruct PEs | Actively maintained (3.9k stars, recent commits) | <https://github.com/hasherezade/pe-sieve> |
| **x64dbg (x32)** | debugger to reach OEP (hardware breakpoint on the `stxt371` stub's jump to OEP / "last one" technique on `VirtualProtect`), then Scylla from Plugins menu | Active | <https://github.com/x64dbg/x64dbg> |
| **UnpacMe** (ReversingLabs/OpenAnalysis) | automated malware-oriented unpacking | **No SafeDisc in supported unpacking list** (OBSERVED, support docs; ReversingLabs' long packer list also omits SafeDisc) | <https://support.unpac.me/unpacme-service> , <https://docs.reversinglabs.com/General/SpectraCore/report-unpacking> |
| **unlicense / cat_unpackers / Unipacker etc.** | automated static unpackers for compression packers (UPX/ASPack/…) | No SafeDisc coverage found (OBSERVED: absent from awesome-executable-packing's entries for SafeDisc) | <https://github.com/packing-box/awesome-executable-packing> |

**Fit assessment (INFERENCE):** SafeDisc v3 is a runtime-decrypting protector with
disc-keyed decryption — structurally it demands the "run on the target machine, break at
OEP, dump + IAT rebuild" pattern. Nothing automates it. With Scylla's x86 dump + IAT
rebuild this is a standard afternoon's work *once the exe is running*.

---

## 5. Legal / ethical framing

- SafeDisc was **discontinued by Macrovision on 31 March 2009**; Microsoft blocked
  `secdrv.sys` in Windows 10 (2015, also KB3086255 for older OS) for security reasons —
  the DRM is both defunct and hostile to modern systems
  ([Wikipedia](https://en.wikipedia.org/wiki/SafeDisc),
  [TechSpot](https://www.techspot.com/news/61790-windows-10-incompatible-securom-safedisc-drm.html)).
- ROTK (2003) is long out of print and not sold digitally; PC Gamer coverage of the
  series' delistings attributes them to the **expired LOTR license**, not active EA
  distribution of this title ([PC Gamer / Facebook post on a delisted LOTR title's
  surprise Steam return](https://www.facebook.com/pcgamermagazine/posts/1416560230338453),
  secondary/weak — mark as INFERENCE that ROTK is unobtainable new). It circulates as
  abandonware (hosted openly on My Abandonware).
- Standard preservation position (echoed by SafeDiscShim's and SafeDiscLoader2's own
  READMEs): removing an abandoned, security-dangerous DRM from **a copy you lawfully own**
  for interoperability/preservation is the intended use case. The clean-room-equivalent
  path for this project: dump from **our own** retail disc rather than shipping or
  consuming someone else's crack; treat any third-party fixed exe only as a checksum
  oracle if we ever choose to hash-compare (we did not download one).

---

## Recommended workflow (combining the pieces, Linux/Wine host)

1. **Verify the version first (free win):** hex-search the on-disk `ROTK.exe` for the
   `SD2` marker + 3 dwords (per Wikipedia) to pin the exact SafeDisc version; also note
   `DrvMgt.dll` presence. Record in the repo.
2. **Environment:** VirtualBox/QEMU Windows XP SP3 or Windows 7 VM (snapshot it). Pass
   through the physical CD drive or mount a `*.iso/*.mdf` made from **our own** disc.
3. **Get it running:**
   - Preferred (authentic): XP/7 VM + original disc + SafeDiscLoader2 `version.dll`
     (SD 2.0–4.9) — no driver surgery, works modern-day too if we later retry on Win10.
   - Alternative: SafeDiscShim v0.9.0 on Win10/11 with the real disc, if Loader2 chokes.
4. **Reach OEP:** x32dbg on `ROTK.exe`; let the `stxt371` stub decrypt; break on return
   to the image (e.g., hardware breakpoint on the stub's final `jmp reg`, or
   `VirtualProtect`/section-execution breakpoint, per the dosbox-x auth trace for what
   the stub does first). Confirm we're in MSVC 7.0 CRT startup (`___tmainCRTStartup`).
5. **Dump + rebuild:** Scylla (x64dbg plugin) → attach → IAT autosearch (enable advanced
   search) → dump → fix dump; cross-check with PE-sieve scanning the live PID.
6. **Validate:** size ≈ 2,874,232 bytes; imports resolve to kernel32/gdi32/dinput8/dsound
   et al.; no `stxt*` section references at OEP; loads in Ghidra with hundreds→thousands
   of functions; ideally the Nemesis/Chip-Biscuit fixes (which expect the unprotected exe)
   behave correctly against it.
7. **Archive:** keep SHA-256 of the original protected exe and the dump side by side in
   the repo notes; dump is derived from our owned copy only.

Fallback if OEP dumping is fought by anti-dump tricks: run fully to main menu, then dump
with PE-sieve (dumps modified regions without needing exact OEP) and reconstruct.

## Unknowns / gaps

- **Exact SafeDisc version of v1.0 retail** — reported v3 by GCW and PCGW, but unverified
  against our binary; do the `SD2` string check. (If it were genuinely 2.x, SafeDiscCleaner
  could statically unwrap it — cheap experiment worth doing only if version < 2.7.)
- **Wine AppDB rating for ROTK** — page exists (id 3257) but is bot-gated (Anubis);
  someone with a browser should read it; also check Lutris (link on PCGW) for runner
  reports.
- **Whether DEViANCE's fixed exe corresponds to retail v1.0 exactly** (GCW lists it as
  v1.0; can't verify without obtaining it, which we deliberately did not do).
- **SafeDisc Discord** (the community behind SafeDiscLoader2/SecuROMLoader) — likely the
  best place to ask about dumping SD3 exes; not directly accessible from research tools.
- **UnSafeDisc availability** — described on Wikipedia but no primary distribution found;
  irrelevant if v3 confirmed (ICD obsolete).
- **Anti-dump countermeasures of this specific SD3 build** — unknown until attempted;
  SD3's docs emphasize encryption + signature, not anti-debug, which is encouraging
  (INFERENCE).
- Softpedia/abandonware download pages were checked only at search-snippet level; original
  circa-2003 tool pages (SafeDiscCleaner homepages) are dead — no verified current
  download location.

## WP-1.1 — Static fingerprint of the retail executable

[observed: ROTK.exe SHA-256
`95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2`,
size `0x2bdb80`. VAs in this addendum refer to this packed image.
The PE32 optional header gives image base `0x400000`, OS and subsystem
versions 4.0, and Windows GUI subsystem (2), superseding the earlier
description of those fields as scrambled.]

[inferred: the retail executable uses **SafeDisc 3.10.020**.
The [BurnOutSharp detector](https://github.com/claunia/BurnOutSharp/blob/master/BurnOutSharp/ProtectionFind.cs#L1303)
defines the two-space `BoG_` marker and falls back from marker+20 to
marker+32 when the first major version is zero. The retail bytes match
that layout.]

[observed: ROTK.exe file+0xFD4 contains `BoG_ *90.0&!!  Yy>`
(two spaces before `Yy>`), in PE header padding before `.text`
at file+0x1000. Little-endian DWORDs at file+0xFE8 (+20 decimal)
are 0, 0, 0. At file+0xFF4 (+32 decimal), 0xFF8 and 0xFFC
they are 3, 10 and 20 respectively.]

[observed: the masked entry-point signature from the
[Detect It Easy SafeDisc rule](https://github.com/horsicq/Detect-It-Easy/blob/master/db/PE/protector_SafeDisc.2.sg)
matches ROTK.exe at packed VA 0x009C305E (file+0x19C05E).
Its structural rule also matches: the last two sections are
`stxt774` and `stxt371`, and `stxt371` holds both the entry point
and import directory. Both checks identify the family and the rule
assigns neither a version.]

### Companion files and search coverage

- [observed: DrvMgt.dll SHA-256
  `310f5c3c861bcafcf430b3479aff626289230ec56192d7aaf90400d2f449991e`.
  The resource directory entry is zero. ASCII labels at file+0x66D6,
  +0x6848 and +0x68CD name `drvmgt.dll`, `DRVMGT` and `SECDRV.SYS`.
  The full-file ASCII and UTF-16LE string scans for dotted version
  triples found none.] [unknown: DrvMgt.dll build.]
- [observed: SECDRV.SYS SHA-256
  `a85c63f5fb99c8efc9ea3be600629ba611c22c2684c380f49cce03572ad7afc1`.
  RT_VERSION (16/1/1033) spans file+0x2600 through +0x2A2D.
  The UTF-16LE FileDescription at +0x282C is `Macrovision SECURITY Driver`.
  FileVersion at +0x2884 is `3.19.000`, and ProductVersion at +0x29E4 begins
  `3.19.000` and includes the date `2003/03/19`. Fixed file and product
  versions at +0x2630 and +0x2638 both decode to 3.11.0.0 when read as
  decimal 16-bit fields (MS DWORD 0x0003000B, LS DWORD 0). The 3.19.000
  string identifies the driver resource. The game fingerprint comes from
  the separate record in ROTK.exe.]
- [observed: searched all bytes of the three files, including headers,
  padding and overlays, for ASCII and UTF-16LE `BoG_`, the single-space
  `BoG_ *90.0&!! Yy>`, `SD2`, `SafeDisc`, `Macrovision`, `C-Dilla`,
  `DrvMgt`, `SECDRV` and `DPLAYERX`, case-insensitively. The full
  two-space ASCII marker occurs once in ROTK.exe and the `BoG_` prefix
  is absent from the companions. ROTK.exe has one case-insensitive
  `SD2` hit, within the high-entropy `.text` at file+0x4B3FF, and no
  uppercase `SD2` or `SafeDisc` hit. Driver-name and vendor hits in the
  companions are consistent with the offsets above.]

### Packed section map

[observed: ROTK.exe has eight 40-byte section headers beginning at
file+0x210. Numeric columns below come from those headers. Entropy is
Shannon bits per byte over each full raw range, including file-alignment
padding and excluding virtual zero-fill. Sizes, offsets and flags are hex.
R/W/X denote the header memory flags.]

| Name | Packed VA | File start | Raw size | Virtual size | Characteristics | Entropy | Role and evidence |
| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| `.text` | 0x00401000 | 0x1000 | 0x134000 | 0x133C58 | `0x60000020` RX code | 7.9987 | [inferred: protected game code, based on executable mapping and near-uniform byte distribution across this raw range.] |
| `.rdata` | 0x00535000 | 0x135000 | 0x25000 | 0x24DEC | `0x40000040` R initialized data | 5.6274 | [observed: readable game source paths, e.g. file+0x1362F4, and the debug directory at file+0x135220.] |
| `.data` | 0x0055A000 | 0x15A000 | 0x1F000 | 0x446FB4 | `0xC0000040` RW initialized data | 7.9734 | [observed: writable data with a large virtual tail.] [inferred: protected initialized game data in the high-entropy raw range.] |
| `.data1` | 0x009A1000 | 0x179000 | 0x1000 | 0x900 | `0xC0000040` RW initialized data | 5.4233 | [observed: its first 0x900 bytes have entropy 7.9125. The PE resource directory RVA starts here, with the named `.rsrc` section one page later.] [unknown: purpose of this early resource-directory page.] |
| `.rsrc` | 0x009A2000 | 0x17A000 | 0x6000 | 0x5AE6 | `0x40000040` R initialized data | 3.5133 | [observed: lies within the resource directory's declared RVA span, which starts at 0x5A2000 in `.data1` and has size 0x5AA0.] |
| Eight ASCII spaces | 0x009A8000 | 0x180000 | 0x18000 | 0x173C8 | `0x42000040` R discardable initialized data | 6.0067 | [observed: file+0x180000 starts a sequence of 345 PE-shaped relocation blocks ending at file+0x1930A0, with 37,441 type-3 and 171 type-0 entries. The PE base-relocation directory is zero.] [inferred: retained relocation table.] [unknown: whether the stub consumes it and the purpose of the remaining bytes.] |
| `stxt774` | 0x009C0000 | 0x199000 | 0x3000 | 0x202C | `0xE0000020` RWX code | 6.2162 | [observed: the first 0x202C bytes have entropy 7.9144.] [inferred: protected loader payload, based on the high-entropy contents and RWX mapping alongside the entry stub.] [unknown: runtime responsibilities and activation path.] |
| `stxt371` | 0x009C3000 | 0x19C000 | 0x4000 | 0x31A8 | `0xE0000020` RWX code | 5.4983 | [observed: hosts the entry stub and bootstrap imports. Static decoding at VA 0x009C308D shows writes that replace the entry instruction with a relative jump. The import directory at file+0x19EF90 lists ten imported functions across six DLLs. The IAT at file+0x19F0A6 occupies 16 slots including six terminators.] |

[observed: `tdb` is absent from the eight section names. Its two literal
ASCII hits at file+0x248911 and +0x296516 lie in the overlay, which starts
at file+0x1A0000.] [unknown: whether either overlay hit has a semantic
meaning.]

### Reproducing the static checks

Use the installation directory from the playbook as `d`. Read the three
files with `Path.read_bytes()` under `python3 -I`. Use `hashlib.sha256`
for identities and `bytes.find` or `re.finditer` for the literal markers.
For the executable, unpack `<III` at offsets `0xFE8` and `0xFF4`.
Read `e_lfanew` as `<I` at file+0x3C, section count as `<H` at
PE+6 and optional header size as `<H` at PE+20. Start the section walk
at PE+24 plus optional header size. For each header, unpack
`<8sIIII12xI` for name, virtual size, RVA, raw size, raw offset and
characteristics. Use `Counter` on the raw slice and sum
`-(count / raw_size) * log2(count / raw_size)` for each byte count.
Use `objdump -p "$d/ROTK.exe"` to inspect the directories and imports,
and `objdump -d -j stxt371 --start-address=0x9c305e --stop-address=0x9c30aa "$d/ROTK.exe"`
to inspect the bootstrap locally. For the version resource, follow PE
directory index 2 through type 16, name 1 and language 1033, or inspect
the bounded payload with `strings -el -t x "$d/SECDRV.SYS"`. The
executable, DLL and driver were inspected as files.

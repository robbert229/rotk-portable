# Misc installed files — provenance & formats

C7/D8 deliverable ([spec](../deliverables.md)). Covers every non-`.scw`/`.GEO`/`.txw`/
`.avi`/PE file in the retail install root and `Support/`, along with selected PE identities. Claims tagged **observed**
(byte/text evidence at the cited location), **inferred**, or **unknown**.

Install root: `…\EA GAMES\LOTR The Return of the King tm\` (read-only corpus).

## `Input.ini` (34,157 B, dated 2003-10-03 in box)

INI file consumed by the game's input system [inferred: bindings below and the
`DirectInput8Create` delay-load import in re/corpus/pe_imports.csv]. The file contains
769 ASCII lines and 25 section headers [observed: re/corpus/assets.csv].
Structure [observed: Input.ini]:

- **`;`-comment lines** and 25 `[section]` headers.
- **`[input_alias_list]`** — maps logical actions to abstract controller tokens:
  player actions (`Player_SpeedAttack`, `Player_Parry`, `Player_FierceAttack`,
  `Player_Kick_PhysicalAttack`, `Player_KillingMove`, `Player_Action`,
  `Player_RangedAttack`, `Player_TurnHoriz/Vert`, `Player_Move`,
  `Player_AutoFlip{UP,LEFT,DOWN,RIGHT}`, `Player_Force{UP,LEFT,DOWN,RIGHT}`,
  `Player_MenuEnable`, `Player_Select`, `Player_JumpBack`, `Player_SpecialAbilityViaKbd`)
  and UI actions (`UIScreen_Start`, `UIScreen_MenuMove{Up,Down}`,
  `UIScreen_Scroll{Left,Right}`, `UIScreen_MenuSelect`, `UIScreen_Back`,
  `UIScreen_Help`, `UIScreen_LevelInfo`, `UIScreen_MoveCursor{H,V}`), plus per-gamepad
  preset aliases (`MSGamePad_*`, `GravisElim_*`, `WingMan_*`, …).
- **`[inputmap_<Device>_BASE]` / `[inputmap_<Device>_UISCREENS]`** — 12 device pairs
  [observed list]: `SidewinderJS`, `MSGamepad`, `GravisEliminator`,
  `LogitechDualAction`, `WingMan`, `WingManRP`, `Firestorm`, `PSPCUSB`, `KikyXSeries`,
  `PsxUSB`, `GenericJoystick`, `ROTKDefault` (the keyboard/mouse default).
  Each section repeats the logical-action list bound to concrete device tokens.

### Value token grammar [observed]

| Family | Examples | Meaning |
|---|---|---|
| `CTRL_BUTTON_<POS>` | `CTRL_BUTTON_RIGHT_DPAD_DOWN`, `CTRL_BUTTON_START`, `CTRL_BUTTON_LEFT_STICK` (107 uses) | abstract pad positions (PlayStation-style layout: left/right stick, dpad quadrants, top/bottom/quadrant buttons) |
| `LEFT/RIGHT_ANALOG_<AXIS>` | `LEFT_ANALOG_X`, `LEFT_ANALOG_EX`, `LEFT_ANALOG_EX_AUTO_NORTH`, `…_FORCE_EAST` | analog axes incl. auto-direction/force threshold variants |
| `JSBUTTON_n` | 1–16 | raw DirectInput joystick button |
| `JSROTATEX(±1000)` / `JSSLIDER(0,±1000)` | Gravis/WingMan hat emulation | axis+sign predicates |
| `KEYID_<NAME>` | `KEYID_E`, `KEYID_NUMPAD8`, `KEYID_LCONTROL`, `KEYID_ESC` | keyboard scancodes by name |
| `MOUSEID_LEFT_BUTTON` / `RIGHT_BUTTON` / `BUTTON_3` | | mouse buttons |
| `MOUSE(200),0` | `Player_TurnHoriz = MOUSE(200),0` | relative mouse axis, sensitivity 200 + polarity 0 [inferred] |
| `MOUSE_CLAMP_POS = 0,0,0,0,1,200` / `MOUSE_INITAL_POS = 0,0,150` (sic, typo in box) | | cursor clamping/centering params [inferred] |
| `QUERY_ALL_DEVICES = 1` | last line of UISCREENS sections | enumerate non-default joysticks [inferred] |

Default keyboard bindings (`ROTKDefault`): action `I`, killing move `M`, ranged `R`,
speed attack mouse-left, fierce mouse-right, parry `Q`, kick `LCTRL`, jump-back `TAB`,
move `WASD`, menu `ESC`, help `F1`, level-info `F2`, special ability `F5` [observed].
Multiple bindings per action allowed (e.g. `Player_Parry` = `KEYID_Q` **and**
`KEYID_NUMPAD4`) [observed].

Parsing semantics (precedence, device matching) are implemented in `ROTK.exe` —
**unknown** until the SafeDisc dump (`docs/research/safe-disc.md`).

## `filelist.txt` (364 B) — installer manifest [observed]

CSV `disc,type,path` lines (both ints; meanings **inferred/unknown**):

```
0,0,cache.dat            0,0,C_TMP00_.DAT        ← runtime/temp files, NOT on disk anymore
1,1,Support\*.*          1,1,eauninstall.exe     ← "type 1" = loose copy from disc 1
1,1,ROTK.exe  1,1,DivxMediaLib.dll  1,1,FileParser.dll  1,1,Input.ini
1,1,DivxDecoder.dll  1,1,rotk_uninst.exe  1,1,eax.dll  1,1,ROTK.ico
1,5,data_1.pac           2,5,data_2.pac          3,5,data_3.pac   ← "type 5" = PAC archives
3,5,00000001.TMP  3,5,00000002.TMP  3,5,DrvMgt.dll  3,5,SECDRV.SYS
3,5,00000000.256  3,5,00000000.016
```

The three `data_N.pac` names occur in the installer list and are absent from the
install [observed: re/corpus/listed_files.csv]. The retail PAC spec records a
comparison that matched all 83 file members to the installed `Data/` tree
[observed: PAC spec and re/corpus/manifest.csv]. This supersedes the earlier
disc-access blocker for identifying the format. The type-0 entries `cache.dat`
and `C_TMP00_.DAT` are also absent [observed: re/corpus/listed_files.csv].
[inferred: temporary files from their names.]

## `manifest.txt` (2,189 B) — installed-payload inventory [observed]

The 87 paths all resolve in the retail install [observed: re/corpus/listed_files.csv].
They cover 18 COTS mission scenes and 26 standalone LRTC files (GlobScen, LoadOnce and
24 character/follower packages), with `Ring.GEO` and `Ring.txw` as separate entries.
The prior count of 22 mission/global SCWs included the two Ring files. The list also
contains 21 `Data/Movies/*.avi`, 16 `Data/Special/*.avi` and four SafeDisc-related
files (`00000000.016`, `00000000.256`, `DrvMgt.dll` and `SECDRV.SYS`)
[observed: re/corpus/listed_files.csv, re/corpus/formats.csv and re/corpus/assets.csv].
The 24 player files form 12 `Char`/`Foll` pairs [observed: re/corpus/assets_scw.csv].
Stems are Ara, ArC, Far, FrD, Fro, Gan, Gim, Leg, Mer, Pip, SaC and Sam
[inferred: hero identities from the stems].

## `00000000.016` (307,324 B) and `00000000.256` (308,278 B) — BMP bitmaps

Both files classify as BMP despite the numeric suffixes [observed: re/corpus/formats.csv].
Their headers give 640×480, 8 bits per pixel and `biCompression=BI_RGB`
[observed: retail BMP headers]:

| File | offBits | palette | pixels | biSizeImage |
|---|---|---|---|---|
| `.016` | 0x7A | **17 entries** (partial: `f6edd2, e5cf9b, cfac6c, …` parchment/gold ramp) | 307,200 B, 15 distinct indices | 0 |
| `.256` | 0x436 | 256 entries (greyscale ramp starts `ffffff, 040404, 0c0c0c…`) | 307,200 B, 254 distinct | 0x4B000 |

The installer lists both bitmaps alongside `DrvMgt.dll` and `SECDRV.SYS`
[observed: re/corpus/listed_files.csv]. [inferred: SafeDisc resources, possibly
full-screen error or disc-prompt backdrops.] [unknown: exact use.]

## `SECDRV.SYS` (12,528 B) + `DrvMgt.dll` (41,472 B) — SafeDisc 3 support

- `SECDRV.SYS`: i386 PE kernel driver, sections `.text/.data/INIT/.rsrc/.reloc`,
  COFF timestamp 2003-03-19 11:33:46 UTC
  [observed: re/corpus/binaries.csv, re/corpus/pe_sections.csv]. Contains debug path
  `sys\secdrv.dbg` and the string `ecdrv.sys` [observed: retail driver strings].
  The version resource identifies the Macrovision security driver and gives file
  version `3.19.000` [observed: re/corpus/binaries.csv, re/corpus/libraries.csv].
- `DrvMgt.dll`: Win32 DLL, COFF timestamp 2003-07-25 10:25:36 UTC [observed: re/corpus/binaries.csv], with exports
  **`Remove`, `Setup`, `_DllMain@12`** [observed: pefile and re/corpus/binaries.csv
  (three slots)]. [inferred: install/remove helper for `SECDRV.SYS` from the
  export names and embedded driver-name string.]
- The executable’s SafeDisc fingerprint is documented in the [WP-1.1 scan](../research/safe-disc.md#wp-11--static-fingerprint-of-the-retail-executable).
  [unknown: division of runtime responsibilities among the executable, helper and driver.]

## `Support/` — installer & registration payloads

| File | Identification | Evidence |
|---|---|---|
| `config.xml` (897 B) | **EA Reg 2.0** registration client config: subs feed `https://account.ea.com/subsxml/subsxml.jsp`, `game-id GAME-LOTR-ROTK`, registry keys `HKLM\SOFTWARE\Electronic Arts\EA GAMES\LOTR The Return of the King tm\{ergc,MemberName,Registered}`, locale key under `EA GAMES\…\Locale`, `debug 1` | observed (full XML) |
| `EReg.exe` (1.44 MB) | EA Registration client (reads `config.xml`; stores serial under `ergc`) | inferred from config + name |
| `ereg-dict-<locale>.xml` ×12 (de, en_UK, en_US, es, fr_FR, it, ko, nl, pl, pt_BR, pt_PT, sv) | Localized string tables for EReg dialogs | [observed: re/corpus/assets.csv, 12 dictionary files plus config.xml] [inferred: role from names] |
| `EasyInfo.exe` (323,584 B) + `en-us_eahelp.hlp` (507,358 B) | EA "EasyInfo" system-info collector + Windows Help manual for support tickets | [observed: re/corpus/binaries.csv and re/corpus/assets.csv] [inferred: roles from names and WinHelp format] |
| `go_ez.exe` (69 KB) | "Get Online Easy" shortcut launcher | inferred |
| `en-us_eula.txt` (6.4 KB) | EULA; header observed: "SUPPLEMENTAL END USER LICENSE AGREEMENT FOR MICROSOFT SOFTWARE" — the *visible* file is the MS-component supplemental EULA, not the full EA EULA | observed |
| `readme.txt` (18.6 KB) | box readme, "Version 1.0, November 5, 2003" (dated after the October 2003 executable headers [observed: re/corpus/binaries.csv]) | observed header |
| `LOTR The Return of the King tm_{code,EZ,uninst}.exe`, `EAInstall`-era stubs | Installer support binaries. `tm_code.exe` identifies itself as CDKey in its version resource and has a `CDKey2.pdb` path. It shares the 290,816-byte size of `eauninstall.exe` and has a distinct hash | [observed: re/corpus/binaries.csv] [inferred: installer roles] |

## Root PE strays (identity recap)

`DivxMediaLib.dll`/`FileParser.dll`/`DivxDecoder.dll` — analyzed in
[companion-dlls.md](../analysis/companion-dlls.md). Creative’s `eax.dll`
(139,264 B) identifies itself as EAX Unified 3.066 and has COFF timestamp
2003-08-15 20:55:32 UTC [observed: re/corpus/binaries.csv, re/corpus/libraries.csv].
`EAXDirectSoundCreate8` is a string fingerprint in the packed executable
[observed: re/corpus/libraries.csv]. [unknown: runtime resolution of that API.]
`eauninstall.exe` and `rotk_uninst.exe` are EA uninstallers
[inferred: filenames and re/corpus/binaries.csv debug paths].
`ROTK.ico` is an icon file [observed: re/corpus/formats.csv]. The 2,874,240-byte
`ROTK.exe` is the packed game [observed: re/corpus/binaries.csv and
[SafeDisc fingerprint](../research/safe-disc.md#wp-11--static-fingerprint-of-the-retail-executable)].

## Unknowns / follow-ons

1. `.016`/`.256` exact render site — check the SafeDisc-dumped exe.
2. `filelist.txt` column semantics (disc/type?) — confirm against the original disc layout.
3. `Data\Player\Char_*` and `Foll_*` resource payloads [unknown]. All 24
   standalone LRTC files use 0x18-byte headers and walk to EOF, superseding
   the earlier leading-COHS coverage note
   [observed: re/corpus/assets_scw.csv and re/corpus/scw_chunk_summary.csv].
4. `cache.dat` producer/reader — probably the game's asset cache; verify post-dump.

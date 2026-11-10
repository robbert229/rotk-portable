# Misc installed files — provenance & formats

C7/D8 deliverable ([spec](../deliverables.md)). Covers every non-`.scw`/`.GEO`/`.txw`/
`.avi`/PE file in the retail install root and `Support/`. Claims tagged **observed**
(byte/text evidence at the cited location), **inferred**, or **unknown**.

Install root: `…\EA GAMES\LOTR The Return of the King tm\` (read-only corpus).

## `Input.ini` (34,157 B, dated 2003-10-03 in box)

INI file consumed by the game's input system (game imports DirectInput 8; the string
`kWinFE_InptCfg_*` front-end screens exist in `ROTK.exe` [observed: string cache]).
Structure [observed]:

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

**Key evidence for D6**: the game shipped as three `.pac` archives (`data_N.pac`, one per
disc, "type 5" = archived payload) which the installer **expanded** into `Data\` — they do
not exist post-install. This corroborates the D6 blocker (spec + `tools/unpac.py` need the
original discs/ISO). The type-0 entries (`cache.dat`, `C_TMP00_.DAT`) are runtime-created
and already absent [observed].

## `manifest.txt` (2,189 B) — installed-payload inventory [observed]

One path per line, backslash-separated: the full post-expand payload —
22 mission/global `.scw` (incl. `Data\Game\fro\Ring.GEO`/`Ring.txw`, the only standalone
mesh pair), 21 `Data\Movies\*.avi`, 16 `Data\Special\*.avi`, 24 `Data\Player\{Char,Foll}_*.scw`
(character/follower packages — **standalone LRTC containers**, observed via
`tools/scwdump.py`; 12 hero pairs — Ara, ArC, Far, FrD, Fro, Gan, Gim, Leg, Mer, Pip,
SaC, Sam [names inferred from stems]), and the four SafeDisc strays
(`00000000.016/.256`, `DrvMgt.dll`, `SECDRV.SYS`). Every listed file exists on disk
[observed]. Good coverage oracle for a `.pac` reimplementation once the ISO is available.

## `00000000.016` (307,324 B) and `00000000.256` (308,278 B) — BMP bitmaps

Both are plain **8-bit BMPs**, 640×480, `biCompression=BI_RGB` [observed]:

| File | offBits | palette | pixels | biSizeImage |
|---|---|---|---|---|
| `.016` | 0x7A | **17 entries** (partial: `f6edd2, e5cf9b, cfac6c, …` parchment/gold ramp) | 307,200 B, 15 distinct indices | 0 |
| `.256` | 0x436 | 256 entries (greyscale ramp starts `ffffff, 040404, 0c0c0c…`) | 307,200 B, 254 distinct | 0x4B000 |

Provenance [inferred]: listed in `filelist.txt` under disc 3 **next to** `DrvMgt.dll` +
`SECDRV.SYS` (SafeDisc components), and no game code path or asset-name reference exists
in `ROTK.exe` strings for them. They are SafeDisc 3's own resources — most plausibly its
full-screen error/"insert disc" backdrop(s) (17-colour parchment variant + 256-colour
variant). Exact use: **unknown** until the SafeDisc dump.

## `SECDRV.SYS` (12,528 B) + `DrvMgt.dll` (41,472 B) — SafeDisc 3 support

- `SECDRV.SYS`: i386 PE kernel driver, sections `.text/.data/INIT/.rsrc/.reloc`,
  TimeDateStamp 0x3E8E8A5A (2003-03-18) [observed: pefile]. Contains debug path
  `sys\secdrv.dbg` and the string `ecdrv.sys` [observed] — the well-known Macrovision
  **SafeDisc/SecuRom anti-copy driver** (also shipped with thousands of 2003 titles; it
  was the subject of the 2005 Sony-rootkit-era security uproar) [inferred: public
  knowledge, not re-verified here].
- `DrvMgt.dll`: Win32 DLL, TimeDateStamp 0x3F44A040 (2003-07-25), exports exactly
  **`Remove`, `Setup`, `_DllMain@12`** [observed: pefile] ⇒ install/remove helper for
  `SECDRV.SYS` ("driver manager") — the SafeDisc loader asks the user (or silently)
  installs the driver at first run [inferred].
- Together with the SafeDisc 3 packing of `ROTK.exe` (see README toolchain section) these
  confirm the copy-protection stack. No SafeDisc payload is in these files themselves —
  the protection core is inside `ROTK.exe`'s packed overlay.

## `Support/` — installer & registration payloads

| File | Identification | Evidence |
|---|---|---|
| `config.xml` (897 B) | **EA Reg 2.0** registration client config: subs feed `https://account.ea.com/subsxml/subsxml.jsp`, `game-id GAME-LOTR-ROTK`, registry keys `HKLM\SOFTWARE\Electronic Arts\EA GAMES\LOTR The Return of the King tm\{ergc,MemberName,Registered}`, locale key under `EA GAMES\…\Locale`, `debug 1` | observed (full XML) |
| `EReg.exe` (1.44 MB) | EA Registration client (reads `config.xml`; stores serial under `ergc`) | inferred from config + name |
| `ereg-dict-<locale>.xml` ×11 (de, en_UK, en_US, es, fr_FR, it, ko, nl, pl, pt_BR, pt_PT, sv) | localized string tables for EReg dialogs | inferred from naming |
| `EasyInfo.exe` (323 KB) + `en-us_eahelp.hlp` (495 KB) | EA "EasyInfo" system-info collector + Windows Help manual for support tickets | inferred from names/WinHelp format |
| `go_ez.exe` (69 KB) | "Get Online Easy" shortcut launcher | inferred |
| `en-us_eula.txt` (6.4 KB) | EULA; header observed: "SUPPLEMENTAL END USER LICENSE AGREEMENT FOR MICROSOFT SOFTWARE" — the *visible* file is the MS-component supplemental EULA, not the full EA EULA | observed |
| `readme.txt` (18.6 KB) | box readme, "Version 1.0, November 5, 2003" (ships **after** Oct 2003 exes — day-one-patch-era rebuild) | observed header |
| `LOTR The Return of the King tm_{code,EZ,uninst}.exe`, `EAInstall`-era stubs | installer support binaries (`tm_code.exe` is byte-identical size to `eauninstall.exe`, 290,816) | observed sizes; roles inferred from names |

## Root PE strays (identity recap)

`DivxMediaLib.dll`/`FileParser.dll`/`DivxDecoder.dll` — analyzed in
[companion-dlls.md](../analysis/companion-dlls.md). `eax.dll` (139,264 B, 2003-09-24) =
Creative EAX/DirectSound wrapper — game imports `EAXDirectSoundCreate8` [observed: string
cache]. `eauninstall.exe` / `rotk_uninst.exe` = EA uninstaller stubs [inferred].
`ROTK.ico` = shell icon. `ROTK.exe` (2,874,240 B) = SafeDisc-packed game
(`docs/research/safe-disc.md` governs it).

## Unknowns / follow-ons

1. `.016`/`.256` exact render site — check the SafeDisc-dumped exe.
2. `filelist.txt` column semantics (disc/type?) — confirm against the original disc layout.
3. `Data\Player\Char_*`/`Foll_*` `.scw` internals — **observed**: standalone **LRTC**
   container (same `header 0x18` + `COHS` index walk to 0x60 as `LoadOnce.scw`),
   1.5 MB chars / 512 KB followers; payload internals undecoded (same LRTC unknowns as
   GlobScen/LoadOnce).
4. `cache.dat` producer/reader — probably the game's asset cache; verify post-dump.

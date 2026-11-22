# Dump the retail ROTK executable in a Windows VM

WP-1.2 prepares this procedure for WP-1.4. The owner needs the original retail
install and play discs, their CD key, licensed Windows media and a host optical
drive. Keep the guest offline. Use only your own media and keep every binary
and runtime artifact private.

[observed: the WP-1.1 addendum in [SafeDisc research](safe-disc.md) identifies
the reference executable by SHA-256
`95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2`.
The `BoG_` marker at file+0xFD4 identifies SafeDisc 3.10.020. The separate
driver resource string is 3.19.000. The packed PE has eight sections, including
the space-named section, `stxt774`, and `stxt371` with the entry stub and
bootstrap imports.]

## Versions and launch route

| Tool | Pin and source |
| --- | --- |
| VirtualBox | [7.1.4](https://www.virtualbox.org/wiki/Download_Old_Builds_7_1), [7.1 manual](https://docs.oracle.com/en/virtualization/virtualbox/7.1/user/) |
| Guest | [Windows 7 SP1 x86](https://learn.microsoft.com/en-us/lifecycle/products/windows-7), build 7601, from owner media. [Windows XP SP3 x86](https://learn.microsoft.com/en-us/lifecycle/products/windows-xp), build 2600, is the native-driver fallback |
| x32dbg | [x64dbg snapshot_2025-03-15_15-57.zip](https://github.com/x64dbg/x64dbg/releases/tag/snapshot), use the `release\x32` tree |
| ScyllaHide | [v1.4](https://github.com/x64dbg/ScyllaHide/releases/tag/v1.4), `ScyllaHide_2023-03-24_13-03.zip` |
| Scylla | Scylla bundled with the pinned x32dbg snapshot, opened from its Plugins menu. [Upstream 0.9.8 reference](https://github.com/NtQuery/Scylla/releases/tag/v0.9.8) |
| SafeDiscShim | [0.9.0 prerelease](https://github.com/RibShark/SafeDiscShim/releases/tag/v0.9.0), Windows 7 compatibility attempt only |
| SafeDiscLoader2 | v1.3, [upstream design documentation](https://github.com/nckstwrt/SafeDiscLoader2/blob/v1.3/README.md), comparison only |
| Host Python | [3.13.0](https://www.python.org/downloads/release/python-3130/) reference version, or the checkout's existing Python 3. Use the WP-1.3 checkout revision of [validate_dump.py](../../tools/validate_dump.py). |

[inferred: start with the guest's native disc-authentication route. If Windows
7 blocks the driver, prefer SafeDiscShim over SafeDiscLoader2 for 3.10.020.
Shim emulates the driver interface and still uses disc authentication, which
keeps the run closer to the retail path. Loader2's advertised 2.0–4.9 range
covers 3.10.020 numerically, but it bypasses disc authentication and changes
the runtime path being measured.] [observed: upstream describes the two
approaches in the [Shim README](https://github.com/RibShark/SafeDiscShim)
and the Loader2 documentation above.] [unknown: Shim 0.9.0 compatibility with this guest and
this ROTK build. Upstream has a [Windows 7 failure report](https://github.com/RibShark/SafeDiscShim/issues/30).]

## 1. Install and verify a normal retail launch

1. In VirtualBox Manager click **New**, select **Windows 7 (32-bit)** and
   select your Windows installer media. Skip unattended installation. Assign
   2 GiB RAM, 2 virtual CPUs and a 25 GiB dynamically allocated disk. For an
   XP retry select **Windows XP (32-bit)** with IDE storage, 1 GiB RAM and
   1 virtual CPU. In **Settings → Network**, disable the adapter. Install
   Windows and log in as a guest administrator.
2. Shut down Windows. Select the VM, open **Snapshots**, click **Take** and
   name it `before-driver-install`. In **Settings → Storage**, select the
   optical device, use the disc icon to select the host optical drive, then
   enable **Passthrough**. Start the guest and insert retail disc 1.
3. In Explorer open the optical drive, double-click `Setup.exe` and follow
   the installer. Choose the full install if offered, enter your own key and
   swap discs when prompted. Decline online registration and automatic game
   launch. Find the installed `ROTK.exe` in Explorer and record its path.
   Shut down and take snapshot `after-game-install`.
4. Stage the pinned tool archives locally in the VM, for example by mounting
   a host-created tools ISO temporarily. Restore optical passthrough afterward.
   Insert the play disc specified by the box or installer. Start the guest,
   double-click the installed `ROTK.exe`, confirm the menu appears and quit
   through the menu. Record any request for administrator elevation and use the
   same elevation for x32dbg.
5. If Windows 7 reports a disabled or blocked driver, restore
   `after-game-install`, run `SafeDiscShim_Setup_0.9.0.exe` in the guest,
   accept installation, and repeat step 4 with the original disc inserted.
   If Shim installation or launch fails, repeat steps 1–4 with XP SP3 and
   native authentication. Keep the host driver configuration untouched.
   If the retail launch still fails, stop at the failure table below.

[inferred: physical drive passthrough is the starting configuration for
disc authentication. A logical ISO may omit protection-related disc data.]
[unknown: optical passthrough and menu launch on the owner's host.]

## 2. Configure x32dbg

1. Extract the x64dbg archive to `C:\Tools\x64dbg`. Merge the ScyllaHide
   archive's `x64dbg\x32\plugins` contents into the debugger's
   `release\x32\plugins` (create that folder if needed). Keep the v1.4
   `.dp32`, `HookLibraryx86.dll` and bundled configuration together.
   Create `C:\Dump` in Explorer.
2. Open `release\x32\x32dbg.exe`. In **Plugins → ScyllaHide → Options**
   select **Basic** and apply it. Start with the bundled profile unchanged.
   [observed: the [v1.4 Basic profile](https://github.com/x64dbg/ScyllaHide/blob/v1.4/ConfigCollection/scylla_hide.ini) enables PEB patches and leaves the thread-context and exception-dispatch hooks off.] This preserves the debugger’s access to CPU execution breakpoints. If a normal launch succeeds and debug launch fails, save the debugger log and try the attach discovery pass in §3.
3. In **Options → Preferences → Events** enable **System Breakpoint**.
   Use **File → Open** to select the installed `ROTK.exe`. At the first stop
   open **Memory Map** and record the live ROTK module base and all rows
   covering its `.text` section. For the reference file, `.text` starts at
   module base + `0x1000`, with virtual size `0x133C58`
   [observed: WP-1.1 packed section map]. In the CPU view use the command
   box below the disassembly for the commands in the next section.

## 3. Recognize and stop at the original entry point

[observed: static inspection from the PE entry points of `eauninstall.exe`
(RVA `0x9E1F`, SHA-256
`8308e2b8c9fab62ec3ad2446f4031582bd5f49291e6850cb39d3814ecd55dfdb`)
and `rotk_uninst.exe` (RVA `0x3EF6`, SHA-256
`77ed3454839afe80d3a5c37333e163311341b102e44ed72b10ef423072b19fd3`)
shows the same sequence. Push a frame-size immediate, push a handler
descriptor address, call the SEH setup helper, load `EDI` with `0x94`,
move it to `EAX`, then call the stack-probe helper. Save ESP in the frame,
use the new stack space as an OS version structure with size `0x94`, and
call indirectly through an import slot. The subsequent code reads the
version fields. See [toolchain provenance](toolchain.md) for the shared
7.00.9466 linker evidence.]

[inferred: this is the VC7 CRT startup family template for
`WinMainCRTStartup` / `mainCRTStartup`. The shared prologue alone cannot
distinguish those entry points. The stack size and addresses can differ
with link inputs.] [unknown: the exact ROTK OEP and whether the whole
template survives in its loaded image.]

1. For each ROTK `.text` memory-map region, enter `bpm ADDRESS,0,x`,
   replacing `ADDRESS` with the row's hexadecimal address. Press **F9**.
   The execute guard is a discovery aid. If EIP stops in `.text`, record
   the address before stepping. Search each live `.text` region by entering
   `findall ADDRESS, "6A??68????????E8????????BF940000008BC7"`.
   Inspect results in **References**. Double-click a match to inspect the
   instructions without changing EIP. Confirm the full sequence above.
   [observed: [execute guard](https://help.x64dbg.com/en/latest/commands/breakpoint-control/SetMemoryBPX.html)
   and [wildcard search](https://help.x64dbg.com/en/latest/commands/searching/findall.html)
   command semantics.]
2. If the first execute stop lands at the confirmed candidate, proceed
   directly to step 4. If it lands on a trampoline, follow direct control
   transfers with **F7** while paused and compare the destination to the
   candidate. If the guard was consumed early, the code is still encrypted,
   or the guard disrupts launch, stop the debug run. Start the game normally,
   wait for the menu, then in x32dbg use **File → Attach**, select
   `ROTK.exe` and search its live `.text` as in step 1. Treat this attach
   only as a discovery pass.
3. For a confirmed candidate discovered away from the current EIP, record
   candidate RVA = candidate VA minus live module base. Quit the discovery
   run, start fresh under x32dbg and stop at the system breakpoint. Verify
   there are no leftover memory guards in **Breakpoints**. Add the candidate
   RVA to the new live module base and enter `bph ADDRESS,x,1` with that
   hexadecimal VA. Press **F9**. Verify the breakpoint hit actually has
   EIP at that address and the decrypted code still matches the sequence.
   If no candidate matches, or multiple candidates survive inspection, stop
   and report the addresses and observed control flow. Never set EIP by hand.
4. Record EIP as the OEP VA, module base and derived OEP RVA. While x32dbg
   is paused, take a **running** VM snapshot named `at-oep` using
   **Machine → Take Snapshot**. Leave the process paused through import
   recovery and dumping.

## 4. Recover imports and save the image

1. In x32dbg choose **Plugins → Scylla**. Confirm the process ID and
   `ROTK.exe` main module. Set **OEP** to the recorded hexadecimal **VA**.
   Enable Scylla's IAT and OEP fix option. Keep the default IAT section name.
   [observed: [upstream Scylla source](https://github.com/NtQuery/Scylla/blob/master/Scylla/MainGui.cpp)
   uses the OEP VA for autosearch and derives the RVA when dumping.]
2. Click **IAT Autosearch** and accept the proposed range, then click
   **Get Imports**. Record the IAT VA, RVA, size and DLL list. If search
   fails or yields only bootstrap imports, toggle **Advanced IAT Search**
   in Scylla options and repeat once. When both ranges are offered, try both
   and retain the one whose resolved imports match game code.
3. Compare module names case-insensitively. [inferred: minimum expected set
   from the [roadmap](../roadmap.md) and engine inventory is
   `d3d8.dll`, `dinput8.dll`, `dsound.dll`, `eax.dll`,
   `DivxMediaLib.dll`, `kernel32.dll` and `user32.dll`. Other Windows
   imports such as `advapi32.dll`, `gdi32.dll` and `winmm.dll` are
   plausible.] [unknown: complete static import set and any redirected
   SafeDisc thunks.] Save the import tree with **Ctrl+S** as `C:\Dump\imports.xml`. Record unresolved
   entries by slot VA and current target. Preserve them for analysis and avoid
   guessing names or deleting groups to force a clean tree.
4. Click **Dump**, save as `C:\Dump\ROTK_raw.exe`, then click **Fix Dump**
   and select that raw file. Check the log for the output path and success.
   Copy the fixed output to `C:\Dump\ROTK_unpacked.exe`, retaining the raw
   file separately. If Fix Dump fails, preserve the raw image and logs as a
   failed attempt. Right-click the Scylla log pane, choose **Save** and write
   `C:\Dump\scylla.txt`. Save notes as `C:\Dump\vm-notes.txt`.

## 5. Transfer and validate on the host

After the capture, attach a dedicated USB transfer drive through
**Devices → USB** in the running VirtualBox window. In guest Explorer, copy
the files below to that drive, eject it in Windows and release it through
**Devices → USB**. Mount it on the host and copy out the fixed image,
raw image, import tree, Scylla log and VM notes. Put the supporting files
under `out/unpacked/` and the fixed image at `$ROTK_UNPACKED_EXE` if set,
otherwise `out/unpacked/ROTK_unpacked.exe`. Keep the VM snapshot private.
Check ignore coverage with `git check-ignore out/unpacked/ROTK_unpacked.exe`.
For a custom path, use a location outside the checkout or under an ignored
directory.

From the repo root after WP-1.3 lands, check its CLI help and run it against
the fixed image. Save stdout as the validation report and record the exit
status. Use the exact CLI in WP-1.3 if it differs from this planned invocation.

```sh
dump="${ROTK_UNPACKED_EXE:-out/unpacked/ROTK_unpacked.exe}"
python3 -I tools/validate_dump.py --help
python3 -I tools/validate_dump.py "$dump" > out/unpacked/validation.json
status=$?
cat out/unpacked/validation.json
printf 'validator exit: %s\n' "$status"
sha256sum "$dump"
```

[inferred: WP-1.3 checks PE structure, entry in `.text`, reduced `.text`
entropy, expected DLLs and calls/jumps from `.text` into SafeDisc
sections. The size check uses roughly 2,874,232 bytes as a comparison only.]
[observed: the numeric reference appears on
[PCGamingWiki](https://www.pcgamingwiki.com/wiki/The_Lord_of_the_Rings:_The_Return_of_the_King)].
Scylla's section padding and retained sections can change the size. Preserve
the output as captured. Residual stub references are input for WP-1.5.
WP-1.6 tests the subsequently repaired executable under Wine.

## Failures and handoff

| Symptom | Action |
| --- | --- |
| Installer or play disc unreadable | Check the physical disc and passthrough, confirm disc ID in guest Explorer, retry with the correct retail disc and record the drive and message. |
| Clean launch works, debugger launch exits or raises an exception | Record exception code, module, EIP and first/second chance. For a first-chance game exception use **Debug → Run (Pass exceptions)** once. Compare with the baseline and use the attach discovery pass. |
| No confirmed OEP | Save candidate RVAs, which executable regions were searched and where the debugger stopped. Stop before assigning an entry point. |
| Small bootstrap IAT, unresolved imports or no fixed output | Keep both search results, import tree, Scylla log and raw dump if available. Record failing slot addresses and module mappings. |
| Validator fails | Preserve its full report and the original artifact, record the failing checks and distinguish residual stub references from PE, entry, entropy or import failures. |

Report Windows edition/build, VM configuration and snapshot names, disc
edition and drive mode, packed executable SHA-256, launch route, tool builds,
ScyllaHide profile, PID, module base, OEP VA and RVA, IAT range and DLLs,
raw/fixed byte sizes and hashes, validator revision and result, and any
warnings or crashes. Keep logs and binaries local. WP-1.4 records the SHA-256
and a sanitized run summary in git. Omit the CD key and personal paths.

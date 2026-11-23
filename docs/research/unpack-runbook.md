# Dump the retail ROTK executable in a Windows VM

WP-1.4 captures the original entry point (OEP) and rebuilds the import
address table (IAT) for repair in WP-1.5. The owner needs the original retail
install and play discs, their CD key, licensed Windows media and a host optical
drive. Keep the guest offline. Use only your own media and keep every binary
and runtime artifact private.

[observed: the [WP-1.1 fingerprint](safe-disc.md#wp-11--static-fingerprint-of-the-retail-executable) identifies
the reference executable by SHA-256
`95af128c93c63fe5d847609b45f3ba146af56f01c76215389bd1aabf0eb2a5a2`.
The `BoG_` marker at file+0xFD4 has version fields 3, 10 and 20 at
marker+32.] [inferred: these identify SafeDisc 3.10.020.]
[observed: WP-1.1 fingerprint: the separate
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
| Scylla | Scylla x86 v0.9.8, `release\x32\Scylla.dll` in the pinned x64dbg ZIP [observed: bundled DLL version string]. Open through **Plugins → Scylla**. Use the [x64dbg Scylla fork](https://github.com/x64dbg/Scylla/tree/aa89026b9e469b0c4b3d2bedb464dd7ab521cd6e) for the UI. |
| SafeDiscShim | [0.9.0 prerelease](https://github.com/RibShark/SafeDiscShim/releases/tag/v0.9.0), Windows 7 compatibility attempt only |
| SafeDiscLoader2 | v1.3, [upstream design documentation](https://github.com/nckstwrt/SafeDiscLoader2/blob/v1.3/README.md), comparison only |
| Host Python | [3.13.0](https://www.python.org/downloads/release/python-3130/) reference version. Check `python3 --version` before validation. |

[observed: [Shim v0.9.0](https://github.com/RibShark/SafeDiscShim/blob/v0.9.0/README.md)
documents original-disc authentication. Loader2 v1.3 documents a disc-check
bypass.] [inferred: try native authentication first, then Shim to keep the
capture closer to the retail launch.] [unknown: Shim v0.9.0 compatibility
with Windows 7 and this ROTK build.] [observed: [Shim issue #30](https://github.com/RibShark/SafeDiscShim/issues/30)
reports a Theme Park Manager launch failure on Windows 10 with Shim 0.1.1.]

## 1. Install and verify a normal retail launch

Use an Intel or AMD x86-64 host. [observed: [VirtualBox 7.1 host and guest
requirements](https://docs.oracle.com/en/virtualization/virtualbox/7.1/user/Introduction.html).]

1. In VirtualBox Manager click **New**. Select **Windows 7 (32-bit)** and
   your installer media, skip unattended installation, and assign 2 GiB RAM,
   2 virtual CPUs and a 25 GiB dynamically allocated disk. For XP select
   **Windows XP (32-bit)** with IDE storage, 1 GiB RAM and 1 virtual CPU.
   In **Settings → Network**, disable the adapter. Install Windows and
   log in as a guest administrator.
2. Shut down. In **Settings → USB**, enable the controller and select
   **USB 1.1 (OHCI)**. Use a dedicated FAT32 drive. On Linux, check that
   your host login belongs to `vboxusers` with `id -nG`. If you add the
   membership, log out and back in before using VirtualBox. [observed:
   [Oracle USB setup](https://docs.oracle.com/en/virtualization/virtualbox/7.1/user/BasicConcepts.html#usb-support).]
   Copy the pinned ZIPs and Shim installer onto the drive and unmount it
   on the host. Boot the guest, select the drive under **Devices → USB**,
   verify the volume label in Explorer and copy the files to
   `C:\Tools\archives`. Eject the drive in Windows and release it via
   **Devices → USB**. Reuse this transfer route in §5.
3. On XP, do the extraction in §2 step 1 now. Open `x32dbg.exe` and
   confirm **Plugins → ScyllaHide → Options** opens before installing
   ROTK. If either fails, record the exact error and use XP for native-disc
   launch testing only. [observed: the [March release note](https://git.x64dbg.cn/x64dbg/x64dbg/releases/tag/2025.03.15)
   identifies the pinned build as XP-capable.] [unknown: full capture
   stack on the owner's XP guest.]
4. Shut down and take snapshot `before-driver-install`. In **Settings →
   Storage**, select the optical device, use the disc icon to select the
   host drive and enable **Passthrough**. Boot and insert retail disc 1.
   In Explorer open the optical drive and double-click `Setup.exe`.
   Choose the full install if offered, enter your key and swap discs as
   prompted. Decline online registration and automatic launch.
5. Find the installed `ROTK.exe` in Explorer and record its full path.
   In Command Prompt run `certutil -hashfile "FULL_PATH_TO_ROTK.EXE" SHA256`
   with that path. If unavailable on XP, transfer a private copy using step
   2 and run `sha256sum` on the host copy. Compare all 64 digits with the
   reference above. On mismatch, record the hash and disc edition and
   stop before §2. Shut down and take snapshot `after-game-install` with
   the staged archives still on the guest disk.
6. Boot with the play disc specified by the retail packaging or installer.
   Double-click the installed executable. Confirm the main menu appears,
   then quit through the menu. Record any elevation prompt and use the
   same elevation for x32dbg. For an explicit Direct3D or display-init
   error, save the exact message and stop. [unknown: ROTK Direct3D 8
   compatibility with the owner's VM configuration.]
7. For a disc or driver error or a silent exit before the menu on Windows 7,
   check the disc label in Explorer and record the outcome. In an elevated
   guest Command Prompt run `sc query secdrv` and `sc qc secdrv`.
   [observed: [Microsoft KB3086255](https://support.microsoft.com/en-us/servicing/os/windows-server/2015/09/ms15-097-description-of-the-security-update-for-the-graphics-component-in-windows-september-8-2015)
   documents manual start of secdrv.] If the start type is `DISABLED`,
   run `sc config secdrv start= demand` and `sc start secdrv` in the
   guest, record the outputs and retry step 6 once. If the service is
   absent or native launch still fails, restore `after-game-install` and
   run `C:\Tools\archives\SafeDiscShim_Setup_0.9.0.exe` in Windows 7.
   Complete the installer, restart and repeat step 6 with the same disc.
   If Shim installation fails or the disc/driver error or silent exit
   persists, repeat steps 1–6 on XP using native authentication.
   If XP fails to reach the menu or fails debugger preflight, record the
   result and stop before capture.

[inferred: physical drive passthrough is the starting configuration for
disc authentication. A logical ISO may omit protection-related disc data.]
[unknown: optical passthrough and menu launch on the owner's host.]

## 2. Configure x32dbg

1. Extract the x64dbg ZIP from `C:\Tools\archives` to `C:\Tools\x64dbg`. Merge the ScyllaHide
   archive's `x64dbg\x32\plugins` contents into the debugger's
   `release\x32\plugins` (create that folder if needed). Keep the v1.4
   `.dp32`, `HookLibraryx86.dll` and bundled configuration together.
   Create `C:\Dump` in Explorer. Reuse this setup if already done for XP preflight.
2. Open `C:\Tools\x64dbg\release\x32\x32dbg.exe` at the elevation recorded in §1. In **Plugins → ScyllaHide → Options**
   select **Basic** and apply it. Start with the bundled profile unchanged.
   [observed: the [v1.4 Basic profile](https://github.com/x64dbg/ScyllaHide/blob/v1.4/ConfigCollection/scylla_hide.ini) enables PEB patches and leaves the thread-context and exception-dispatch hooks off.] [inferred: leaving those hooks off should preserve hardware execution breakpoints.] If a normal launch succeeds and debug launch fails, save the debugger log and try the attach discovery pass in §3.
3. In **Options → Preferences → Events** enable **System Breakpoint** and
   clear **Entry Breakpoint**, **User TLS Callbacks** and **System TLS Callbacks**.
   Click **Save**.
   Use **File → Open** to select the installed `ROTK.exe`. At the first stop
   open **View → Memory Map** and record the live ROTK module base and all rows
   covering its `.text` section. For the reference file, `.text` starts at
   module base + `0x1000`, up to but excluding module base + `0x134C58`
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

1. At the system breakpoint, set `bpm ADDRESS,0,x` for each memory-map
   row overlapping the ROTK `.text` interval. Use the row's hexadecimal
   start for ADDRESS. Press **F9**. If a stop occurs outside the interval,
   record EIP and the reason. Resume from an ordinary breakpoint. For
   exceptions or process exit, use the failure table. At the first
   execute stop in the interval, record EIP and search each live `.text` row
   with `findall ADDRESS, "6A??68????????E8????????BF940000008BC7"`.
   Record matches in **References** before searching the next row.
   Double-click each match to inspect it. If the full pattern yields no
   matches, try `findall ADDRESS, "E8????????BF940000008BC7"` and inspect
   the preceding two pushes, allowing either immediate width for the frame
   size. [observed: [execute guard](https://help.x64dbg.com/en/latest/commands/breakpoint-control/SetMemoryBPX.html)
   and [pattern search](https://help.x64dbg.com/en/latest/commands/searching/findall.html)
   semantics.]
2. Compare the matches with the full sequence above. Record whether the
   first execute stop reached a candidate or a trampoline to it. Use
   **F7** to inspect a direct transfer. If the guard fails, the code
   still looks packed or the debugger launch fails, save the log and
   try one discovery pass. Start the game normally, wait for the menu,
   choose **File → Attach** and select `ROTK.exe`. Use **Debug → Pause**
   if running. Search the paused `.text` rows as in step 1. Use **File →
   Detach** and quit through the game menu.
3. Record the candidate RVA (candidate VA minus live module base). Start
   a fresh debugger run even if discovery stopped at that candidate.
   At the system breakpoint, verify **Breakpoints** has no leftover
   guards. Add the candidate RVA to the new live module base and enter
   `bph ADDRESS,x,1` for that VA. Press **F9**. Verify EIP reaches that
   address during startup and the decrypted code matches the full
   sequence. If the game exits, the candidate never hits or multiple
   candidates remain plausible, preserve the log, EIP, searched ranges,
   candidate RVAs and observed control flow. Stop before assigning an OEP.
4. Record EIP as the OEP VA, module base and derived OEP RVA. While x32dbg
   is paused, take a **running** VM snapshot named `at-oep` using
   **Machine → Take Snapshot**. Leave the process paused through import
   recovery and dumping.

## 4. Recover imports and save the image

1. With x32dbg paused, open **Plugins → Scylla**. Check the ROTK PID
   and main image base. Enter the recorded hexadecimal OEP **VA**.
   Under **Misc → Options**, check **Fix IAT and OEP**, keep `.SCY` as
   the IAT section name, clear **Use advanced IAT search**, and click
   **Accept**. [observed: the [fork's controls and handlers](https://github.com/x64dbg/Scylla/blob/aa89026b9e469b0c4b3d2bedb464dd7ab521cd6e/Scylla/MainGui.cpp)
   use the VA and derive the RVA.]
2. Click **IAT Autosearch**. Confirm a fresh `IAT Search Nor` result
   supplies a nonzero VA and size matching the fields, then click
   **Get Imports**. Use **Imports → Save Tree** to save
   `C:\Dump\imports-normal.xml`. Record VA, RVA, size, resolved DLLs,
   and invalid slots with their target addresses. [observed: a failed
   search can leave prior fields populated, per the fork's handler.]
3. If the search fails, yields only bootstrap imports or lacks the
   game-code evidence in step 4, enable
   **Use advanced IAT search** and repeat. If prompted, **Yes** selects
   advanced and **No** selects normal [observed: fork autosearch handler].
   Check each successful range against its fresh log entry before
   clicking **Get Imports**. Save the advanced tree as
   `C:\Dump\imports-advanced.xml`. If both ranges differ and the normal
   tree is missing, run autosearch again, choose **No** and save it.
4. Compare the candidates with the [WP-1.1 packed section map](safe-disc.md#packed-section-map).
   The bootstrap IAT is at file+0x19F0A6, corresponding to RVA 0x5C60A6
   with 16 four-byte slots [observed: packed IAT and section map].
   [inferred: prefer the range with slots referenced by decrypted game
   code beyond the bootstrap. Resolved game DLLs such as `d3d8.dll`,
   `dinput8.dll` and `dsound.dll` support that choice.]
   [unknown: complete static import set and redirected SafeDisc slots.]
   If both distinct ranges have support or neither does, preserve
   the trees and take only the raw dump and logs below. With one supported
   range, set its IAT VA and size, click **Get Imports**, and save
   `C:\Dump\imports.xml` via **Imports → Save Tree**. Keep invalid
   entries for repair.
5. Click **Dump**, save `C:\Dump\ROTK_raw.exe` and check for `Dump success`.
   With a selected tree and a successful dump, click **Fix Dump** and
   choose `ROTK_raw.exe`. Check for `Import Rebuild success` and verify
   `C:\Dump\ROTK_raw_SCY.exe` exists [observed: fork Fix Dump handler].
   Copy it to `C:\Dump\ROTK_unpacked.exe` and retain both source files.
   If either step fails, preserve whatever was produced.
6. Right-click the Scylla log pane and choose **Save**. Write
   `C:\Dump\scylla.txt` and save your notes as `C:\Dump\vm-notes.txt`.

## 5. Transfer and validate on the host

Reuse the USB drive from §1. In guest Explorer copy `ROTK_raw.exe`,
`ROTK_raw_SCY.exe`, `ROTK_unpacked.exe`, `imports.xml`, any alternate
import trees, `scylla.txt` and `vm-notes.txt` when available. Eject the
drive in Windows and release it from **Devices → USB** before mounting
it on the host. From the repo root, create `out/unpacked/` and copy the
files there. If `ROTK_UNPACKED_EXE` is set, copy `ROTK_unpacked.exe` to
that destination instead. For destinations inside the checkout, verify
each actual path with `git check-ignore -- PATH` before copying.

For WP-1.4, use a checkout containing WP-1.3b. Validate the unchanged
Scylla-fixed image before WP-1.5 repair. From the repo root run:

```sh
export ROTK_UNPACKED_EXE="${ROTK_UNPACKED_EXE:-out/unpacked/ROTK_unpacked.exe}"
make -s validate-dump VALIDATE_FLAGS=--pre-repair > out/unpacked/validation.json
status=$?
cat out/unpacked/validation.json
printf 'validator exit: %s\n' "$status"
sha256sum "$ROTK_UNPACKED_EXE"
```

[inferred: WP-1.3b pre-repair acceptance requires exit zero and JSON
`"ok": true`. The validator checks PE structure, entry in `.text`,
`.text` entropy and required imports. File size is advisory. The
2,874,232-byte comparison is documented in [WP-1.3's notes](dump-validator.md).
`DivxMediaLib.dll` is advisory because it may be late-bound. Pre-repair
mode reports call/jmp targets into SafeDisc sections for WP-1.5 without
failing on them. After WP-1.5 repair, point `ROTK_UNPACKED_EXE` at the
repaired image and run `make validate-dump` with `VALIDATE_FLAGS` unset.
The strict default requires zero such targets for the M1 validator
gate.] WP-1.6 tests the repaired image under Wine.

Hand WP-1.5 the unchanged Scylla-fixed image, capture evidence and
validator JSON privately. Keep all binaries (retail executable, raw
and fixed dumps, repaired image and staged tools), VM disks and
snapshots, import trees, raw logs and validator output private.
WP-1.4 may commit the Scylla-fixed SHA-256 in `re/corpus/unpacked.sha256`
and append a sanitized run summary here. The summary may include
other hashes and observed metadata. Omit CD keys and personal paths.

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

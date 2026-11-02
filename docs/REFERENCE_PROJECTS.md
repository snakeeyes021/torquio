# Other projects running Steinberg software on Linux

An audit (2026-11-02) of two projects that run Dorico and other Steinberg software under Wine, for anything
they solved that Torquio hadn't. Licences: Torquio is GPL-3.0; [vstenv](https://github.com/dguedry/vstenv) is
GPL-3.0 and its Wine patches are LGPL-2.1-or-later (Wine's licence), so both can be used with credit;
[steinberg_fix](https://github.com/chiarfe/steinberg_fix) is LGPL-2.1-or-later, but its `pwrshsip.dll` is
Microsoft's, copied from Windows, which nobody may redistribute.

| What they do | Who | Torquio | What we do |
|---|---|---|---|
| **Store credential attributes** (Wine's `CredWriteW`/`CredReadW` dropped them): Steinberg's License Engine keeps its refresh token with one, and without it resets the token on every start ("1.1 Format refresh token detecting -- resetting"), so the Activation Manager signs you out | vstenv (`advapi32-credential-attributes` patch) | No: our 2026-10-22 investigation concluded attributes weren't used, wrongly (the round-trip test didn't check them). Confirmed on the maintainer's machine: the reset is logged and the credential is gone | **v0.6.5:** their patch as Wine patch 0013, unchanged (it applies to our zhiyi/wine base), credited |
| Export `CloseThreadWaitChainSession` (HALion Sonic calls it on exit; Wine's stub raised an exception) | vstenv (same patch) | No | **v0.6.5**, with 0013; may be part of item 11 (HALion exception dump) |
| Allow empty virtual surfaces (`CreateVirtualSurface(0, 0)`, legal on Windows, backed on `Resize`); refusing them crashed HALion with a null dereference and a crash dump | vstenv (`dcomp-steinberg` patch) | No: our patch 0002 returns `E_INVALIDARG` | Backlog item 11: the lead to test against the HALion Sonic dump (needs HALion, maintainer's machine), then a fix in our dcomp patches |
| A PowerShell signature provider, so the Install Assistant trusts `preinstall.ps1` (MediaBay's error 231) | steinberg_fix (Microsoft's `pwrshsip.dll`, from Windows); vstenv works around it (runs the refused MSIs itself) | Workaround in v0.6.5 (installs the zip the Download Assistant leaves) | **v0.6.5:** Wine patch 0012, our own implementation of the PowerShell SIP in crypt32/wintrust (identifies `.ps1`, reads the `# SIG #` block, checks the UTF-16LE digest) |
| Guard `RevokeDragDrop` against a stale drop target left by WebView2 (crashed WebView2 apps on close) | vstenv (`ole32-dragdrop-stale-target` patch) | Partly: our patch 0006 covers drop targets of other processes' windows | Backlog: Cantai's editor is WebView2; port if it ever crashes on close |
| Download Assistant text: `-Dprism.lcdtext=false` in its launcher's `[JVMOptions]` (JavaFX's ClearType blending makes Wine's grey glyph masks bold and jagged), and built-in Direct3D for it (DXVK breaks its Direct2D glyphs) | vstenv | Not needed so far: Torquio uses Wine's own Direct3D, and the Download Assistant's text looks clean in testing | Backlog: compare with and without the option |
| GNOME "shell wedge": mutter can get a window stuck in `unmanaging` and then minimise every new Wine window off-screen until you log out (`journalctl --user -b \| grep meta_window_can_ping`) | vstenv (`shellwedge.py`) | No | Backlog: check it in the launchers and say so instead of looking hung (a Dorico that never showed its window was seen once in testing, but not this) |
| Session-wide DirectComposition wedge: every dcomp program hangs windowless until `wineserver -k` | vstenv (`wedge.py`, `launchguard.py`) | No | Backlog: worth a check in the launchers if users report Dorico not appearing |
| `Segoe UI` for DirectWrite: Selawik installed under that name (steinberg_fix: Noto Sans/DejaVu/Liberation as replacements) | both | Yes, differently: `Segoe UI` → Tahoma in Wine's font replacements, which DirectWrite honours | Nothing |
| A real `powershell.exe` for a few installer queries (process checks, service scripts) | vstenv (`tools/psshim`) | No: Wine's stub exits 0 | Note: with patch 0012 MediaBay's `preinstall.ps1` runs through the stub, so its "close MediaBay's clients and server" step does nothing. To check: whether the Download Assistant's update then fails while the MediaBay server runs (Torquio's own MediaBay installs stop it first) |
| DirectComposition, composition swap chains, frame pacing | both | Yes: patches 0001-0009 | Nothing |
| Wine Mono for the .NET Install Assistant | vstenv | Yes, differently: Microsoft .NET 4.8 | Nothing |
| Browser sign-in links (`net-steinberg-sda://`, `net-steinberg-activation-manager://`) | vstenv | Yes | Nothing |
| winetricks: corefonts, vcrun2022, dotnet48, DXVK, vkd3d, Windows 11 | steinberg_fix | allfonts, vcrun2019, dotnet48, Windows 10; vkd3d-proton only for Cantai | Nothing (Dorico runs on these) |
| Stale virtual-desktop monitor size, private `$XDG_RUNTIME_DIR/wine`, NI keyboard HID descriptors, Electron app fixes | vstenv | Not applicable (no virtual desktops; Torquio's Wine is in its container; Dorico doesn't use them) | Nothing |

Also from vstenv: the Activation Manager ignores clicks for a few seconds while the License Engine is busy with
a product that just started (a second click works).

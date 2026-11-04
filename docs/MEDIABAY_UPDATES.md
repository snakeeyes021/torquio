# MediaBay updates without errors: options

Status: **B implemented** (2026-11-04, backlog item 16, branch `feat/mediabay-native-script`; see "What Torquio
does" at the end). Decided earlier: v0.6.5 ships patch 0012 with the install-after-the-Download-Assistant
fallback; v0.7.0 runs `preinstall.ps1`'s step natively. Goal: the Download Assistant never reports a failed
MediaBay update. In v0.6.5 it could, once per MediaBay update (the fallback installs the update after that).

## What actually fails (found 2026-11-02/03)

The Download Assistant hands each MediaBay update to Steinberg's Install Assistant (`Setup.exe`, a .NET 4
program). Before installing `MediaBay.msi`, it runs the package's `preinstall.ps1` (it closes MediaBay's clients
and server), in two steps:

1. **Signature check:** `WinVerifyTrust` on the script. Wine had no PowerShell signature provider, so this failed
   (`TRUST_E_SUBJECT_FORM_UNKNOWN`): error 231, "not trusted". **Fixed by Wine patch 0012** (Torquio's own
   PowerShell SIP in crypt32/wintrust). Genuine scripts are trusted; changed or unsigned ones are still refused.
2. **Running the script:** not through `powershell.exe` but in the installer's own process, through Windows
   PowerShell's .NET library (`System.Management.Automation`: `AddScript`, `BeginInvoke`). Windows has it; Wine
   and .NET 4.8 don't. With patch 0012 the installer gets this far, can't run the script, quietly skips the
   MediaBay package, and still reports success (seen in a VM: `"success": true`, MediaBay still 1.3.70).

So a PowerShell shim or a real `powershell.exe` (winetricks' PowerShell 7 wrapper, vstenv's `psshim`) can't
help: nothing starts PowerShell as a program. Whether the Download Assistant now shows an error (the installer
says it succeeded, but MediaBay is unchanged) is untested; it needs a signed-in Download Assistant.

Steinberg's public MediaBay link, `https://www.steinberg.net/smb-win`, redirects to
`download.steinberg.net/.../steinberg-media-bay/<version>-<id>/MediaBay_Installer_win64.zip`: the version is in
the redirect, so a HEAD request says whether there's a newer one without downloading anything. It's the same zip
the Download Assistant downloads (same size, 71,548,137 bytes for 1.4.10.19).

## Options

| # | Option | Zero errors? | Effort | Risk |
|---|---|---|---|---|
| A | **Install the update before the Download Assistant tries.** When the Download Assistant is started (and on Update Torquio), ask Steinberg's public link for the current version; if it's newer than the installed MediaBay, download that zip from Steinberg and install it the way Torquio installs the user's zip, then start the Download Assistant, which finds MediaBay current. | Yes, as long as Torquio is first, which it is: the Download Assistant only runs through Torquio's launcher. | Small: the zip install exists (`install_mediabay.sh --zip`); add the version check and download (with progress, ~70 MB, only when there's an update). | Steinberg recommends the Download Assistant rather than this link, and the link could change or go away. If it fails, Torquio just starts the Download Assistant as today (no worse). The user downloads Steinberg's own file from Steinberg; Torquio ships nothing. |
| B | **Run the script in-process: our own `System.Management.Automation` for .NET Framework**, a small free implementation of the few PowerShell hosting calls the installer uses, installed into the prefix. Combined with patch 0012, the Install Assistant runs the step itself and installs `MediaBay.msi`: the Download Assistant's own update simply works. | Yes, the root fix: the update succeeds the normal way. | Medium to large: find the exact calls the installer makes (tracing which members it asks for), write and build the assembly (Mono's compiler, in CI), install it into the GAC. It has to carry Microsoft's public assembly identity (the public key token) to be loaded instead of the real one, as Mono's own framework assemblies do. The script's work (closing MediaBay) is done by Torquio before starting the Download Assistant, so the implementation can report success, like Wine's `powershell.exe`. | Fragile against new installer versions (other calls); the GAC identity needs care; future packages with scripts that matter would silently not run them. |
| C | **Run the package's MSIs in place of the failing step** (vstenv's way: unpack, run `MediaBay.msi` and `LibraryManager.msi` with msiexec). | Not by itself: the Download Assistant still runs the installer first, so whatever it reports stands; this is a variant of today's fallback (Torquio's zip install already runs `Setup.exe` without the script, which installs those MSIs and registers the content). | Small. | Same as today: one attempt per update by the Download Assistant before Torquio steps in. |
| D | **Today's fallback** (v0.6.5 as merged): after the Download Assistant closes, install the update it downloaded. | No: one failure per MediaBay update (Matt's objection). With patch 0012 the failure may now be silent (the installer reports success), but MediaBay is updated only after the Download Assistant closes. | Done. | None new. |
| E | Make the Download Assistant or Install Assistant skip MediaBay (edit their files or settings). | Yes. | Unknown. | Out: Torquio doesn't modify Steinberg's software. |

## Recommendation

Layer them, so the user never sees a failure and each layer covers the one above it:

1. **A, now (v0.6.5):** check Steinberg's public link before starting the Download Assistant and on Update
   Torquio; when there's a newer MediaBay, install it first. This gives zero errors in practice today.
2. **B, later (v0.7.x), as the root fix:** with our own PowerShell hosting library and patch 0012, the Download
   Assistant's own MediaBay updates succeed the normal way, even when Steinberg's link changes. Start by tracing
   exactly which calls the installer makes, to size the work before committing to it.
3. **D stays as the safety net** for when the link can't be reached and B isn't there: after the Download
   Assistant closes, Torquio installs the update it downloaded.

Patch 0012 stays in either case: it's correct on its own (signed scripts are verified the way Windows does), and
B needs it.

## What Torquio does (v0.7.0: option B, plus D as the safety net)

**What the installer calls** (traced 2026-11-04 by decompiling the Install Assistant's managed code, only for the
calls it makes; the same `Setup.exe` build, SHA-256 `6b8c8aa3...`, ships in MediaBay 1.3.70, 1.3.80 and 1.4.10): it
references `System.Management.Automation, Version=3.0.0.0, PublicKeyToken=31bf3856ad364e35`, and only in
`Prerun.run_powershell`: `PowerShell.Create()`, `AddScript(File.ReadAllText(script))`, `AddParameters(IList)`
(when setup.xml gives parameters), `Invoke()` (a `Collection<PSObject>`, ignored), then `Streams.Information`,
`.Warning` and `.Error` (each a `PSDataCollection<...Record>`, enumerated, every record's `ToString()` written to
its log), and `Dispose()`. There's no `BeginInvoke`. Any error record, or an exception, fails the package with
error 230 (unless setup.xml says `ignore_return`). Without the assembly, the JIT fails to compile that method and
the package is skipped. Post-run programs (`RunAfterInstallation`) are started as programs, not through
PowerShell.

**Which packages have scripts:** of the Steinberg installers checked (MediaBay 1.3.70/1.3.80/1.4.10, Dorico
6.2.20/6.2.30, Cubase 15.0.30, HALion Sonic 7.1.51/7.5.0, Groove Agent SE 6.0.20/6.0.30, Yamaha Omnivocal 1.2.5),
only MediaBay has a PowerShell pre-run (`preinstall.ps1`). Dorico, Cubase and Omnivocal pre-run
`vc_redist.x64.exe`, which the installer starts as a program (unaffected); the others have none.

**What `preinstall.ps1` does:** if MediaBay and the Activation Manager's `silkupdatehelper.exe` are installed, it
asks the helper whether a program has MediaBay's client library (`mediaclient.dll`) loaded, and if so asks it to
close those programs (cancelling the installation, with an error, if they aren't closed); then it stops
`SteinbergMediaBayServer.exe` (`taskkill /F`).

**That step matters:** with the MediaBay server running, MediaBay.msi "succeeds" (the installer reports success
and the registry says 1.4.10), but Wine's msi can't replace the files in use: `medialib.dll`,
`SteinbergMediaBayServer.exe` and `Components\videometadata.dll` stay at 1.3.70, with the new ones left as
`msic*.tmp` for a rename at the next Wine restart (seen in the VM, 2026-11-04). Torquio didn't close the server
before starting the Download Assistant (only before its own MediaBay installs), so the stand-in does it.

**The stand-in** (`scripts/2-install/powershell_host/System.Management.Automation.cs`, GPL-3.0-or-later, about 600
lines of C# 5 with the members above and a few neighbours): it doesn't interpret scripts. For MediaBay's script
(recognised by `SteinbergMediaBayServer.exe` in it) it does the script's job without asking: if a process has
`mediaclient.dll` loaded, it returns an error record ("MediaBay is in use by ... Close Dorico and Steinberg's other
programs, then update MediaBay again"), so the installer cancels the MediaBay package cleanly (error 230, nothing
changed), as on Windows when the clients aren't closed; otherwise it stops MediaBay's server and reports success.
Any other script reports success without running, and the log says so (with a short hash of the script). The
installer writes these messages to its log (`Prerun: Torquio: ...`).

**Build and install** (`scripts/2-install/install_powershell_host.sh`, run by `setup_prefix.sh`, so during prefix
setup, after Update Torquio and from Fix Icons & Refresh Launchers): compiled in the prefix with its own .NET
Framework 4.8 compiler (`csc.exe`, from winetricks `dotnet48`, about 10 s), so no build tools are added and nothing
prebuilt is committed; delay-signed with the public key of token 31bf3856ad364e35 (a public identity: Mono's
WindowsBase.dll carries the same key; no private key is involved, and the script checks the token), and copied
into `C:\windows\Microsoft.NET\assembly\GAC_MSIL\System.Management.Automation\v4.0_3.0.0.0__31bf3856ad364e35\`.
The .NET 4 GAC loads it as it is: no strong-name skip-verification entry was needed (none exists in the prefix).
It's rebuilt only when its source changes, and a `System.Management.Automation` that isn't Torquio's is left alone.
CI checks that it compiles as C# 5 (Mono's `mcs`).

**Verified** (Fedora 44 VM, engine `build-3f3a8cb19fee` with patch 0012, MediaBay 1.3.70 installed, the 1.4.10
package with its `preinstall.ps1`, run as the Download Assistant runs it: `Setup.exe --silent`):

| Case | Result |
|---|---|
| Without the stand-in | success reported, MediaBay package skipped, still 1.3.70 (2026-11-02) |
| Stand-in, server not running | `preinstall.ps1 executed successfully`, MediaBay 1.4.10, all files new |
| Stand-in, old server running | stand-in stopped the server; 1.4.10, all files new, no pending renames |
| Stand-in, a process with `mediaclient.dll` loaded | error 230 with the stand-in's message; MediaBay unchanged at 1.3.70, nothing pending |
| Installed by `setup_prefix.sh` and by `torquio --post-update` (Update Torquio) | built and installed; the next run says "up to date" |

The updated MediaBay server starts. Not verified: the Download Assistant's own update (it needs a signed-in
account) and the "in use" case with a real Dorico (the VM's Dorico isn't activated, so it never loads MediaBay).

**Option A is no longer needed**; D stays as the safety net (after the Download Assistant closes, with no Steinberg
program open, Torquio installs an update it downloaded but didn't install, e.g. one cancelled because Dorico was
open).

**Risks:** a newer Install Assistant calling members the stand-in doesn't have would fail that package (a
`MissingMethodException`; the log would show it); a future Steinberg package whose PowerShell script does more
than MediaBay's would have it skipped; other programs in the prefix that look for Windows PowerShell's library
would find this one, which doesn't run scripts.

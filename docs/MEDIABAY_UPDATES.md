# MediaBay updates without errors: options

Status: **brainstorm** (2026-11-03), for deciding how v0.6.5 handles MediaBay updates. Goal: the Download
Assistant never reports a failed MediaBay update. Today it does, once per MediaBay update (v0.6.5's current fix
installs the update after that failure).

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

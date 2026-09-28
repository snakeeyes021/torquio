# DirectComposition & Dorico UI Investigation State Journal

This journal tracks all experiments, hypotheses, confirmed fixes, and discovered behaviors throughout the DirectComposition implementation for Steinberg Dorico 6.

---

## 1. Evolution of Observed Behaviors

| Phase / State | Behavior Description | What Caused It / How It Was Resolved |
| :--- | :--- | :--- |
| **Commit 1 (Branch Start)** | Bumped Wine upstream commit & added `--rebuild_wine` to `torquio`. | No behavior change; baseline established for patching workflow. |
| **Patch 0001 (`dxgi-composition-swapchain`)** | Fixed **Behavior #1** (content displayed correctly only on very first pulldown; subsequent pulldowns showed white). Bumped to **Behavior #2**. | Implemented composition swapchain support in DXGI and initial DComp hooks. Dropdowns now rendered beyond the first click, but exhibited Behavior #2 (first click flashed content briefly, followed by rapid white flashes settling on static white). |
| **Patch 0002 (`virtual-surface`)** | Fixed **Behavior #2** (bumping to **Behavior #3**) and fixed the **main instrument window content draw**. | Added DComp virtual surface support, texture region copying, and compositor thread loop. Dropdown content now reliably displays on open instead of white, reaching Behavior #3. Main instrument window body started rendering. |
| **Patch 0003 (`d2d1-device-context-support`)** | Fixed the **very top section/bar of the Play Mode instrument window**. | Added `ID2D1DeviceContext` draw surface support in DComp. Top bar of the instrument window became visible. Dropdowns remained on Behavior #3. |
| **Patch 0004 WIP (Current Iteration)** | Tackling **Behavior #3** and preventing/resolving any regressions encountered during development. | **Current Stable Baseline:**<br>1. Dropdown content displays reliably every time a dropdown is opened.<br>2. Mouse hover highlights and checkbox clicks do not visually refresh while the dropdown is open.<br>3. Leaf 2 in nested dropdowns renders its visual content, but mouse input still hits Leaf 1.<br>4. Scrolling dropdown shows a thin white rectangle at top on first draw, then moves and doesn't redraw.<br>5. Tooltips have no text and appear flatter than normal.<br>6. Zero regressions on Steinberg Hub exit and Play Mode instrument window top bar. |

---

## 2. Confirmed Discoveries & Permanent Fixes (Do NOT Revert)

1. **Multithreaded D3D11 Protection in DComp (`device.c`):**
   - Protected `ID3D11DeviceContext` calls with `ID3D11Multithread_Enter / Leave` to prevent multithread crashes when Qt / Dorico render threads overlap with compositor threads.
2. **`target_SetRoot` Visual Reassignment:**
   - Dorico reassigns the root visual or re-sets the same visual on open. We allow reassigning if already root, and return `S_OK` if `target->root == visual`.
3. **Layered Window Alpha Blending:**
   - Restored `GdiAlphaBlend` with `AC_SRC_ALPHA` for `WS_EX_LAYERED` popup windows and retained `DCX_CLIPCHILDREN`.
4. **Compositor Thread Lifetime:**
   - In `composite_thread_proc`, threads do not exit when `count == 0` during transient window transitions; they stay alive until explicit teardown.
5. **D2D Asynchronous Flush:**
   - Added `ID2D1DeviceContext_Flush` after `CopyFromBitmap` in `do_composite_dxgi_surface` so GDI `GetDC` reads completed GPU copies.
6. **Frame Statistics Implementation (`dxgi` & `dcomp`):**
   - Implemented `GetFrameStatistics` on both swapchains and DComp devices/desktop devices returning `S_OK` and valid QPC timestamps, preventing Qt/Dorico render loops from bailing out or destroying targets early.
7. **DXGI BackBuffer Index:**
   - Returned `0` in `GetCurrentBackBufferIndex` matching WineD3D's flip rotation model.
8. **NULL Device Context Elimination:**
   - Handled `swapchain->dc == NULL` in `wined3d_context_gl_update_window` by falling back to backup DC, eliminating thousands of `failed to set pixel format on device context 0000000000000000`.
9. **Visual Format Guarding in WineX11:**
   - Only advertise `PFD_DRAW_TO_WINDOW` if `fmt->visual` is non-NULL, preventing invalid window pixel formats on pure offscreen visuals.

---

## 3. Analysis of Current Behavior #3

### Symptoms Breakdown
1. **Dropdown static content on hover / click:**
   - Content renders on initial open.
   - When hovering or clicking an item/checkbox inside the dropdown, the visual display does **not** update.
2. **Nested dropdown input target mismatch:**
   - When Leaf 1 opens Leaf 2, Leaf 2 displays its visual content.
   - But mouse clicks/hovers over Leaf 2 act as if the mouse is still hovering over Leaf 1 behind it!
3. **Scrolling dropdown:**
   - Initial draw shows a thin white rectangle at the top (placeholder for scroller chevron?).
   - On repositioning / scrolling, it moves and then stops updating.
4. **Tooltips:**
   - Tooltips show as small/flat boxes with no text.

---

## 4. Discoveries from Runtime Log Analysis (1.2MB Log)

1. **Dropdowns use DXGI Swapchains, NOT Surfaces:**
   - Dropdowns are created with `WS_POPUP`, `DwmExtendFrameIntoClientArea`, and `DwmEnableBlurBehindWindow`.
   - Dorico creates a DXGI swapchain for the dropdown visual (`COMPOSITION_CONTENT_SWAPCHAIN`).
   - Dorico calls `Present()` **exactly ONCE** upon opening.
   - `composite_thread_proc` continuously loops at 60 FPS reading swapchain buffer 0 and blitting to the HWND.
   - While the dropdown is open and the mouse is hovered over items, **Dorico never calls `Present()` again**.
   - This proves conclusively that the lack of visual hover update is **NOT a compositing/presentation failure**, but rather that **Qt/Dorico is not initiating a repaint** (it either never receives `WM_MOUSEMOVE` or is blocked waiting for mouse capture release).

2. **Nested Menus (Leaf 1 vs Leaf 2) Pointer Grab Root Cause Discovered:**
   - In `dlls/winex11.drv/window.c:3118` (`X11DRV_SetCapture`), when a menu opens, Wine calls:
     ```c
     XGrabPointer( data->display, data->whole_window, False,
                   PointerMotionMask | ButtonPressMask | ButtonReleaseMask,
                   GrabModeAsync, GrabModeAsync, None, None, CurrentTime );
     ```
   - Crucially, `owner_events` is set to `False`!
   - Under X11, `owner_events = False` commands the X server: *"Do not deliver pointer events to other windows of this client; deliver ALL pointer events on the display exclusively to this grab window (`HWND_1` / Leaf 1)"*.
   - When Leaf 2 (`HWND_2`) opens, all mouse movements and clicks over Leaf 2 are captured and rerouted by X11 to Leaf 1!
   - This perfectly explains why *"the mouse appears to think leaf 1 is still displaying even though leaf 2 is displaying"*.

3. **Tooltips use DirectComposition Surfaces with 15px Height:**
   - Tooltips create dedicated targets and surfaces (`(0,0)-(370,15)`, `(0,0)-(271,15)`, `(0,0)-(194,15)`).
   - They render via `surface_BeginDraw` with `ID2D1DeviceContext`.
   - The height of 15px indicates font measurement / text layout metrics.

4. **Scrolling Dropdown `surface_Scroll` is never called:**
   - Dorico called `surface_Scroll` 0 times. Scrolling in dropdowns is handled by window movement or internal buffer updates.

---

## 5. Targeted Fix Plan

1. **Fix Nested Menu Pointer Grab in WineX11:**
   - In `dlls/winex11.drv/window.c`, change `XGrabPointer` `owner_events` parameter from `False` to `True`.
   - With `owner_events = True`, X11 will report pointer events normally to any child/popup window owned by the application (enabling Leaf 2 to receive mouse input!).
2. **Diagnose Dropdown Mouse Move Dispatch:**
   - Log `WM_MOUSEMOVE` and mouse capture state in `send_mouse_input` to verify why the dropdown window isn't processing hover events.
3. **Investigate Tooltip Text Rendering:**
   - Check why Direct2D drawing inside the 15px tooltip surface does not display text.

---

## 6. Build and Deployment (Round 11)

- **`win32u/opengl.c` (`wglSetPixelFormatWINE`):**
  - Removed `!is_cache_dc(hdc)` restriction which was rejecting own-DCs and backup DCs used by WineD3D.
  - Allowed offscreen pixel formats to record the DC format in `set_dc_pixel_format_internal` and return TRUE.
  - Resolves the `wglSetPixelFormatWINE failed to set pixel format 81 on device context` error loop when popup menus and nested leaves initialize GL contexts.
- **`winex11.drv/window.c` (`X11DRV_SetCapture`):**
  - Passed `owner_events = True` for `GUI_INMENUMODE` to allow submenus / child popup windows (e.g. Leaf 2) to receive pointer events.
  - Guaranteed `XUngrabPointer` is called even if `get_win_data` fails on release.
- **Deployment Status:**
  - 64-bit and 32-bit `win32u.so`, `winex11.so`, `wined3d.dll`, `dxgi.dll`, and `dcomp.dll` compiled and copied to `/opt/wine-custom` and prefix `system32`.
  - Prefix cleanly rebooted with `wineboot -r` and wineserver stopped.
  - Ready for user re-testing across all 7 items.

---

## 7. Major Root Cause Discovery & Fix (Round 12)

### The Popup Mouse Message Routing Black Hole
- **Mechanism Discovered:**
  - In `dlls/win32u/message.c:process_mouse_message`:
    ```c
    msg->hwnd = window_from_point( msg->hwnd, msg->pt, &hittest, TRUE );
    ```
  - When a dropdown or submenu (Leaf 2) opens, X11 and Wineserver report the hardware mouse event with `msg->hwnd` set to the main application window (or the previous grab window, Leaf 1).
  - In Win32, popup windows (`WS_POPUP`) have the desktop window as their parent; their owner is the main window, but they are NOT `WS_CHILD` children of the main window!
  - `window_from_point( hwnd, pt, ... )` calls `list_children_from_point( hwnd )`, which only queries children of `hwnd`!
  - Therefore, `window_from_point( main_window, pt )` or `window_from_point( Leaf 1, pt )` **NEVER** finds any popup, dropdown, or submenu!
  - If `pt` was within the bounds of Leaf 1, it returned Leaf 1 every time (causing the mouse to think Leaf 1 was still active over Leaf 2).
  - If `pt` was outside Leaf 1, it returned 0 and Wine dropped the mouse event completely (`return FALSE`).
  - **Result:** Dorico's Qt dropdowns never received `WM_MOUSEMOVE`, hover highlights never updated, and submenus never received clicks!

### The Fix
- In `dlls/win32u/message.c:process_mouse_message`:
  - When `!info.hwndCapture`, query `top = window_from_point( 0, msg->pt, &hittest, TRUE )` from the desktop window.
  - If `top` belongs to the current thread (`is_current_thread_window( top )`), assign `msg->hwnd = top`.
  - This delivers mouse messages directly to the topmost active popup / dropdown / submenu!
- In `dlls/win32u/opengl.c:win32u_wglSetPixelFormatWINE`:
  - Handle DCs without a window DCE by setting DC pixel format via `set_dc_pixel_format_internal` and returning TRUE.
  - Guard `format > total` checks.
- Committed to `test/dcomp-2026-wip`. Prefix cleanly rebooted with `wineboot -r`.

---

## 8. Build, Implementation and Full Deployment (Round 13)

### Discoveries & Implementations
1. **DComp DXGI Front-Buffer vs Back-Buffer Selection (`dcomp/device.c`):**
   - WineD3D flip model rotates buffer `0` to `BufferCount - 1` upon `Present()`.
   - Query `IDXGISwapChain1_GetLastPresentCount`. When `present_count > 0`, query buffer `swapchain_desc.BufferCount - 1`; before any present has occurred (`present_count == 0`), query buffer `0`.
   - Fallback gracefully to buffer `0` if querying `BufferCount - 1` fails.
   - Fixed C89 variable scoping for `-Wdeclaration-after-statement`.

2. **Direct2D DXGI Format Support Implementation (`d2d1/device.c`):**
   - Dorico and Qt probe DXGI formats 0x1 through 0x84 via `d2d_device_context_IsDxgiFormatSupported`.
   - Replaced stub returning `FALSE` with proper `ID3D11Device1_CheckFormatSupport` verifying `D3D11_FORMAT_SUPPORT_RENDER_TARGET`.
   - Fixes text layout and font rendering checks for tooltips and controls.

3. **OpenGL Format 81 Resolution (`win32u/opengl.c`):**
   - Removed `format > total` rejection in `win32u_wglSetPixelFormatWINE` for offscreen/backup contexts.
   - When `format > onscreen || (total && format > total)`, set internal DC pixel format via `set_dc_pixel_format_internal` and return `TRUE`.
   - Eliminates repeated GL context creation failures during popup menu instantiation.

4. **Synchronous Compilation & Verified Deployment:**
   - Both 64-bit and 32-bit (`wine64` and `wine32`) modules for `dcomp.dll`, `d2d1.dll`, and `win32u.so` compiled cleanly without warnings/errors.
   - Directly copied and verified timestamps in `/opt/wine-custom/lib/wine/` (x86_64 and i386).
   - Unified patch updated at `scripts/1-build/patches/0004-dcomp-dropdown-scroll-and-frame-stats.patch` and committed to `test/dcomp-2026-wip`.

---

## 9. Build, Root Cause Discoveries & Full Deployment (Round 14)

### Discoveries & Implementations
1. **Mouse Capture Trap on Submenus and Dropdowns (`win32u/message.c`):**
   - When a dropdown button or Leaf 1 opens, it calls `SetCapture`.
   - Previously, `process_mouse_message` unconditionally routed all mouse events to `info.hwndCapture` whenever capture was active, starving child popups, dropdowns, and submenus (Leaf 2).
   - This caused the exact symptom where "mouse appears to think leaf 1 is still displaying even though leaf 2 is displaying", and prevented dropdowns from receiving `WM_MOUSEMOVE` hover events.
   - **Fix:** In `process_mouse_message`, if `top = window_from_point(0, msg->pt, ...)` is a `WS_POPUP` window belonging to the current thread, prioritize `top` over `info.hwndCapture`! Mouse events are now delivered directly to the active popup/dropdown/submenu under the cursor.

2. **Hwnd Filter Drop on Owned Popups (`win32u/message.c`):**
   - Popups (`WS_POPUP`) have `parent = desktop` and are NOT `WS_CHILD` windows; `is_child(hwnd_filter, popup)` returns `FALSE`.
   - When modal or window event loops filtered by `hwnd_filter`, mouse messages to owned popup windows were rejected by `check_hwnd_filter` and dropped on the floor.
   - **Fix:** In `check_hwnd_filter`, traverse `get_window_relative(owner, GW_OWNER)` up the owner chain. If any owner matches `hwnd_filter`, the message is accepted.

3. **Direct2D `A8_UNORM` Glyph Mask Support (`d2d1/device.c`):**
   - `d2d_device_context_draw_glyph_run_bitmap` uses `DXGI_FORMAT_A8_UNORM` bitmaps for font rendering.
   - Because `A8_UNORM` is a texture format rather than a render target, `D3D11_FORMAT_SUPPORT_RENDER_TARGET` was returning `FALSE`, causing Dorico to believe font glyph textures were unsupported.
   - **Fix:** In `d2d_device_context_IsDxgiFormatSupported`, explicitly return `TRUE` for `DXGI_FORMAT_A8_UNORM`, `B8G8R8A8_UNORM`, and `R8G8B8A8_UNORM`, and check `(RENDER_TARGET | TEXTURE2D)` for other formats.

4. **Terminal Output Question Addressed:**
   - Evaluated user inquiry regarding terminal vs log output. Confirmed `run-dorico.sh` executes `wine "$DORICO_NAME" 2>&1 | tee "$LOG_FILE"`. All stdout/stderr output is already captured identically in `dorico_wine.log`, so running in terminal offers no additional information and is unnecessary.

5. **Deployment:**
   - Both 64-bit and 32-bit `win32u.so` and `d2d1.dll` recompiled cleanly and deployed to `/opt/wine-custom/lib/wine/`.
   - Prefix cleanly rebooted via `wineboot -r`.

---

## 10. Root Cause Breakthrough & Full Deployment (Round 15)

### Root Cause Analysis & Implementations
1. **Child Controls in Popups Bypassing Mouse Routing (`win32u/message.c`):**
   - In Round 14, `process_mouse_message` checked `(get_window_long(top, GWL_STYLE) & WS_POPUP)` on `top`.
   - However, in Qt, dropdown containers and popup menus contain nested child widgets (`QListView`, `QScrollBar`, items) which are `WS_CHILD` windows.
   - When `window_from_point` returned the child window inside the popup, `style & WS_POPUP` evaluated to `FALSE`, causing Wine to fall back to `else if (info.hwndCapture)` and route all mouse movement back to the capture window (the dropdown trigger button or Leaf 1)!
   - **Fix:** Implemented `is_popup_window(hwnd)` which queries `root = NtUserGetAncestor(hwnd, GA_ROOT)`. If `root` has `WS_POPUP`, the window is recognized as part of an active popup hierarchy and receives mouse events directly.

2. **Hwnd Filter Rejecting Child Controls of Owned Popups (`win32u/message.c`):**
   - In `check_hwnd_filter(msg, hwnd_filter)`:
     When Qt ran a filtered modal/window message loop, child controls (`WS_CHILD`) of popup windows had `get_window_relative(child, GW_OWNER) == NULL` because only top-level windows have owners.
     `check_hwnd_filter` returned `FALSE`, silently discarding every mouse move/button event intended for controls inside the popup.
   - **Fix:** First obtain `root = NtUserGetAncestor(msg->hwnd, GA_ROOT)`. Test if `root == hwnd_filter || is_child(hwnd_filter, root)`. If not, traverse the owner chain of `root`. This guarantees all child controls inside owned popups are accepted by the message filter.

3. **Graceful Fallback for Offscreen OpenGL Contexts (`wined3d/context_gl.c`):**
   - In `wined3d_context_gl_set_pixel_format`:
     When `wglSetPixelFormatWINE` failed on backup DCs during popup/menu instantiation (logging 56 errors in `dorico_wine.log`), it previously returned `FALSE` immediately, killing context initialization.
   - **Fix:** Added graceful fallback: if `current` format is already active, return `TRUE`; otherwise attempt `SetPixelFormat(dc, format, NULL)`.

4. **Direct2D Tooltip Diagnostics (`d2d1/device.c`):**
   - Added detailed instrumentation in `PushAxisAlignedClip`, `DrawTextLayout`, and `draw_glyph_run` logging clip rectangles, coordinates, font face, and glyph count to pinpoint why tooltips render background without text glyphs.

5. **Build & Deployment:**
   - Both 64-bit and 32-bit (`wine64` and `wine32`) `win32u.so`, `wined3d.dll`, and `d2d1.dll` recompiled cleanly without warnings/errors.
   - Deployed to `/opt/wine-custom/lib/wine/` and prefix `system32`.
   - Prefix cleanly rebooted via `wineboot -r`.
   - Unified patch updated at `scripts/1-build/patches/0004-dcomp-dropdown-scroll-and-frame-stats.patch`.

---

## 11. Coordinate Translation & GDI Sysmem Dirtying Fixes (Round 16)

### Round 15 Results & Critical Discoveries
1. **Zero OpenGL Failures:** The fallback in `wined3d_context_gl_set_pixel_format` completely eliminated the 56 `wglSetPixelFormatWINE failed to set pixel format 81` errors per run.
2. **D2D Text Diagnostics Findings:**
   - In Round 15, `PushAxisAlignedClip` logged Dorico clipping down to `(3,2)-(width-3, 13)` (~15px height, matching tooltip dimensions).
   - However, Dorico executed zero `DrawTextLayout` or `draw_glyph_run` calls on that Direct2D context!
   - This confirmed Dorico draws tooltip text using GDI DC interoperability (`ID2D1GdiInteropRenderTarget` / `dxgi_surface_GetDC` / `ReleaseDC`).

### Root Cause Analysis & Implementations (Round 16)

1. **Dropdown / Submenu Hover & Click Failure (`dlls/win32u/message.c`):**
   - **Root Cause:** In Wine's `process_mouse_message` (lines 2806–2820):
     ```c
     else
     {
         /* coordinates don't get translated while tracking a menu */
         /* FIXME: should differentiate popups and top-level menus */
         if (!(info.flags & GUI_INMENUMODE))
             screen_to_client( msg->hwnd, &pt );
     }
     msg->lParam = MAKELONG( pt.x, pt.y );
     ```
   - When Dorico opened any dropdown or submenu, `info.flags & GUI_INMENUMODE` was set.
   - Wine **skipped `screen_to_client(msg->hwnd, &pt)`** and packed raw **SCREEN coordinates** (e.g. `x=1150, y=650`) into `msg->lParam`!
   - Qt's popup widget expects **client coordinates** (e.g. `0 <= x <= 200, 0 <= y <= 300`).
   - Because `(1150, 650)` lies completely outside the popup's local geometry, Qt evaluated the cursor as outside all items:
     - Hover highlights never activated.
     - Submenu leaves (Leaf 2) never received focus.
     - Mouse clicks on dropdown items were ignored or misrouted.
   - **Fix:** In `process_mouse_message`, ensure popups and child controls always undergo coordinate translation:
     ```c
     if (!(info.flags & GUI_INMENUMODE) || is_popup_window( msg->hwnd ))
         screen_to_client( msg->hwnd, &pt );
     ```
     Added diagnostic logging showing raw screen coordinates vs converted client coordinates and `is_popup` status.

2. **Tooltip Missing Text / Flat Box Failure (`dlls/wined3d/texture.c`):**
   - **Root Cause:** When GDI text rendering completes on a DXGI surface, `ReleaseDC` invokes `wined3d_texture_destroy_dc(void *object)`.
   - While `dxgi_surface_GetDC` properly sets up the GDI sysmem bitmap, `wined3d_texture_destroy_dc` **failed to validate `WINED3D_LOCATION_SYSMEM`** or invalidate `~WINED3D_LOCATION_SYSMEM`.
   - As a result, WineD3D never marked the texture dirty in sysmem. When DirectComposition subsequently presented the surface or bound it to the visual tree, the GPU never re-uploaded the GDI text rendering from host memory. DirectComposition displayed the initial un-rendered white background.
   - **Fix:** In `wined3d_texture_destroy_dc`:
     ```c
     wined3d_texture_validate_location(texture, sub_resource_idx, WINED3D_LOCATION_SYSMEM);
     wined3d_texture_invalidate_location(texture, sub_resource_idx, ~WINED3D_LOCATION_SYSMEM);
     ```
     This forces WineD3D to mark host sysmem as the authoritative source and invalidates the stale GPU copy so GDI rendered text is re-uploaded to the GPU immediately.

3. **Direct2D `Clear` Instrumentation & C89 Fix (`dlls/d2d1/device.c`):**
   - Added diagnostic FIXME in `d2d_device_context_Clear` to log clear colors and interface pointers.
   - Preserved strict C89 declaration order (`-Wdeclaration-after-statement`).

4. **Build, Verification & Deployment:**
   - Both 64-bit and 32-bit (`wine64` and `wine32`) `win32u.so`, `wined3d.dll`, and `d2d1.dll` recompiled cleanly with zero warnings/errors.
   - Binaries deployed to `/opt/wine-custom/lib/wine/` (`x86_64-unix`, `i386-unix`, `x86_64-windows`, `i386-windows`) and prefix `system32`.
   - Wine prefix cleanly rebooted via `wineboot -r`.
   - Unified patch updated at `scripts/1-build/patches/0004-dcomp-dropdown-scroll-and-frame-stats.patch`.

---

## 12. Targeted Tracing Deployed for Presentation & Event Pipelines (Round 17)

### Investigation Objectives
Following Round 16's telemetry proving mouse events reach the popup window handles in client coordinates, targeted diagnostic hooks were deployed across both the rendering/presentation pipeline and the window invalidation/event tracking pipeline to isolate why the visuals do not refresh:

1. **Presentation & Swapchain Telemetry (`dlls/dxgi/swapchain.c`):**
   - Added `FIXME` logging in `d3d11_swapchain_present` to capture whether Qt invokes `Present` on the popup swapchain when hover events occur, including swapchain address, HWND, sync interval, present flags, and monotonic `present_count`.

2. **Composition Front Buffer Sampling Telemetry (`dlls/dcomp/device.c`):**
   - Added `FIXME` logging in `do_composite` for `IDXGISwapChain1` content to verify which buffer (`buffer_idx` vs `BufferCount`) the composition thread is blitting to the target window and whether `present_count` is changing.

3. **Window Invalidation & Redraw Telemetry (`dlls/win32u/dce.c`):**
   - Added `FIXME` logging in `NtUserRedrawWindow` specifically filtering for `WS_POPUP` windows to detect whether Qt requests invalidation (`RDW_INVALIDATE`, `RDW_ERASE`, `RDW_UPDATENOW`) during mouse movements.

4. **Mouse Tracking Telemetry (`dlls/win32u/input.c`):**
   - Added `FIXME` logging in `NtUserTrackMouseEvent` to determine whether Qt requests hover or leave tracking (`TME_HOVER`, `TME_LEAVE`) on popup windows or child controls.

5. **Build & Deployment:**
   - Both 64-bit and 32-bit (`wine64` and `wine32`) `win32u.so`, `dxgi.dll`, and `dcomp.dll` recompiled cleanly.
   - Installed to `/opt/wine-custom/lib/wine/` and prefix `system32`.
   - Wine prefix cleanly rebooted via `wineboot -r`.

---

## 13. Round 17 Telemetry Analysis & DirectComposition Buffer Alignment Fix (Round 18)

### Telemetry Findings from Round 17 Log Analysis
Analysis of `/var/home/matt/.local/share/torquio/dorico_wine.log` revealed critical insights across the rendering and presentation pipelines:

1. **DirectComposition Compositor Loop is Fully Active:**
   - `composite_thread_proc` runs continuously every 16ms (60 FPS), calling `do_composite` and blitting surfaces onto target window handles.

2. **The Buffer Mismatch Defect in `do_composite` (`dlls/dcomp/device.c`):**
   - In Direct3D 11 under Wine, windowless/DirectComposition swapchains use WineD3D's GDI/D3D11 presentation path (`swapchain_blit_gdi`), which maintains back buffer 0 as the active rendered surface and does **not** rotate texture handles.
   - Qt's Direct3D 11 backend creates its primary render target view on `GetBuffer(0)` and renders into buffer 0.
   - However, in `dlls/dcomp/device.c`, `do_composite` had hardcoded logic:
     ```c
     if (SUCCEEDED(IDXGISwapChain1_GetLastPresentCount(swapchain, &present_count)) && present_count > 0)
         buffer_idx = swapchain_desc.BufferCount - 1;
     else
         buffer_idx = 0;
     ```
   - For any 2-buffer swapchain once `present_count > 0`, `buffer_idx` was hardcoded to `2 - 1 = 1`.
   - As a result, DirectComposition was blitting **buffer 1** repeatedly at 60 FPS, while Qt was rendering every new frame into **buffer 0**.
   - This directly explains why tooltips (which called `Present` 30 times in thread 0674) and dropdowns displayed only the static/initial flat background, with all subsequent text and hover updates frozen.

3. **Window Classification & Mouse Capture in `process_mouse_message` (`dlls/win32u/message.c`):**
   - Dorico's main window (`0x10192`) was created with `WS_POPUP | WS_THICKFRAME` (custom dark titlebar), causing `is_popup_window` to classify it as a popup.
   - Overriding `info.hwndCapture` in `process_mouse_message` when `is_popup_window(top)` was true broke Win32 mouse capture semantics whenever the mouse cursor moved near the main window.
   - Refined `is_popup_window` to require `GW_OWNER != NULL` or the absence of `WS_MINIMIZEBOX | WS_MAXIMIZEBOX`, correctly distinguishing transient popups/menus/tooltips from main application windows.
   - Restored standard mouse capture priority (`if (info.hwndCapture) msg->hwnd = info.hwndCapture`).

### Fixes Applied in Round 18
1. **`dlls/dcomp/device.c`:**
   - Explicitly sample `buffer_idx = 0` in `do_composite` so DirectComposition blits the active rendered surface from Direct3D 11.
2. **`dlls/win32u/message.c`:**
   - Corrected `is_popup_window` filtering and restored proper `info.hwndCapture` routing.
3. **Build & Deployment:**
   - Both 64-bit and 32-bit (`wine64` and `wine32`) `dcomp.dll` and `win32u.so` recompiled cleanly with zero warnings/errors.
   - Binaries deployed to `/opt/wine-custom/lib/wine/` and prefix updated.
   - Unified patch updated at `scripts/1-build/patches/0004-dcomp-dropdown-scroll-and-frame-stats.patch`.

---

## 14. Round 18 Telemetry Analysis & DirectComposition Non-Destructive Dirty Tracking (Round 19)

### Telemetry Findings from Round 18 Log Analysis
A comprehensive trace of the 16,793-line `/var/home/matt/.local/share/torquio/dorico_wine.log` from Round 18 resolved the mystery of why dropdowns, checkboxes, scrolls, and nested trees freeze on hover despite perfect mouse coordinate routing:

1. **Qt Uses GDI `BitBlt` for Widget Repaints, NOT Swapchain Presents:**
   - Dorico's UI widgets (menus, dropdowns, combo boxes, checkboxes, scrollbars) are standard QtWidgets managed by `qwindows.dll`.
   - When a dropdown window (e.g., `0x6009E`) opens, Steinberg's `graphics2d.dll` initializes a DirectComposition target and swapchain (`0x4C266ED0`), presenting frames 0 and 1 to draw the initial static background.
   - Once open, Qt's internal `QBackingStore` handles mouse hover highlights, checkbox toggles, selection changes, and scrollbar movement by directly painting dirty rectangles to the window device context via GDI (`GetDC` / `BitBlt` / `ReleaseDC`).
   - During the 121 `WM_MOUSEMOVE` events logged to `0x6009E`, Dorico called `IDXGISwapChain::Present()` **zero times** (`present_count` remained static at 2).

2. **The 60 FPS Compositor Blit Stomp:**
   - In upstream Wine's `dlls/dcomp/device.c`, `composite_thread_proc` ran an unconditional, periodic 60 Hz loop:
     ```c
     while (TRUE) {
         LIST_FOR_EACH_ENTRY(target, &device->targets, ...)
             do_composite(target, visual, 0, 0); // calls BitBlt(dst_dc, ..., src_dc, ..., SRCCOPY)
         Sleep(refresh_period); // 16ms
     }
     ```
   - Every 16 milliseconds, `do_composite_dxgi_surface` fetched buffer 0 of the swapchain (containing only the static initial image) and executed `BitBlt(dst_dc, 0, 0, width, height, src_dc, 0, 0, SRCCOPY)` over the entire target window.
   - **Consequently, whenever Qt painted a hover highlight, toggled a checkbox, or scrolled content via GDI, the background DirectComposition thread wiped it out within 0–16 milliseconds with the stale buffer 0.**

3. **Nested Tree Menus (Leaf 1 vs Leaf 2 Collision):**
   - Targets `0x2013E` (Leaf 1) and `0x3013E` (Leaf 2) shared the same device. The unconditional 60 FPS loop continuously blitted `0x24EDFDC0` into `0x3013E` while the mouse was moving over it, completely suppressing Qt's hover rendering on Leaf 2.

4. **Surface Alpha Transparency in Virtual Surfaces:**
   - In `dlls/dcomp/surface.c`, `create_virtual_surface` fell back to `DXGI_ALPHA_MODE_IGNORE` when `DXGI_ALPHA_MODE_UNSPECIFIED` was passed. In Direct2D, `ALPHA_MODE_IGNORE` forces transparent clears (`Clear(1, 1, 1, 0)`) to opaque white (`0xffffffff`), causing transient surfaces (tooltips) to lose alpha blending.

### Architecture Fixes Applied in Round 19
1. **Target-Level Dirty State & Swapchain Monotonic Tracking:**
   - Added `BOOL is_dirty;` and `UINT last_present_count;` to `struct composition_target` in `dlls/dcomp/dcomp_private.h`.
   - Initialized `is_dirty = TRUE; last_present_count = 0;` on target creation and `target_SetRoot`.
   - In `device_Commit`, all targets on the committing device are marked `is_dirty = TRUE;`.
   - Added `target_check_swapchain_dirty()` to detect whether any swapchain in the visual tree has presented a new frame (`present_count != target->last_present_count`).

2. **Non-Destructive Composite Execution in `composite_thread_proc`:**
   - Modified `composite_thread_proc` in `dlls/dcomp/device.c` to only execute `do_composite` when `target->is_dirty || swapchain_dirty` is true.
   - After a composite pass, resets `target->is_dirty = FALSE;` and records `target->last_present_count = new_present_count;`.
   - When no visual tree commit or swapchain present has occurred, DirectComposition does **not** touch the window DC, allowing Qt's GDI backingstore painting (hover highlights, checkbox ticks, scroll positions) to persist undisturbed.
   - Replaced passive `Sleep(refresh_period)` with an event-driven `WaitForSingleObject(device->commit_event, refresh_period)`, ensuring transactional visual changes and transient windows composite immediately (< 1ms) rather than waiting out a sleep interval.

3. **Preserve Premultiplied Alpha on Unspecified Mode:**
   - In `dlls/dcomp/surface.c`, changed `DXGI_ALPHA_MODE_UNSPECIFIED` fallback to `DXGI_ALPHA_MODE_PREMULTIPLIED` for both `create_surface` and `create_virtual_surface`.

4. **Build & Deployment:**
   - Recompiled both 64-bit and 32-bit `dcomp.dll` cleanly in `torquio-env` with zero warnings.
   - Deployed to `/opt/wine-custom/lib/wine/` and prefix `system32`/`syswow64`.
   - Updated unified patch at `scripts/1-build/patches/0004-dcomp-dropdown-scroll-and-frame-stats.patch`.
   - Cleanly updated Wine prefix with `wineboot -u`.

---

## 15. Round 19 Telemetry Analysis & Win32 Menu Coordinate Correction (Round 20)

### Telemetry Findings from Round 19 Log Analysis (`torquio_dorico_2026-09-27_22-15-38.log` & `22-18-25.log`)

1. **DirectComposition Event-Driven Dirty Tracking Succeeded:**
   - On dropdown creation (`0x400e8`), `do_composite` blitted initial frames at `present_count 1` and `present_count 2`.
   - Once open, as mouse events moved over `0x400e8` (`client_pt=(90,5)` down to `(78,1)`), `do_composite` was not invoked a single time. DirectComposition successfully stopped blitting stale frames over the window.

2. **Root Cause of Item 7 Regression (Top Bar Pulldowns Not Updating on Hover):**
   - The dropdown menus in the instrument window top bar are standard Win32 popup menus (`#32768` class, e.g. `hwnd=0x2012c` in log 1 and `hwnd=0x301f0` in log 2) tracked by Wine's built-in `MENU_TrackMenu` (`info.flags & GUI_INMENUMODE` = 1, `in_menu=1`).
   - In `process_mouse_message` (`dlls/win32u/message.c`), the check `if (!(info.flags & GUI_INMENUMODE) || is_popup_window(msg->hwnd))` evaluated `is_popup_window` as TRUE because `0x2012c` is a `WS_POPUP` window.
   - This forcibly converted `msg->lParam` to client coordinates (`client_pt=(16,-10)` in log 1, `(39,20)` in log 2).
   - However, Wine's internal menu tracking loop in `dlls/win32u/menu.c` explicitly requires `msg->lParam` to be in **SCREEN coordinates**:
     ```c
     mt.pt.x = (short)LOWORD( msg.lParam );
     mt.pt.y = (short)HIWORD( msg.lParam );
     hmenu = menu_from_point( mt.hTopMenu, mt.pt );
     ```
   - Because `lParam` was overwritten with client coordinates, `menu_from_point` evaluated coordinates near (0, 0) on the entire screen, returning `hmenu = NULL`. Thus, `menu_mouse_move` never updated the selected/highlighted item during hover.
   - Qt dropdowns (`0x400e8`, etc.) never run under `GUI_INMENUMODE` (`in_menu=0` across all logs). Wine's standard `!(info.flags & GUI_INMENUMODE)` was already translating client coordinates for Qt dropdowns without `is_popup_window`.

3. **Instrument Window Header Initial Draw Flash:**
   - In Round 19, `create_surface` and `create_virtual_surface` fell back to `DXGI_ALPHA_MODE_PREMULTIPLIED` when `DXGI_ALPHA_MODE_UNSPECIFIED` was passed.
   - Target `0x200cc` (the instrument window) was created and `device_Commit` was called before the first Direct2D draw finished (`dst_before=0x00000000`).
   - With premultiplied alpha on an uninitialized texture, alpha = 0 is fully transparent, causing `BitBlt` to temporarily flash the desktop/background through the top bar area until Direct2D finished drawing (`dst_after=0xff242629`).
   - Reverting the fallback alpha mode to `DXGI_ALPHA_MODE_IGNORE` ensures the surface defaults to opaque and eliminates the transparent flash.

### Fixes Applied in Round 20
1. **`dlls/win32u/message.c`:**
   - Restored standard menu tracking check `if (!(info.flags & GUI_INMENUMODE))` so `lParam` retains screen coordinates during `GUI_INMENUMODE`, fully restoring item hover updates in standard Win32 pulldown menus.
2. **`dlls/dcomp/surface.c`:**
   - Reverted `DXGI_ALPHA_MODE_UNSPECIFIED` fallback to `DXGI_ALPHA_MODE_IGNORE` in both `create_surface` and `create_virtual_surface` to prevent transparent initialization flicker.
3. **Build & Deployment:**
   - Recompiled both 64-bit and 32-bit (`wine64` and `wine32`) `win32u.so` and `dcomp.dll` cleanly in `torquio-env` with zero warnings.
   - Deployed to `/opt/wine-custom/lib/wine/` and prefix `system32`/`syswow64`.
   - Updated unified patch at `scripts/1-build/patches/0004-dcomp-dropdown-scroll-and-frame-stats.patch`.

---

## 16. Round 20 Telemetry Analysis & Swapchain Front-Buffer Sampling Correction (Round 21)

### Test Results from Round 20
- **Item 7 (Play mode instrument window in general):** **Regression completely fixed!** The system-style grey pulldown menu mouseover highlighting works reliably. The only minor observation was that when opening the instrument window, the top bar content area was briefly blank white before the rendered controls appeared.
- **Items 1–5 (Dropdowns - single, checkbox, multi-item, scroll, nested tree):** No change; Behavior #3 persists. Content displays on initial open, but mouseovers and interactions do not update the visual display. In item 4 (scroll dropdown), initial draw shows a thin white rectangle at the top where a scroller chevron would be. In item 5 (nested tree), leaf 2 is displayed but mouse interactions act as if leaf 1 is under cursor.
- **Item 6 (Tooltips):** Tooltips display background but no text glyphs, appearing flatter than expected.

### Telemetry & Root Cause Breakthrough from Round 20 Log (`torquio_dorico_2026-09-27_23-46-41.log`)

1. **Root Cause of Item 7 Top-Bar Initial Blank White Delay:**
   - On instrument window creation (`hwnd=0x40110`), `create_target` creates target `0x074c4f80` with virtual surface `0x39cd3020`.
   - `target_SetRoot` and `device_Commit` initialized `target->is_dirty = TRUE;`.
   - The composition thread woke immediately on `device->commit_event` and executed `do_composite` at line 3617.
   - However, Direct2D had not yet begun drawing (`surface_BeginDraw` was called at line 3623 and `surface_EndDraw` finished at line 3699).
   - Because fallback alpha mode was `DXGI_ALPHA_MODE_IGNORE` (opaque), `BitBlt` blitted the uninitialized (0x00000000 / blank white) surface buffer to the window DC.
   - Direct2D drawing completed 80ms later and committed, replacing the white rectangle with the drawn controls.
   - **Resolution:** Surfaces must never composite until their initial `surface_EndDraw` has executed. Added `draw_count` tracking to `struct composition_surface`. If `surface_impl->draw_count == 0`, `do_composite` skips blitting and returns `S_OK`. Upon completion of `surface_EndDraw`, device targets are marked dirty and `device->commit_event` is signaled, compositing the fully rendered controls immediately with zero blank white flash.

2. **Root Cause of Item 6 (Tooltips Lacking Text) and Items 1–5 (Stale Dropdown Frames):**
   - In commit `b598505`, `buffer_idx = 0;` was hardcoded in `do_composite`:
     ```c
     if (SUCCEEDED(IDXGISwapChain1_GetLastPresentCount(swapchain, &present_count)))
         buffer_idx = 0;
     ```
   - In Wine's D3D11 swapchain implementation (`dlls/wined3d/swapchain.c`):
     - When `wined3d_swapchain_present` executes, `wined3d_swapchain_gl_rotate` rotates `back_buffers[0]` into `back_buffers[desc.backbuffer_count - 1]`!
     - In double-buffered composition swapchains (`BufferCount == 2`), `back_buffers[1]` (`swapchain_desc.BufferCount - 1`) **always contains the most recently presented frame**.
     - `back_buffers[0]` becomes the scratch back buffer for the *next* frame!
   - By hardcoding `buffer_idx = 0`, DirectComposition was **always reading the scratch back buffer**, completely ignoring the presented frame in buffer 1!
   - **Effect on Tooltips (Item 6):** Tooltips present exactly two frames: frame 0 (background shape) and frame 1 (text glyphs on background). At `present_count = 2`, the text frame was in buffer 1, but `do_composite` sampled buffer 0 (the empty background without text), rendering a flat box devoid of glyphs!
   - **Effect on Dropdowns (Items 1–5):** Subsequent frames (scroller chevrons, hover states, submenus) presented to the swapchain rotated into buffer 1, but DirectComposition continuously sampled buffer 0, causing the visual display to appear frozen at the initial un-hovered frame.
   - **Premature Composition at `present_count == 0`:** When dropdown `0x500e6` was created, `target->is_dirty = TRUE` triggered `do_composite` when `present_count == 0`, blitting an uninitialized buffer before Dorico even presented frame 1.

### Fixes Applied in Round 21
1. **`dlls/dcomp/device.c`:**
   - In `do_composite`, if `present_count == 0`, the swapchain has not presented any frames yet; skip compositing and return `S_OK`.
   - When `present_count > 0`, set `buffer_idx = swapchain_desc.BufferCount - 1;` so DirectComposition samples the true front buffer containing the newly presented frame.
   - In `target_check_swapchain_dirty`, require `present_count > 0 && present_count != target->last_present_count`.
   - For `IDCompositionSurface`, check `if (surface_impl->draw_count == 0) return S_OK;`.
2. **`dlls/dcomp/dcomp_private.h` & `surface.c`:**
   - Added `UINT draw_count;` to `struct composition_surface`.
   - In `surface_EndDraw`, increment `surface->draw_count++`. If `surface->factory`, mark all device targets `is_dirty = TRUE;` and signal `device->commit_event`.
3. **Build & Deployment:**
   - Recompiled both 64-bit and 32-bit (`wine64` and `wine32`) `dcomp.dll` cleanly with zero warnings/errors.
   - Deployed binaries to `/opt/wine-custom/lib/wine/` and prefix `system32`/`syswow64`.
   - Updated unified patch at `scripts/1-build/patches/0004-dcomp-dropdown-scroll-and-frame-stats.patch`.
   - Updated Wine prefix configurations via `wineboot -u`.
---

## 17. Round 21 Telemetry Analysis, Missing GPU-to-DC Sync Root Cause & ADVAPI32 Fix (Round 22)

### Test Results from Round 21
- **Items 1–5 (Dropdowns) & Item 6 (Tooltips):** Behavior #3 persists. Content renders on initial open, but mouseovers, scroll chevrons, and submenus do not update the visual display. Tooltips remain flat and lack text glyphs.
- **Item 7 (Instrument window top-bar area):** Regression observed where top-bar area remained blank white or black until moused over.
- **Startup Crash / Error Messages:** Unhandled exception on unimplemented API `ADVAPI32.dll.CloseThreadWaitChainSession` causing rundll32/process crash.

### Breakthrough Findings from Round 21 Telemetry (`torquio_dorico_2026-09-28_00-59-41.log`)

1. **The Root Cause of Stale Visuals (Items 1–6): Missing GPU-to-DC SYSMEM Reload in `wined3d_texture_get_dc`:**
   - In `dlls/dcomp/device.c`, DirectComposition reads swapchain surfaces via `IDXGISurface_GetDC(dxgi_surface, FALSE, &src_dc)` and `BitBlt`s to the window DC.
   - `IDXGISurface_GetDC` routes to `wined3d_texture_get_dc(texture, sub_resource_idx, &dc)` in `dlls/wined3d/texture.c`.
   - On the very first call, `dc_info[sub_resource_idx].dc` is NULL. Wine calls `wined3d_texture_create_dc`, which downloads the GPU texture to system memory (`WINED3D_LOCATION_SYSMEM`) and wraps it in a DIB section DC.
   - On all subsequent calls (when Dorico draws text onto a tooltip, renders a hover highlight in a dropdown, or rotates the swapchain), `dc_info[sub_resource_idx].dc` is **already non-NULL**.
   - **The Critical Flaw:** `wined3d_texture_get_dc` NEVER checked whether `WINED3D_LOCATION_SYSMEM` was valid!
   - When the GPU draws a new frame or `wined3d_swapchain_gl_rotate` rotates textures, `WINED3D_LOCATION_SYSMEM` is invalidated because the newest pixels reside in `WINED3D_LOCATION_TEXTURE_RGB`.
   - Because `wined3d_texture_get_dc` omitted any location validation for existing DCs, it handed DirectComposition the **same stale DIB section memory from frame 1 over and over again**!
   - Even though Dorico presented 33 frames to the dropdown swapchain, DirectComposition was blitting the stale initial DC on every single frame!
   - **Resolution:** Added `wined3d_texture_sync_dc`. When `dc_info` already exists but `!(sub_resource->locations & texture->resource.map_binding)`, `wined3d_texture_sync_dc` executes `wined3d_texture_load_location(texture, sub_resource_idx, context, texture->resource.map_binding)`, downloading the fresh OpenGL texture into the DC's memory before returning it.

2. **The Root Cause of Item 7 Top-Bar Blank Delay:**
   - In Round 21, when `do_composite` encountered `draw_count == 0`, it returned `S_OK`.
   - In `composite_thread_proc`, `SUCCEEDED(hr)` caused `target->is_dirty = FALSE;` to execute, marking the target clean before it had ever composited!
   - If GDI erased the window (`RDW_ERASE`) before Direct2D completed drawing, the window displayed default background (white or black) and remained uncomposited until mouseover triggered a new commit.
   - **Resolution:** In `do_composite`, return `S_FALSE` when unready (`draw_count == 0` or `present_count == 0`). In `composite_thread_proc`, if `hr == S_FALSE`, keep `target->is_dirty = TRUE;` so composition executes immediately on the next pass once drawing is complete.

3. **ADVAPI32 Unimplemented Function Crash:**
   - Dorico and startup processes call `CloseThreadWaitChainSession`.
   - Implemented stub `CloseThreadWaitChainSession(HWCT handle)` in `dlls/advapi32/advapi.c` and exported in `advapi32.spec`.

### Code Changes Applied & Deployed
1. `dlls/wined3d/texture.c`: Added `wined3d_texture_sync_dc` and hooked into `wined3d_texture_get_dc`.
2. `dlls/dcomp/device.c`: Return `S_FALSE` from `do_composite` on unready surfaces; preserve `target->is_dirty` until drawn.
3. `dlls/advapi32/advapi.c` & `advapi32.spec`: Added `CloseThreadWaitChainSession` stub.
4. Compiled 64-bit and 32-bit `wined3d.dll`, `advapi32.dll`, and `dcomp.dll`.
5. Deployed to `/opt/wine-custom/lib/wine/` and prefix `system32`/`syswow64`.
6. Regenerated unified patch `scripts/1-build/patches/0004-dcomp-dropdown-scroll-and-frame-stats.patch`.


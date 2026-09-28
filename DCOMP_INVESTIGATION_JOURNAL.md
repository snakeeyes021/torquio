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
   - Unified patch updated at `scripts/1-build/patches/0004-dcomp-dropdown-scroll-and-frame-stats.patch`.

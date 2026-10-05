"""
overlay/window.py — Fullscreen transparent always-on-top overlay window.

Responsibilities
────────────────
• Creates a borderless, fullscreen Tkinter window that covers the entire display.
• The window is normally CLICK-THROUGH (WS_EX_TRANSPARENT) so all mouse/keyboard
  events pass through to whatever app is underneath.
• When the lasso controller arms itself, the click-through flag is removed so
  the overlay can intercept the left-drag used to draw the lasso.
• Draws a thin dark-yellow border on all four screen edges — the only persistent
  visual element — so the user always knows the app is running.
• Hosts the canvas on which lasso polygons are drawn.
• Drives the tooltip's position update via a Tk after-poll on mouse position.

Win32 click-through mechanism
──────────────────────────────
We use SetWindowLongW to set/clear WS_EX_TRANSPARENT.  This is the most
reliable and flicker-free method on Windows 10/11.  The layered window flag
(WS_EX_LAYERED) must be present at the same time; we use -transparentcolor
trick on the canvas background so the Tkinter alpha pipeline doesn't fight us.
"""

from __future__ import annotations

import ctypes
import tkinter as tk
from typing import Callable, Optional

from config import (
    APP_NAME,
    BORDER_COLOR,
    BORDER_WIDTH,
    PANEL_COLOR,
    PANEL_LINE_WIDTH,
    PANEL_MIN_SIZE,
)
from storage.keystore import load_panel_mode, load_panel_bounds, save_panel_bounds

# ── Win32 constants ────────────────────────────────────────────────────────────
GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST     = 0x00000008
WS_EX_NOACTIVATE  = 0x08000000

SWP_NOMOVE   = 0x0002
SWP_NOSIZE   = 0x0001
SWP_NOACTIVATE = 0x0010
HWND_TOPMOST = ctypes.c_void_p(-1)

user32 = ctypes.windll.user32

# The "magic" transparent colour used as the canvas background.
# Pixels of this exact colour become fully transparent (click-through even
# when WS_EX_TRANSPARENT is NOT set, because they're invisible).
_TRANSPARENT_KEY = "#010101"


class OverlayWindow:
    """
    The main overlay window.

    Parameters
    ----------
    on_ready : called once the window is up and the event loop is running.
               Use this to wire the LassoController and Tooltip after Tk init.
    """

    def __init__(self, on_ready: Optional[Callable[[], None]] = None, master=None) -> None:
        self._master = master
        self._on_ready = on_ready
        self._root: Optional[tk.Tk] = None
        self._canvas: Optional[tk.Canvas] = None
        self._hwnd: int = 0
        self._mouse_x: int = 0
        self._mouse_y: int = 0
        self._on_mouse_move_callbacks: list[Callable[[int, int], None]] = []
        
        self._panel_active: bool = False
        self._panel_bounds: list[int] = [100, 100, 600, 800] # default x, y, w, h
        self._panel_rect_id = None

    # ── Public API ─────────────────────────────────────────────────────────────

    @property
    def root(self) -> tk.Tk:
        assert self._root is not None
        return self._root

    @property
    def canvas(self) -> tk.Canvas:
        assert self._canvas is not None
        return self._canvas

    @property
    def mouse_x(self) -> int:
        return self._mouse_x

    @property
    def mouse_y(self) -> int:
        return self._mouse_y

    def register_mouse_move(self, cb: Callable[[int, int], None]) -> None:
        """Register a callback invoked whenever the mouse moves (polled via after)."""
        self._on_mouse_move_callbacks.append(cb)
        
    def get_panel_bounds(self) -> tuple[int, int, int, int] | None:
        """Return the (x, y, w, h) of the panel if active, else None."""
        if self._panel_active:
            return tuple(self._panel_bounds)
        return None
        
    def set_panel_bounds(self, x: int, y: int, w: int, h: int) -> None:
        """Update the panel bounds and redraw (no disk I/O for smooth dragging)."""
        w = max(PANEL_MIN_SIZE, w)
        h = max(PANEL_MIN_SIZE, h)
        self._panel_bounds = [x, y, w, h]
        self._redraw_panel()
        
    def save_current_panel_bounds(self) -> None:
        """Save the current panel bounds to keystore (call on drag release)."""
        if self._panel_active:
            save_panel_bounds(tuple(self._panel_bounds))
            
    def update_panel_mode(self) -> None:
        """Read from keystore and update the panel box visibility and position."""
        self._panel_active = load_panel_mode()
        saved = load_panel_bounds()
        if saved:
            self._panel_bounds = list(saved)
        else:
            sw = self._root.winfo_screenwidth()
            sh = self._root.winfo_screenheight()
            # Default center of screen
            w, h = 600, 800
            self._panel_bounds = [(sw - w) // 2, (sh - h) // 2, w, h]
            save_panel_bounds(tuple(self._panel_bounds))
            
        self._redraw_panel()

    def set_sleep_mode(self, is_sleep: bool) -> None:
        """Update border color based on sleep mode."""
        if not self._canvas:
            return
        color = "#555555" if is_sleep else BORDER_COLOR
        self._canvas.itemconfig("border", fill=color)
        
        if is_sleep and self._panel_rect_id:
            self._canvas.itemconfig("panel_box", state="hidden")
        elif not is_sleep and self._panel_rect_id:
            self._canvas.itemconfig("panel_box", state="normal")

    def set_click_through(self, enabled: bool) -> None:
        """
        Toggle click-through mode.
        True  → overlay is invisible to mouse (idle state).
        False → overlay captures mouse input (lasso-drawing state).
        """
        if not self._hwnd:
            return
        style = user32.GetWindowLongW(self._hwnd, GWL_EXSTYLE)
        if enabled:
            style |= WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
        user32.SetWindowLongW(self._hwnd, GWL_EXSTYLE, style)
    def run(self) -> None:
        """Create the window and start the Tkinter event loop (blocks until quit)."""
        self._build()
        if self._on_ready:
            self._root.after(100, self._on_ready)  # type: ignore[union-attr]
        if not self._master:
            self._root.mainloop()  # type: ignore[union-attr]

    def quit(self) -> None:
        """Destroy the Tk window and stop the event loop."""
        if self._root:
            self._root.quit()
            self._root.destroy()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        if self._master:
            root = tk.Toplevel(self._master)
        else:
            root = tk.Tk()
        root.title(APP_NAME)

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()

        # Fullscreen borderless
        root.overrideredirect(True)
        root.geometry(f"{sw}x{sh}+0+0")
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", _TRANSPARENT_KEY)
        root.configure(bg=_TRANSPARENT_KEY)
        root.lift()

        canvas = tk.Canvas(
            root,
            width=sw,
            height=sh,
            bg=_TRANSPARENT_KEY,
            highlightthickness=0,
            cursor="arrow",
        )
        canvas.pack(fill="both", expand=True)

        # Draw the four border lines
        bw = BORDER_WIDTH
        bc = BORDER_COLOR
        # Top
        canvas.create_rectangle(0, 0, sw, bw, fill=bc, outline="", tags="border")
        # Bottom
        canvas.create_rectangle(0, sh - bw, sw, sh, fill=bc, outline="", tags="border")
        # Left
        canvas.create_rectangle(0, bw, bw, sh - bw, fill=bc, outline="", tags="border")
        # Right
        canvas.create_rectangle(sw - bw, bw, sw, sh - bw, fill=bc, outline="", tags="border")

        self._root   = root
        self._canvas = canvas

        # Get Win32 handle and configure extended styles
        root.update()  # Ensure window is created before querying HWND
        hwnd = int(root.frame(), 16)
        self._hwnd = hwnd

        # Set initial style: layered + transparent (click-through) + no-activate
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE,
            style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
        )

        # Force always-on-top via SetWindowPos for reliability
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

        # Start mouse position polling (every 16ms ≈ 60fps)
        self._poll_mouse()
        
        # Initialize panel state
        self.update_panel_mode()

    def _redraw_panel(self) -> None:
        if not self._canvas:
            return
            
        if self._panel_rect_id:
            self._canvas.delete(self._panel_rect_id)
            self._panel_rect_id = None
            
        if self._panel_active:
            x, y, w, h = self._panel_bounds
            self._panel_rect_id = self._canvas.create_rectangle(
                x, y, x + w, y + h,
                outline=PANEL_COLOR,
                width=PANEL_LINE_WIDTH,
                tags="panel_box"
            )

    def _poll_mouse(self) -> None:
        """Poll Win32 cursor position and notify callbacks.  Runs on Tk thread."""
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))

        if pt.x != self._mouse_x or pt.y != self._mouse_y:
            self._mouse_x = pt.x
            self._mouse_y = pt.y
            for cb in self._on_mouse_move_callbacks:
                cb(pt.x, pt.y)

        if self._root:
            self._root.after(16, self._poll_mouse)

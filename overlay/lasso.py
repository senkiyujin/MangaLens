"""
overlay/lasso.py

Tetikleme — SADECE CTRL:
  CTRL BASILI TUT  → çizim modu, fare hareketiyle otomatik lasso çizilir
  CTRL BIRAK       → çizim biter
                     • Yeterli hareket varsa → çeviri başlar
                     • Az hareket / tooltip varsa → tooltip kapanır / idle
"""

from __future__ import annotations

import math
import threading
import tkinter as tk
from enum import Enum, auto
from typing import Callable, List, Optional, Tuple

from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse

from config import (
    LASSO_DOT_RADIUS,
    LASSO_LINE_COLOR,
    LASSO_LINE_WIDTH,
    MIN_LASSO_DRAG_PX,
    PANEL_MIN_SIZE,
)


class LassoState(Enum):
    SLEEP       = auto()
    IDLE        = auto()
    DRAWING     = auto()
    TRANSLATING = auto()
    SHOWING     = auto()
    PANEL_DRAG = auto()
    PANEL_RESIZE_L = auto()
    PANEL_RESIZE_R = auto()
    PANEL_RESIZE_T = auto()
    PANEL_RESIZE_B = auto()
    PANEL_RESIZE_TL = auto()
    PANEL_RESIZE_TR = auto()
    PANEL_RESIZE_BL = auto()
    PANEL_RESIZE_BR = auto()

Point = Tuple[int, int]

_CTRL_KEYS = {
    pynput_keyboard.Key.ctrl,
    pynput_keyboard.Key.ctrl_l,
    pynput_keyboard.Key.ctrl_r,
}

_SHIFT_KEYS = {
    pynput_keyboard.Key.shift,
    pynput_keyboard.Key.shift_l,
    pynput_keyboard.Key.shift_r,
}


class LassoController:

    def __init__(
        self,
        overlay,
        on_lasso_done: Callable[[List[Point]], None],
        on_magic_wand: Callable[[Point], None],
        on_full_page: Callable[[], None],
        on_dismiss: Callable[[], None],
        on_set_clickthrough: Callable[[bool], None],
        on_sleep_toggle: Callable[[bool], None] = None,
    ) -> None:
        self._overlay       = overlay
        self._canvas        = overlay.canvas
        self._on_lasso_done = on_lasso_done
        self._on_magic_wand = on_magic_wand
        self._on_full_page   = on_full_page
        self._on_dismiss    = on_dismiss
        self._on_sleep_toggle = on_sleep_toggle

        self._state: LassoState   = LassoState.IDLE
        self._state_lock           = threading.Lock()
        self._points: List[Point]  = []
        self._canvas_ids: List[int] = []
        self._start_point: Optional[Point] = None

        self._ctrl_pressed: bool  = False
        self._shift_pressed: bool = False
        
        self._panel_drag_start: Optional[Point] = None
        self._panel_initial_bounds: Optional[Tuple[int, int, int, int]] = None

        self._mouse_listener: Optional[pynput_mouse.Listener] = None
        self._kbd_listener:   Optional[pynput_keyboard.Listener] = None
        self._start_listeners()

    # ── Public ───────────────────────────────────────────────────────────────

    def set_state_translating(self) -> None:
        with self._state_lock:
            self._state = LassoState.TRANSLATING
        self._clear_canvas()

    def set_state_showing(self) -> None:
        with self._state_lock:
            self._state = LassoState.SHOWING

    def set_state_idle(self) -> None:
        with self._state_lock:
            if self._state == LassoState.SLEEP:
                return
            self._state = LassoState.IDLE
        self._points = []
        self._clear_canvas()

    def force_sleep(self, is_sleep: bool) -> None:
        with self._state_lock:
            if is_sleep:
                self._state = LassoState.SLEEP
                self._points = []
                self._start_point = None
                self._clear_canvas()
            else:
                self._state = LassoState.IDLE

    def stop(self) -> None:
        if self._mouse_listener: self._mouse_listener.stop()
        if self._kbd_listener:   self._kbd_listener.stop()

    # ── Klavye ───────────────────────────────────────────────────────────────

    def _on_key_press(self, key) -> None:
        if key in _CTRL_KEYS:
            self._ctrl_pressed = True
        if key in _SHIFT_KEYS:
            self._shift_pressed = True

        # Toggle Sleep mode with Ctrl + Enter
        if key == pynput_keyboard.Key.enter and self._ctrl_pressed:
            with self._state_lock:
                if self._state == LassoState.SLEEP:
                    self._state = LassoState.IDLE
                    is_sleep = False
                else:
                    self._state = LassoState.SLEEP
                    self._points = []
                    self._start_point = None
                    self._clear_canvas()
                    is_sleep = True
            if self._on_sleep_toggle:
                self._canvas.after(0, lambda s=is_sleep: self._on_sleep_toggle(s))
            return

        with self._state_lock:
            state = self._state

        if state == LassoState.SLEEP:
            return

        # Ctrl + Shift birlikte basıldı → Tam Sayfa Çeviri
        if self._ctrl_pressed and self._shift_pressed:
            if state != LassoState.TRANSLATING:
                with self._state_lock:
                    self._state = LassoState.TRANSLATING
                self._clear_canvas()
                self._canvas.after(0, self._on_dismiss)
                self._canvas.after(50, self._on_full_page)
                return

        if key not in _CTRL_KEYS:
            return

        if state in (LassoState.IDLE, LassoState.SHOWING):
            self._canvas.after(0, self._on_dismiss)
            with self._state_lock:
                self._state = LassoState.DRAWING
            self._points = []
            self._start_point = None
            self._canvas.after(0, self._init_draw_from_cursor)

    def _on_key_release(self, key) -> None:
        if key in _CTRL_KEYS:
            self._ctrl_pressed = False
        if key in _SHIFT_KEYS:
            self._shift_pressed = False

        if key not in _CTRL_KEYS:
            return
        with self._state_lock:
            state = self._state
        if state == LassoState.DRAWING:
            self._canvas.after(0, self._finish_lasso)

    def _init_draw_from_cursor(self) -> None:
        """Tk thread'inde — mevcut fare konumunu başlangıç noktası yap."""
        import ctypes
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        x, y = pt.x, pt.y
        self._start_point = (x, y)
        self._points = [(x, y)]
        self._draw_start_dot(x, y)

    # ── Fare hareketi ve Tıklama ──────────────────────────────────────────────

    def _on_move(self, x: int, y: int) -> None:
        with self._state_lock:
            state = self._state
        if state == LassoState.SLEEP:
            return
        if state == LassoState.DRAWING:
            self._points.append((x, y))
            self._canvas.after(0, self._redraw_lasso)
        elif state in (
            LassoState.PANEL_DRAG, LassoState.PANEL_RESIZE_L, LassoState.PANEL_RESIZE_R,
            LassoState.PANEL_RESIZE_T, LassoState.PANEL_RESIZE_B, LassoState.PANEL_RESIZE_TL,
            LassoState.PANEL_RESIZE_TR, LassoState.PANEL_RESIZE_BL, LassoState.PANEL_RESIZE_BR
        ):
            dx = x - self._panel_drag_start[0]
            dy = y - self._panel_drag_start[1]
            px, py, pw, ph = self._panel_initial_bounds
            
            if state in (LassoState.PANEL_RESIZE_L, LassoState.PANEL_RESIZE_TL, LassoState.PANEL_RESIZE_BL):
                dx = min(dx, pw - PANEL_MIN_SIZE)
            if state in (LassoState.PANEL_RESIZE_T, LassoState.PANEL_RESIZE_TL, LassoState.PANEL_RESIZE_TR):
                dy = min(dy, ph - PANEL_MIN_SIZE)
                
            nx, ny, nw, nh = px, py, pw, ph
            
            if state == LassoState.PANEL_DRAG:
                nx, ny = px + dx, py + dy
            elif state == LassoState.PANEL_RESIZE_L:
                nx, nw = px + dx, pw - dx
            elif state == LassoState.PANEL_RESIZE_R:
                nw = pw + dx
            elif state == LassoState.PANEL_RESIZE_T:
                ny, nh = py + dy, ph - dy
            elif state == LassoState.PANEL_RESIZE_B:
                nh = ph + dy
            elif state == LassoState.PANEL_RESIZE_TL:
                nx, ny, nw, nh = px + dx, py + dy, pw - dx, ph - dy
            elif state == LassoState.PANEL_RESIZE_TR:
                ny, nw, nh = py + dy, pw + dx, ph - dy
            elif state == LassoState.PANEL_RESIZE_BL:
                nx, nw, nh = px + dx, pw - dx, ph + dy
            elif state == LassoState.PANEL_RESIZE_BR:
                nw, nh = pw + dx, ph + dy
                
            self._canvas.after(0, lambda nnx=nx, nny=ny, nnw=nw, nnh=nh: self._overlay.set_panel_bounds(nnx, nny, nnw, nnh))

    def _on_click(self, x: int, y: int, button, pressed: bool) -> None:
        with self._state_lock:
            state = self._state
        if state == LassoState.SLEEP:
            return

        if not pressed:
            with self._state_lock:
                if self._state in (
                    LassoState.PANEL_DRAG, LassoState.PANEL_RESIZE_L, LassoState.PANEL_RESIZE_R,
                    LassoState.PANEL_RESIZE_T, LassoState.PANEL_RESIZE_B, LassoState.PANEL_RESIZE_TL,
                    LassoState.PANEL_RESIZE_TR, LassoState.PANEL_RESIZE_BL, LassoState.PANEL_RESIZE_BR
                ):
                    self._state = LassoState.IDLE
                    self._canvas.after(0, self._overlay.save_current_panel_bounds)
            return
            
        with self._state_lock:
            state = self._state
            
        if button == pynput_mouse.Button.left and state == LassoState.IDLE:
            panel_bounds = self._overlay.get_panel_bounds()
            if panel_bounds:
                px, py, pw, ph = panel_bounds
                ET = 12 # Edge tolerance pixels
                
                is_l = abs(x - px) <= ET
                is_r = abs(x - (px + pw)) <= ET
                is_t = abs(y - py) <= ET
                is_b = abs(y - (py + ph)) <= ET
                is_inside = (px - ET <= x <= px + pw + ET) and (py - ET <= y <= py + ph + ET)
                
                if is_inside:
                    with self._state_lock:
                        if is_l and is_t: self._state = LassoState.PANEL_RESIZE_TL
                        elif is_r and is_t: self._state = LassoState.PANEL_RESIZE_TR
                        elif is_l and is_b: self._state = LassoState.PANEL_RESIZE_BL
                        elif is_r and is_b: self._state = LassoState.PANEL_RESIZE_BR
                        elif is_l: self._state = LassoState.PANEL_RESIZE_L
                        elif is_r: self._state = LassoState.PANEL_RESIZE_R
                        elif is_t: self._state = LassoState.PANEL_RESIZE_T
                        elif is_b: self._state = LassoState.PANEL_RESIZE_B
                        elif (px + ET < x < px + pw - ET) and (py + ET < y < py + ph - ET): 
                            self._state = LassoState.PANEL_DRAG
                        else:
                            pass
                            
                    if self._state != LassoState.IDLE:
                        self._panel_drag_start = (int(x), int(y))
                        self._panel_initial_bounds = (px, py, pw, ph)
                        return

        if button != pynput_mouse.Button.left:
            return

            
        # Eğer CTRL basılıyken sol tıklanırsa -> Sihirli Değnek
        if state == LassoState.DRAWING:
            with self._state_lock:
                self._state = LassoState.TRANSLATING
            self._clear_canvas()
            pt = (int(x), int(y))
            # Pynput thread'inden Tkinter GUI çağırmamak için canvas.after ile Tk thread'ine gönder
            self._canvas.after(0, lambda: self._on_magic_wand(pt))

    # ── Lasso bitirme ─────────────────────────────────────────────────────────

    def _finish_lasso(self) -> None:
        """Ctrl bırakılınca Tk thread'inde çağrılır."""
        with self._state_lock:
            state = self._state
            if state != LassoState.DRAWING:
                return

        pts = self._points
        sp  = self._start_point

        # Az hareket → tooltip kapat veya idle'a dön
        if not sp or len(pts) < 3:
            self._dismiss_or_idle()
            return

        # Çizilen alanın (bounding box) boyutuna bak
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        
        # Yeterli hareket yoksa (Tıklama) -> Sihirli Değnek
        if width < MIN_LASSO_DRAG_PX and height < MIN_LASSO_DRAG_PX:
            with self._state_lock:
                self._state = LassoState.TRANSLATING
            self._clear_canvas()
            self._on_magic_wand(sp)
            return

        # Yeterli hareket → çevir
        points_snapshot = list(pts)
        with self._state_lock:
            self._state = LassoState.TRANSLATING
        self._on_lasso_done(points_snapshot)

    def _dismiss_or_idle(self) -> None:
        """Az hareket: tooltip varsa kapat, yoksa idle'a dön."""
        with self._state_lock:
            prev = self._state
        if prev == LassoState.DRAWING:
            # Önceki durum ne olduğunu bilemiyoruz — tooltip kapatmayı dene
            pass
        self._on_dismiss()   # dismiss hem tooltip'i kapatır hem idle'a alır
        self.set_state_idle()

    # ── Canvas ────────────────────────────────────────────────────────────────

    def _draw_start_dot(self, x: int, y: int) -> None:
        r = LASSO_DOT_RADIUS
        cid = self._canvas.create_oval(
            x - r, y - r, x + r, y + r,
            fill=LASSO_LINE_COLOR, outline=LASSO_LINE_COLOR,
        )
        self._canvas_ids.append(cid)

    def _redraw_lasso(self) -> None:
        for cid in self._canvas_ids[1:]:
            self._canvas.delete(cid)
        self._canvas_ids = self._canvas_ids[:1]
        pts = self._points
        if len(pts) < 2:
            return
        flat = [c for pt in pts for c in pt] + [pts[0][0], pts[0][1]]
        cid = self._canvas.create_line(
            *flat, fill=LASSO_LINE_COLOR, width=LASSO_LINE_WIDTH, smooth=True,
        )
        self._canvas_ids.append(cid)

    def _clear_canvas(self) -> None:
        self._canvas.after(0, self.__clear_canvas_main)

    def __clear_canvas_main(self) -> None:
        for cid in self._canvas_ids:
            self._canvas.delete(cid)
        self._canvas_ids = []

    # ── Listeners ─────────────────────────────────────────────────────────────

    def _start_listeners(self) -> None:
        self._mouse_listener = pynput_mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
        )
        self._mouse_listener.start()

        self._kbd_listener = pynput_keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._kbd_listener.start()

#!/usr/bin/env python3
import ctypes
import ctypes.util
import subprocess
import re
import threading
import time
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import base64

# ── Optional Bluetooth support ────────────────────────────────────────────
try:
    import dbus

    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False

_SCALE = 4


def _make(draw_fn, size=24, color="#e2e4e9"):
    px = size * _SCALE
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_fn(d, px, color)
    img = img.resize((size, size), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


# ── Speaker / Volume ──────────────────────────────────────────────
def icon_speaker(size=24, color="#60a5fa"):
    def draw(d, s, c):
        d.polygon(
            [
                (s * 0.16, s * 0.38),
                (s * 0.16, s * 0.62),
                (s * 0.34, s * 0.62),
                (s * 0.48, s * 0.74),
                (s * 0.48, s * 0.26),
                (s * 0.34, s * 0.38),
            ],
            fill=c,
        )
        w = max(2, int(s * 0.05))
        cx, cy = s * 0.38, s * 0.50
        for f in [0.22, 0.35, 0.48]:
            d.arc(
                [cx - s * f, cy - s * f, cx + s * f, cy + s * f],
                -45,
                45,
                fill=c,
                width=w,
            )

    return _make(draw, size, color)


def icon_speaker_muted(size=24, color="#f87171"):
    def draw(d, s, c):
        d.polygon(
            [
                (s * 0.16, s * 0.38),
                (s * 0.16, s * 0.62),
                (s * 0.34, s * 0.62),
                (s * 0.48, s * 0.74),
                (s * 0.48, s * 0.26),
                (s * 0.34, s * 0.38),
            ],
            fill=c,
        )
        w = max(2, int(s * 0.06))
        d.line([(s * 0.62, s * 0.42), (s * 0.74, s * 0.58)], fill=c, width=w)
        d.line([(s * 0.62, s * 0.58), (s * 0.74, s * 0.42)], fill=c, width=w)

    return _make(draw, size, color)


# ── Microphone ────────────────────────────────────────────────────
def icon_mic(size=24, color="#34d399"):
    def draw(d, s, c):
        w = max(2, int(s * 0.05))
        cx, cap_r = s * 0.50, s * 0.16
        d.rounded_rectangle(
            [cx - cap_r, s * 0.12, cx + cap_r, s * 0.48], radius=int(cap_r), fill=c
        )
        arc_r = s * 0.26
        d.arc(
            [cx - arc_r, s * 0.34, cx + arc_r, s * 0.74],
            0,
            180,
            fill=c,
            width=max(2, int(s * 0.05)),
        )
        d.line([(cx, s * 0.68), (cx, s * 0.88)], fill=c, width=w)
        d.line([(s * 0.36, s * 0.88), (s * 0.64, s * 0.88)], fill=c, width=w)

    return _make(draw, size, color)


def icon_mic_muted(size=24, color="#f87171"):
    def draw(d, s, c):
        w = max(2, int(s * 0.05))
        cx, cap_r = s * 0.50, s * 0.16
        d.rounded_rectangle(
            [cx - cap_r, s * 0.12, cx + cap_r, s * 0.48], radius=int(cap_r), fill=c
        )
        arc_r = s * 0.26
        d.arc(
            [cx - arc_r, s * 0.34, cx + arc_r, s * 0.74],
            0,
            180,
            fill=c,
            width=max(2, int(s * 0.05)),
        )
        d.line([(cx, s * 0.68), (cx, s * 0.88)], fill=c, width=w)
        d.line([(s * 0.36, s * 0.88), (s * 0.64, s * 0.88)], fill=c, width=w)
        d.line(
            [(s * 0.12, s * 0.88), (s * 0.88, s * 0.12)],
            fill=c,
            width=max(3, int(s * 0.07)),
        )

    return _make(draw, size, color)


# ── Equalizer ─────────────────────────────────────────────────────
def icon_equalizer(size=24, color="#fbbf24"):
    def draw(d, s, c):
        w = max(2, int(s * 0.05))
        for x in [0.28, 0.50, 0.72]:
            d.line([(s * x, s * 0.20), (s * x, s * 0.80)], fill=c, width=w)
        r = s * 0.08
        for x, y in [(0.28, 0.60), (0.50, 0.35), (0.72, 0.50)]:
            d.ellipse([s * x - r, s * y - r, s * x + r, s * y + r], fill=c)

    return _make(draw, size, color)


# ── WiFi / Wireless Signal ─────────────────────────────────────────
def icon_wifi(size=24, color="#34d399"):
    def draw(d, s, c):
        w = max(2, int(s * 0.05))
        cx, cy = s * 0.50, s * 0.72
        r = s * 0.06
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
        for rf in [0.20, 0.40, 0.60]:
            rad = s * rf
            d.arc([cx - rad, cy - rad, cx + rad, cy + rad], 220, 320, fill=c, width=w)

    return _make(draw, size, color)


# ── Bluetooth ─────────────────────────────────────────────────────
def icon_bluetooth(size=24, color="#818cf8"):
    def draw(d, s, c):
        w = max(2, int(s * 0.08))
        d.line(
            [
                (s * 0.32, s * 0.30),
                (s * 0.68, s * 0.66),
                (s * 0.50, s * 0.84),
                (s * 0.50, s * 0.16),
                (s * 0.68, s * 0.34),
                (s * 0.32, s * 0.70),
            ],
            fill=c,
            width=w,
            joint="round",
        )

    return _make(draw, size, color)


# ── Gamepad ───────────────────────────────────────────────────────
def icon_gamepad(size=24, color="#e2e4e9"):
    def draw(d, s, c):
        w = max(2, int(s * 0.06))
        d.rounded_rectangle(
            [s * 0.12, s * 0.28, s * 0.88, s * 0.72],
            radius=int(s * 0.16),
            outline=c,
            width=w,
        )
        d.line([(s * 0.28, s * 0.40), (s * 0.28, s * 0.60)], fill=c, width=w)
        d.line([(s * 0.18, s * 0.50), (s * 0.38, s * 0.50)], fill=c, width=w)
        r = s * 0.045
        for x, y in [(0.68, 0.42), (0.78, 0.50), (0.68, 0.58), (0.58, 0.50)]:
            d.ellipse([s * x - r, s * y - r, s * x + r, s * y + r], fill=c)

    return _make(draw, size, color)


# ── Target / Crosshair ────────────────────────────────────────────
def icon_target(size=24, color="#e2e4e9"):
    def draw(d, s, c):
        w = max(2, int(s * 0.06))
        cx = cy = s * 0.50
        r = s * 0.32
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=w)
        cr = s * 0.05
        d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=c)
        d.line([(cx, cy - r - s * 0.10), (cx, cy - r + s * 0.06)], fill=c, width=w)
        d.line([(cx, cy + r - s * 0.06), (cx, cy + r + s * 0.10)], fill=c, width=w)
        d.line([(cx - r - s * 0.10, cy), (cx - r + s * 0.06, cy)], fill=c, width=w)
        d.line([(cx + r - s * 0.06, cy), (cx + r + s * 0.10, cy)], fill=c, width=w)

    return _make(draw, size, color)


# ── Music note ────────────────────────────────────────────────────
def icon_music(size=24, color="#e2e4e9"):
    def draw(d, s, c):
        w = max(2, int(s * 0.06))
        d.ellipse([s * 0.18, s * 0.60, s * 0.38, s * 0.76], fill=c)
        d.ellipse([s * 0.52, s * 0.50, s * 0.72, s * 0.66], fill=c)
        d.line([(s * 0.38, s * 0.68), (s * 0.38, s * 0.22)], fill=c, width=w)
        d.line([(s * 0.72, s * 0.58), (s * 0.72, s * 0.12)], fill=c, width=w)
        beam_w = max(3, int(s * 0.12))
        d.line([(s * 0.38, s * 0.22), (s * 0.72, s * 0.12)], fill=c, width=beam_w)

    return _make(draw, size, color)


# ── Headset / Connected ────────────────────────────────────────────
def icon_headset(size=24, color="#e2e4e9"):
    def draw(d, s, c):
        w = max(2, int(s * 0.06))
        cx, cy = s * 0.50, s * 0.50
        hb_r = s * 0.30
        d.arc([cx - hb_r, cy - hb_r, cx + hb_r, cy + hb_r], 180, 360, fill=c, width=w)
        cup_w = s * 0.12
        cup_y1 = cy - s * 0.05
        cup_y2 = cy + s * 0.23
        d.rounded_rectangle(
            [cx - hb_r - cup_w / 2, cup_y1, cx - hb_r + cup_w / 2, cup_y2],
            radius=int(cup_w / 2),
            fill=c,
        )
        d.rounded_rectangle(
            [cx + hb_r - cup_w / 2, cup_y1, cx + hb_r + cup_w / 2, cup_y2],
            radius=int(cup_w / 2),
            fill=c,
        )
        d.line(
            [cx - hb_r, cy + s * 0.12, cx - s * 0.12, cy + s * 0.32],
            fill=c,
            width=max(2, int(w * 0.7)),
        )
        r = s * 0.05
        d.ellipse(
            [
                cx - s * 0.12 - r,
                cy + s * 0.32 - r,
                cx - s * 0.12 + r,
                cy + s * 0.32 + r,
            ],
            fill=c,
        )

    return _make(draw, size, color)


# ── Battery Status Icon ────────────────────────────────────────────
def icon_battery_status(size=16, color="#34d399"):
    def draw(d, s, c):
        w = max(1.5, s * 0.08)
        d.rounded_rectangle(
            [s * 0.12, s * 0.28, s * 0.76, s * 0.72],
            radius=int(s * 0.08),
            outline=c,
            width=int(w),
        )
        d.rounded_rectangle(
            [s * 0.76, s * 0.42, s * 0.88, s * 0.58], radius=int(s * 0.04), fill=c
        )
        d.rounded_rectangle(
            [s * 0.22, s * 0.36, s * 0.42, s * 0.64], radius=int(s * 0.02), fill=c
        )
        d.rounded_rectangle(
            [s * 0.48, s * 0.36, s * 0.68, s * 0.64], radius=int(s * 0.02), fill=c
        )

    return _make(draw, size, color)


# ── Lightning Bolt ────────────────────────────────────────────────
def icon_lightning(size=16, color="#fbbf24"):
    def draw(d, s, c):
        d.polygon(
            [
                (s * 0.55, s * 0.12),
                (s * 0.24, s * 0.52),
                (s * 0.48, s * 0.52),
                (s * 0.45, s * 0.88),
                (s * 0.76, s * 0.48),
                (s * 0.52, s * 0.48),
            ],
            fill=c,
        )

    return _make(draw, size, color)


# ── Checkmark ─────────────────────────────────────────────────────
def icon_check(size=16, color="#34d399"):
    def draw(d, s, c):
        w = max(2, int(s * 0.10))
        d.line(
            [(s * 0.24, s * 0.50), (s * 0.42, s * 0.68), (s * 0.76, s * 0.28)],
            fill=c,
            width=w,
            joint="round",
        )

    return _make(draw, size, color)


# ── Crescent Moon ─────────────────────────────────────────────────
def icon_moon(size=16, color="#64748b"):
    def draw(d, s, c):
        d.ellipse([s * 0.24, s * 0.24, s * 0.76, s * 0.76], fill=c)
        d.ellipse([s * 0.38, s * 0.20, s * 0.82, s * 0.72], fill="#0f1318")

    return _make(draw, size, color)


# ── Alert Cross ───────────────────────────────────────────────────
def icon_cross(size=16, color="#f87171"):
    def draw(d, s, c):
        w = max(2, int(s * 0.08))
        d.line([(s * 0.28, s * 0.28), (s * 0.72, s * 0.72)], fill=c, width=w)
        d.line([(s * 0.28, s * 0.72), (s * 0.72, s * 0.28)], fill=c, width=w)

    return _make(draw, size, color)


# ═══════════════════════════════════════════════════════════════════════════
# Color Palette — Refined dark theme (2024+)
# ═══════════════════════════════════════════════════════════════════════════
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# ── Background & Surface ──────────────────────────────────────────
BG = "#0b0e14"  # Deep rich dark (main background)
SURFACE_1 = "#131720"  # Card surface (primary)
SURFACE_2 = "#1a1f2b"  # Card surface (elevated/hover)
SURFACE_3 = "#222838"  # Subtle overlay / secondary surface
BORDER = "#1e2433"  # Very subtle borders
BORDER_HOVER = "#2a3148"  # Borders on hover

# ── Accent Colors (Refined, modern) ──────────────────────────────
ACCENT_BLUE = "#60a5fa"  # Soft sky blue (volume, primary actions)
ACCENT_BLUE_DIM = "#3b82f6"  # Slightly deeper blue
ACCENT_INDIGO = "#818cf8"  # Indigo (bluetooth, secondary)
ACCENT_GREEN = "#34d399"  # Emerald green (connected, positive)
ACCENT_GREEN_DIM = "#10b981"
ACCENT_GOLD = "#fbbf24"  # Warm amber/gold (equalizer, highlights)
ACCENT_RED = "#f87171"  # Soft red (muted, errors, warning)
ACCENT_ORANGE = "#fb923c"  # Orange (charging)
ACCENT_PURPLE = "#a78bfa"  # Purple (secondary accent)
ACCENT_TEAL = "#2dd4bf"  # Teal accent

# ── Text Colors ───────────────────────────────────────────────────
TEXT_PRIMARY = "#f1f5f9"  # Main text (near white)
TEXT_SECONDARY = "#94a3b8"  # Secondary text (slate)
TEXT_MUTED = "#475569"  # Muted / disabled text
TEXT_DIM = "#334155"  # Very dim text
TEXT_ON_ACCENT = "#ffffff"  # Text on accent backgrounds

# ── Glow & Shadow Colors ──────────────────────────────────────────
GLOW_BLUE = "#1e3a5f"  # Blue glow background
GLOW_GREEN = "#064e3b"  # Green glow
GLOW_RED = "#450a0a"  # Red glow
GLOW_GOLD = "#451a03"  # Gold glow


# ── Battery color gradient (green → yellow → red) ───────────────────────────
def _lerp_rgb(c1, c2, t):
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
    )


def _battery_color(pct: int) -> str:
    pct = max(0, min(100, int(pct)))
    _GREEN = (52, 211, 153)  # #34d399
    _YELLOW = (251, 191, 36)  # #fbbf24
    _RED = (248, 113, 113)  # #f87171
    if pct >= 50:
        t = (100 - pct) / 50.0
        r, g, b = _lerp_rgb(_GREEN, _YELLOW, t)
    else:
        t = (50 - pct) / 50.0
        r, g, b = _lerp_rgb(_YELLOW, _RED, t)
    return f"#{int(round(r)):02x}{int(round(g)):02x}{int(round(b)):02x}"


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _gradient_color(pct):
    pct = max(0, min(100, int(pct)))
    # Define gradient stops: 100% green, 50% yellow, 0% red
    stops = [
        (100, _hex_to_rgb("#34d399")),
        (70, _hex_to_rgb("#6ee7b7")),
        (50, _hex_to_rgb("#fbbf24")),
        (30, _hex_to_rgb("#fb923c")),
        (0, _hex_to_rgb("#f87171")),
    ]
    for i in range(len(stops) - 1):
        p1, c1 = stops[i]
        p2, c2 = stops[i + 1]
        if pct >= p2:
            t = (p1 - pct) / (p1 - p2) if p1 != p2 else 0
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            return r, g, b
    return stops[-1][1]


class BatteryRing(tk.Canvas):

    def __init__(self, master, size=180, **kw):
        super().__init__(
            master, width=size, height=size, bg=SURFACE_1, highlightthickness=0, **kw
        )
        self._size = size
        self._pct = 0
        self._color = "#34d399"
        self._anim_pct = 0
        self._target_pct = 0
        self._animating = False

    def set_value(self, pct: int, color: str = "#34d399"):
        self._pct = max(0, min(100, pct))
        self._color = color
        self._target_pct = self._pct
        # Start animation if not already running
        if not self._animating:
            self._animate_to(self._target_pct)

    def _animate_to(self, target):
        # Update target if a new value arrived
        target = self._target_pct
        diff = target - self._anim_pct
        if abs(diff) < 1:
            self._anim_pct = target
            self._animating = False
            self._draw()
            return
        self._anim_pct += diff * 0.15
        self._draw()
        self._animating = True
        self.after(16, lambda: self._animate_to(self._target_pct))

    def _draw(self):
        self.delete("all")
        s = self._size
        cx = cy = s // 2
        pad = 14
        r = (s - 2 * pad) // 2
        w = max(6, int(r * 0.14))

        # ── Glow effect (subtle shadow behind the arc) ──
        glow_r = r + 4
        if self._anim_pct > 0:
            try:
                glow_img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
                gd = ImageDraw.Draw(glow_img)
                extent = -self._anim_pct * 3.6
                if extent <= -360:
                    extent = -359.99
                rgb = _hex_to_rgb(self._color)
                gd.arc(
                    [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
                    start=270,
                    end=270 + (self._anim_pct * 3.6),
                    fill=(*rgb, 40),
                    width=w + 8,
                )
                glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=6))
                self._glow_photo = ctk.CTkImage(
                    light_image=glow_img, dark_image=glow_img, size=(s, s)
                )
                self.create_image(0, 0, anchor="nw", image=self._glow_photo)
            except Exception:
                pass

        # ── Track (background ring) ──
        self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=BORDER, width=w)

        # ── Gradient arc ──
        if self._anim_pct > 0:
            extent = -self._anim_pct * 3.6
            if extent <= -360:
                extent = -359.99
            # Draw the main arc
            self.create_arc(
                cx - r,
                cy - r,
                cx + r,
                cy + r,
                start=90,
                extent=extent,
                outline=self._color,
                width=w,
                style="arc",
            )

        # ── Center content ──
        # Subtle background circle
        inner_r = r - w - 8
        if inner_r > 0:
            self.create_oval(
                cx - inner_r,
                cy - inner_r,
                cx + inner_r,
                cy + inner_r,
                fill="#0d1017",
                outline="",
            )

        # Percentage text
        font_size = max(22, int(r * 0.48))
        self.create_text(
            cx,
            cy - 4,
            text=f"{int(self._anim_pct)}%",
            fill=TEXT_PRIMARY,
            font=("Helvetica", font_size, "bold"),
        )

        # "BATERIA" label below
        label_size = max(8, int(r * 0.16))
        self.create_text(
            cx,
            cy + font_size * 0.55,
            text="BATERIA",
            fill=TEXT_MUTED,
            font=("Helvetica", label_size, "normal"),
        )


# ═══════════════════════════════════════════════════════════════════════════
# Modern Main Application
# ═══════════════════════════════════════════════════════════════════════════
class MchoseBatteryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MCHOSE V9 PRO")
        self.geometry("460x850")
        self.minsize(400, 800)
        self.configure(fg_color=BG)

        # ── state ─────────────────────────────────────────────────
        self.battery_level = 0
        self.status_code = 0
        self.connected = False
        self.connection_mode = None
        self.fw_dongle = ""
        self.fw_headset = ""
        self.eq_mode = 0
        self.volume_level = 50
        self.mic_level = 50
        self.mic_muted = False
        self._dragging_vol = False
        self._dragging_mic = False

        # ── HID ───────────────────────────────────────────────────
        self.hid = None
        self._init_hid()

        # ── UI ────────────────────────────────────────────────────
        self._build_ui()

        # ── auto-poll thread ──────────────────────────────────────
        self._stop = False
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

        # initial read
        self._refresh_system_audio()

    # ───────────────────────────────────────────────────────────────
    # UI construction
    # ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Scrollable main container
        self._main = ctk.CTkFrame(self, fg_color=BG)
        self._main.pack(fill="both", expand=True, padx=0, pady=0)
        self._main.columnconfigure(0, weight=1)

        self._build_header()
        self._build_battery_section()
        self._build_connection_section()
        self._build_volume_card()
        self._build_mic_card()
        self._build_eq_card()

    # ── header ─────────────────────────────────────────────────────
    def _build_header(self):
        frame = ctk.CTkFrame(
            self._main,
            fg_color="transparent",
        )
        frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(28, 0))
        frame.columnconfigure(0, weight=1)

        # Top accent line (decorative)
        accent_bar = ctk.CTkFrame(
            frame, fg_color=ACCENT_BLUE, height=3, corner_radius=2
        )
        accent_bar.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        # Product name
        ctk.CTkLabel(
            frame,
            text="MCHOSE",
            font=("Helvetica", 14, "bold"),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w")

        ctk.CTkLabel(
            frame,
            text="V9 PRO CONTROLLER",
            font=("Helvetica", 26, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        # Firmware info
        self._fw_label = ctk.CTkLabel(
            frame,
            text="",
            font=("Helvetica", 11),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self._fw_label.grid(row=3, column=0, sticky="w", pady=(0, 0))

    # ── battery section ────────────────────────────────────────────
    def _build_battery_section(self):
        card = self._make_card(row=1, pady_top=16)

        # Battery ring (centered)
        self._ring = BatteryRing(card, size=180)
        self._ring.pack(pady=(20, 8))

        # Status badge (below ring)
        self._status_frame = ctk.CTkFrame(
            card, fg_color=SURFACE_3, corner_radius=20, height=32
        )
        self._status_frame.pack(pady=(4, 16), padx=20)
        self._status_frame.pack_propagate(False)

        self._status_icon = ctk.CTkLabel(
            self._status_frame, image=icon_cross(14, ACCENT_RED), text=""
        )
        self._status_icon.pack(side="left", padx=(12, 4))

        self._status_label = ctk.CTkLabel(
            self._status_frame,
            text="Fone não detectado",
            font=("Helvetica", 11, "bold"),
            text_color=ACCENT_RED,
        )
        self._status_label.pack(side="left", padx=(0, 12))

    # ── connection section ─────────────────────────────────────────
    def _build_connection_section(self):
        card = self._make_card(row=2, pady_top=8)

        conn_row = ctk.CTkFrame(card, fg_color="transparent")
        conn_row.pack(fill="x", padx=20, pady=(14, 14))

        # Left side: icon + connection info
        left = ctk.CTkFrame(conn_row, fg_color="transparent")
        left.pack(side="left")

        self._conn_icon_cv = ctk.CTkLabel(
            left, image=icon_headset(20, TEXT_MUTED), text=""
        )
        self._conn_icon_cv.pack(side="left", padx=(0, 8))

        info_frame = ctk.CTkFrame(left, fg_color="transparent")
        info_frame.pack(side="left")

        self._conn_text = ctk.CTkLabel(
            info_frame,
            text="Desconectado",
            font=("Helvetica", 12, "bold"),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self._conn_text.pack(anchor="w")

        self._conn_mode_label = ctk.CTkLabel(
            info_frame,
            text="Aguardando conexão...",
            font=("Helvetica", 10),
            text_color=TEXT_DIM,
            anchor="w",
        )
        self._conn_mode_label.pack(anchor="w")

        # Right side: connection indicator dot
        self._conn_dot = tk.Canvas(
            conn_row, width=10, height=10, bg=SURFACE_1, highlightthickness=0
        )
        self._conn_dot.pack(side="right")
        self._draw_dot(TEXT_DIM)

    def _draw_dot(self, color):
        self._conn_dot.delete("all")
        self._conn_dot.create_oval(1, 1, 9, 9, fill=color, outline="")

    # ── volume card ────────────────────────────────────────────────
    def _build_volume_card(self):
        card = self._make_card(row=3, pady_top=8)

        # Header row
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 0))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")

        vol_icon = ctk.CTkLabel(left, image=icon_speaker(18, ACCENT_BLUE), text="")
        vol_icon.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            left,
            text="Volume",
            font=("Helvetica", 13, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        self._vol_pct = ctk.CTkLabel(
            header,
            text="50%",
            font=("Helvetica", 14, "bold"),
            text_color=ACCENT_BLUE,
        )
        self._vol_pct.pack(side="right")

        # Slider
        self._vol_slider = ctk.CTkSlider(
            card,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._on_vol_slide,
            button_color=ACCENT_BLUE,
            button_hover_color="#93c5fd",
            progress_color=ACCENT_BLUE,
            button_length=22,
            button_corner_radius=11,
            height=20,
            corner_radius=10,
        )
        self._vol_slider.set(self.volume_level)
        self._vol_slider.pack(fill="x", padx=20, pady=(12, 16))
        self._vol_slider.bind(
            "<ButtonRelease-1>", lambda e: setattr(self, "_dragging_vol", False)
        )

    def _on_vol_slide(self, val):
        self._dragging_vol = True
        self._on_vol_change(val)

    def _on_vol_change(self, val):
        v = int(val)
        self.volume_level = v
        self._vol_pct.configure(text=f"{v}%")
        threading.Thread(target=self._set_sys_vol, args=(v,), daemon=True).start()

    # ── microphone card ────────────────────────────────────────────
    def _build_mic_card(self):
        card = self._make_card(row=4, pady_top=8)

        # Header row
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 0))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")

        self._mic_icon_cv = ctk.CTkLabel(
            left, image=icon_mic(18, ACCENT_GREEN), text=""
        )
        self._mic_icon_cv.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            left,
            text="Microfone",
            font=("Helvetica", 13, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        # Container for switch and percentage on the right
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side="right")

        # Mute switch
        self._mic_switch = ctk.CTkSwitch(
            right_frame,
            text="Mudo",
            onvalue=1,
            offvalue=0,
            command=self._on_mic_switch,
            font=("Helvetica", 11),
            button_color=ACCENT_RED if self.mic_muted else ACCENT_GREEN,
            button_hover_color="#fca5a5" if self.mic_muted else "#6ee7b7",
            progress_color=ACCENT_RED,
            text_color=TEXT_SECONDARY,
        )
        self._mic_switch.pack(side="left", padx=(0, 16))
        if self.mic_muted:
            self._mic_switch.select()

        # Percentage label
        self._mic_pct = ctk.CTkLabel(
            right_frame,
            text="50%",
            font=("Helvetica", 14, "bold"),
            text_color=ACCENT_RED if self.mic_muted else ACCENT_GREEN,
        )
        self._mic_pct.pack(side="left")

        # Slider
        self._mic_slider = ctk.CTkSlider(
            card,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._on_mic_slide,
            button_color=ACCENT_GREEN,
            button_hover_color="#6ee7b7",
            progress_color=ACCENT_GREEN,
            button_length=22,
            button_corner_radius=11,
            height=20,
            corner_radius=10,
        )
        self._mic_slider.set(self.mic_level)
        self._mic_slider.pack(fill="x", padx=20, pady=(12, 16))
        self._mic_slider.bind(
            "<ButtonRelease-1>", lambda e: setattr(self, "_dragging_mic", False)
        )

    def _on_mic_switch(self):
        self.mic_muted = bool(self._mic_switch.get())
        color = ACCENT_RED if self.mic_muted else ACCENT_GREEN
        self._mic_icon_cv.configure(
            image=icon_mic_muted(18, color) if self.mic_muted else icon_mic(18, color)
        )
        self._mic_switch.configure(
            button_color=color,
            button_hover_color="#fca5a5" if self.mic_muted else "#6ee7b7",
        )
        self._mic_pct.configure(text_color=color)
        threading.Thread(
            target=self._set_sys_mic_mute, args=(self.mic_muted,), daemon=True
        ).start()

    def _on_mic_slide(self, val):
        self._dragging_mic = True
        self._on_mic_change(val)

    def _on_mic_change(self, val):
        v = int(val)
        self.mic_level = v
        self._mic_pct.configure(text=f"{v}%")
        threading.Thread(target=self._set_sys_vol, args=(v, False), daemon=True).start()

    # ── equalizer card ─────────────────────────────────────────────
    def _build_eq_card(self):
        card = self._make_card(row=5, pady_top=8)

        # Header
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 0))

        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left")

        eq_icon = ctk.CTkLabel(left, image=icon_equalizer(18, ACCENT_GOLD), text="")
        eq_icon.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            left,
            text="Equalizador",
            font=("Helvetica", 13, "bold"),
            text_color=ACCENT_GOLD,
        ).pack(side="left")

        self._eq_hint = ctk.CTkLabel(
            top,
            text="",
            font=("Helvetica", 10),
            text_color=TEXT_MUTED,
        )
        self._eq_hint.pack(side="right")

        # EQ buttons
        eq_frame = ctk.CTkFrame(card, fg_color="transparent")
        eq_frame.pack(fill="x", padx=20, pady=(12, 16))
        eq_frame.columnconfigure((0, 1, 2), weight=1)

        labels = ["Jogo 1", "Jogo 2", "Música"]
        icons_fn = [icon_gamepad, icon_target, icon_music]
        self._eq_btns = []
        self._eq_icon_imgs = []

        for i, txt in enumerate(labels):
            btn = ctk.CTkButton(
                eq_frame,
                text=txt,
                corner_radius=12,
                font=("Helvetica", 12, "bold"),
                height=40,
                fg_color=SURFACE_2,
                hover_color=SURFACE_3,
                border_width=1,
                border_color=BORDER,
                text_color=TEXT_SECONDARY,
                command=lambda m=i: self._change_eq(m),
            )
            btn.grid(row=0, column=i, sticky="ew", padx=4)
            self._eq_btns.append(btn)
            img = icons_fn[i](14, TEXT_SECONDARY)
            self._eq_icon_imgs.append(img)
            btn.configure(image=img, compound="left")

        self._update_eq_buttons()

    def _change_eq(self, mode):
        self.eq_mode = mode
        self._update_eq_buttons()
        threading.Thread(
            target=self._send_eq_command, args=(mode,), daemon=True
        ).start()

    def _update_eq_buttons(self):
        enabled = self.connected and self.connection_mode == "2.4G"
        eq_fns = [icon_gamepad, icon_target, icon_music]
        for i, btn in enumerate(self._eq_btns):
            if i == self.eq_mode and enabled:
                btn.configure(
                    fg_color=ACCENT_GOLD,
                    hover_color="#fcd34d",
                    text_color="#000000",
                    border_color=ACCENT_GOLD,
                )
                ic_color = "#000000"
            elif enabled:
                btn.configure(
                    fg_color=SURFACE_2,
                    hover_color=SURFACE_3,
                    text_color=TEXT_SECONDARY,
                    border_color=BORDER,
                )
                ic_color = TEXT_SECONDARY
            else:
                btn.configure(
                    fg_color=BG,
                    hover_color=BG,
                    text_color=TEXT_DIM,
                    border_color="#151a24",
                )
                ic_color = TEXT_DIM
            self._eq_icon_imgs[i] = eq_fns[i](14, ic_color)
            btn.configure(image=self._eq_icon_imgs[i])

        if not enabled:
            self._eq_hint.configure(text="somente 2.4G")
        else:
            self._eq_hint.configure(text="")

    # ── card helper ────────────────────────────────────────────────
    def _make_card(self, row, pady_top=8):
        f = ctk.CTkFrame(
            self._main,
            fg_color=SURFACE_1,
            corner_radius=16,
            border_width=1,
            border_color=BORDER,
        )
        f.grid(row=row, column=0, sticky="ew", padx=20, pady=(pady_top, 0))
        return f

    # ═══════════════════════════════════════════════════════════════════
    # UI refresh (called from poll thread)
    # ═══════════════════════════════════════════════════════════════════
    def _refresh_ui(self):
        bat = self.battery_level
        bcolor = _battery_color(bat)
        self._ring.set_value(bat if self.connected else 0, bcolor)

        if self.connected:
            mode = self.connection_mode or ""
            icon_color = ACCENT_INDIGO if mode == "Bluetooth" else ACCENT_GREEN
            dot_color = ACCENT_INDIGO if mode == "Bluetooth" else ACCENT_GREEN

            if mode == "Bluetooth":
                self._conn_icon_cv.configure(image=icon_bluetooth(20, icon_color))
            else:
                self._conn_icon_cv.configure(image=icon_wifi(20, icon_color))

            self._conn_text.configure(text="Conectado", text_color=TEXT_PRIMARY)
            self._conn_mode_label.configure(text=mode, text_color=icon_color)
            self._draw_dot(dot_color)

            # Status badge
            status_map = {
                0x02: (
                    "Em uso",
                    icon_battery_status(14, ACCENT_GREEN),
                    ACCENT_GREEN,
                    GLOW_GREEN,
                ),
                0x03: (
                    "Carregando...",
                    icon_lightning(14, ACCENT_ORANGE),
                    ACCENT_ORANGE,
                    GLOW_GOLD,
                ),
                0x04: (
                    "Carregado (100%)",
                    icon_check(14, ACCENT_GREEN),
                    ACCENT_GREEN,
                    GLOW_GREEN,
                ),
                0x1A: (
                    "Modo de Suspensão",
                    icon_moon(14, TEXT_SECONDARY),
                    TEXT_SECONDARY,
                    SURFACE_3,
                ),
            }

            if mode == "2.4G":
                mapped = status_map.get(self.status_code)
                if mapped:
                    txt, img, txt_color, bg = mapped
                else:
                    txt, img, txt_color, bg = (
                        f"Status: {hex(self.status_code)}",
                        icon_battery_status(14, ACCENT_GREEN),
                        ACCENT_GREEN,
                        GLOW_GREEN,
                    )
            else:
                txt = "Bluetooth conectado"
                img = icon_bluetooth(14, ACCENT_INDIGO)
                txt_color = ACCENT_INDIGO
                bg = GLOW_BLUE

            self._status_label.configure(text=txt, text_color=txt_color)
            self._status_icon.configure(image=img)
            self._status_frame.configure(fg_color=bg)

        else:
            self._conn_icon_cv.configure(image=icon_headset(20, TEXT_DIM))
            self._conn_text.configure(text="Desconectado", text_color=TEXT_MUTED)
            self._conn_mode_label.configure(
                text="Aguardando conexão...", text_color=TEXT_DIM
            )
            self._draw_dot(TEXT_DIM)
            self._status_label.configure(
                text="Fone não detectado", text_color=ACCENT_RED
            )
            self._status_icon.configure(image=icon_cross(14, ACCENT_RED))
            self._status_frame.configure(fg_color=GLOW_RED)
            self.fw_dongle = ""
            self.fw_headset = ""

        # firmware
        if self.connected:
            fw = f"FW Dongle: {self.fw_dongle or '—'}  •  FW Headset: {self.fw_headset or '—'}"
        else:
            fw = ""
        self._fw_label.configure(text=fw)

        # volume slider
        if not self._vol_slider.get() == self.volume_level:
            self._vol_slider.set(self.volume_level)
        self._vol_pct.configure(text=f"{self.volume_level}%")

        # mic
        self._mic_slider.set(self.mic_level)
        self._mic_pct.configure(text=f"{self.mic_level}%")
        if self.mic_muted:
            if not self._mic_switch.get():
                self._mic_switch.select()
            self._mic_icon_cv.configure(image=icon_mic_muted(18, ACCENT_RED))
            self._mic_switch.configure(
                button_color=ACCENT_RED, button_hover_color="#fca5a5"
            )
            self._mic_pct.configure(text_color=ACCENT_RED)
        else:
            if self._mic_switch.get():
                self._mic_switch.deselect()
            self._mic_icon_cv.configure(image=icon_mic(18, ACCENT_GREEN))
            self._mic_switch.configure(
                button_color=ACCENT_GREEN, button_hover_color="#6ee7b7"
            )
            self._mic_pct.configure(text_color=ACCENT_GREEN)

        self._update_eq_buttons()

    # ═══════════════════════════════════════════════════════════════════
    # HID helpers
    # ═══════════════════════════════════════════════════════════════════
    def _init_hid(self):
        candidates = [
            ctypes.util.find_library("hidapi-hidraw"),
            "libhidapi-hidraw.so.0",
            "libhidapi-hidraw.so",
            "/usr/lib/x86_64-linux-gnu/libhidapi-hidraw.so.0",
        ]
        for lib_path in (p for p in candidates if p):
            try:
                self.hid = ctypes.CDLL(lib_path)
                break
            except Exception:
                continue
        else:
            return

        try:
            self.hid.hid_init()
            self.hid.hid_open.argtypes = [
                ctypes.c_ushort,
                ctypes.c_ushort,
                ctypes.c_wchar_p,
            ]
            self.hid.hid_open.restype = ctypes.c_void_p
            self.hid.hid_write.argtypes = [
                ctypes.c_void_p,
                ctypes.c_char_p,
                ctypes.c_size_t,
            ]
            self.hid.hid_write.restype = ctypes.c_int
            self.hid.hid_read_timeout.argtypes = [
                ctypes.c_void_p,
                ctypes.c_char_p,
                ctypes.c_size_t,
                ctypes.c_int,
            ]
            self.hid.hid_read_timeout.restype = ctypes.c_int
            self.hid.hid_send_feature_report.argtypes = [
                ctypes.c_void_p,
                ctypes.c_char_p,
                ctypes.c_size_t,
            ]
            self.hid.hid_send_feature_report.restype = ctypes.c_int
            self.hid.hid_get_feature_report.argtypes = [
                ctypes.c_void_p,
                ctypes.c_char_p,
                ctypes.c_size_t,
            ]
            self.hid.hid_get_feature_report.restype = ctypes.c_int
            self.hid.hid_close.argtypes = [ctypes.c_void_p]
            self.hid.hid_close.restype = None
            self.hid.hid_exit.argtypes = []
            self.hid.hid_exit.restype = ctypes.c_int
        except Exception:
            self.hid = None

    def _query_hid(self):
        if not self.hid:
            return False, 0, 0, 0
        handle = self.hid.hid_open(0x291D, 0x385D, None)
        if not handle:
            return False, 0, 0, 0
        battery = status_code = eq_mode = 0
        ok_bat = ok_eq = False
        try:
            buf = bytearray(64)
            buf[0], buf[1], buf[2] = 0x55, 0x65, 0x01
            c_buf = (ctypes.c_char * 64).from_buffer(buf)
            if self.hid.hid_write(handle, c_buf, 64) > 0:
                rbuf = bytearray(64)
                c_r = (ctypes.c_char * 64).from_buffer(rbuf)
                if self.hid.hid_read_timeout(handle, c_r, 64, 500) > 0:
                    d = list(rbuf)
                    if d[0] == 0x55 and d[1] == 0x65:
                        battery, status_code = d[2], d[3]
                        ok_bat = True
            buf2 = bytearray(64)
            buf2[0], buf2[1] = 0x55, 0x11
            c2 = (ctypes.c_char * 64).from_buffer(buf2)
            if self.hid.hid_write(handle, c2, 64) > 0:
                r2 = bytearray(64)
                c_r2 = (ctypes.c_char * 64).from_buffer(r2)
                if self.hid.hid_read_timeout(handle, c_r2, 64, 500) > 0:
                    d2 = list(r2)
                    if d2[0] == 0x55 and d2[1] == 0x11:
                        eq_mode = d2[2]
                        ok_eq = True
        except Exception:
            pass
        finally:
            self.hid.hid_close(handle)
        if ok_bat:
            return True, battery, status_code, eq_mode if ok_eq else self.eq_mode
        return False, 0, 0, 0

    def _send_eq_command(self, mode):
        if not self.hid:
            return False
        handle = self.hid.hid_open(0x291D, 0x385D, None)
        if not handle:
            return False
        try:
            buf = bytearray(64)
            buf[0], buf[1], buf[2], buf[3] = 0x55, 0x21, 0x01, mode
            c = (ctypes.c_char * 64).from_buffer(buf)
            if self.hid.hid_write(handle, c, 64) <= 0:
                return False
            time.sleep(0.05)
            q = bytearray(64)
            q[0], q[1] = 0x55, 0x11
            cq = (ctypes.c_char * 64).from_buffer(q)
            self.hid.hid_write(handle, cq, 64)
            rb = bytearray(64)
            cr = (ctypes.c_char * 64).from_buffer(rb)
            if self.hid.hid_read_timeout(handle, cr, 64, 300) > 2:
                if rb[0] == 0x55 and rb[1] == 0x11:
                    self.eq_mode = int(rb[2])
            return True
        except Exception:
            return False
        finally:
            self.hid.hid_close(handle)

    def _get_firmware(self):
        if not self.hid:
            return "", ""
        handle = self.hid.hid_open(0x291D, 0x385D, None)
        if not handle:
            return "", ""
        fw_dongle = fw_headset = ""
        try:
            buf = bytearray(64)
            buf[0], buf[1], buf[2] = 0xAA, 0x01, 0x00
            c = (ctypes.c_char * 64).from_buffer(buf)
            if self.hid.hid_send_feature_report(handle, c, 64) <= 0:
                return "", ""
            for delay in (0.3, 0.5, 0.9):
                time.sleep(delay)
                rb = bytearray(64)
                rb[0] = 0xAA
                cr = (ctypes.c_char * 64).from_buffer(rb)
                if self.hid.hid_get_feature_report(handle, cr, 64) > 0:
                    d = list(rb)
                    if d[0] == 0xAA:
                        if len(d) >= 10:
                            fw_dongle = f"{d[8]:02d}{d[9]:02d}"
                        if len(d) >= 12:
                            fw_headset = f"{d[10]:02d}{d[11]:02d}"
                        break
        except Exception:
            pass
        finally:
            self.hid.hid_close(handle)
        return fw_dongle, fw_headset

    # ═══════════════════════════════════════════════════════════════════
    # Bluetooth (D-Bus / BlueZ)
    # ═══════════════════════════════════════════════════════════════════
    def _query_bluetooth(self):
        if not HAS_DBUS:
            return False, 0
        try:
            bus = dbus.SystemBus()
            mgr = dbus.Interface(
                bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager"
            )
            for path, ifaces in mgr.GetManagedObjects().items():
                dev = ifaces.get("org.bluez.Device1")
                if not dev:
                    continue
                name = dev.get("Name", dev.get("Alias", ""))
                if "MCHOSE V9 PRO" in name or "V9 PRO" in name:
                    if dev.get("Connected", False):
                        bat = ifaces.get("org.bluez.Battery1")
                        pct = int(bat.get("Percentage", 100)) if bat else 100
                        return True, pct
        except Exception:
            pass
        return False, 0

    # ═══════════════════════════════════════════════════════════════════
    # System audio helpers
    # ═══════════════════════════════════════════════════════════════════
    @staticmethod
    def _get_sys_vol(sink=True):
        target = "@DEFAULT_AUDIO_SINK@" if sink else "@DEFAULT_AUDIO_SOURCE@"
        for cmd in (
            ["wpctl", "get-volume", target],
            ["amixer", "sget", "Master" if sink else "Capture"],
        ):
            try:
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                m = re.search(r"(?:Volume:\s*|(\d+)%)", out)
                if m:
                    val = m.group(1)
                    if val:
                        return int(val)
                    m2 = re.search(r"Volume:\s*([0-9.]+)", out)
                    if m2:
                        return int(float(m2.group(1)) * 100)
            except Exception:
                pass
        return 50

    @staticmethod
    def _set_sys_vol(value, sink=True):
        value = max(0, min(100, value))
        target = "@DEFAULT_AUDIO_SINK@" if sink else "@DEFAULT_AUDIO_SOURCE@"
        for cmd in (
            ["wpctl", "set-volume", target, f"{value / 100:.2f}", "-"],
            ["amixer", "sset", "Master" if sink else "Capture", f"{value}%"],
        ):
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except Exception:
                continue

    @staticmethod
    def _get_sys_mic_mute():
        for cmd in (
            ["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"],
            ["amixer", "sget", "Capture"],
            ["amixer", "sget", "Mic"],
        ):
            try:
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                if "[MUTED]" in out or "[off]" in out:
                    return True
            except Exception:
                pass
        return False

    @staticmethod
    def _set_sys_mic_mute(state):
        val = "1" if state else "0"
        for cmd in (
            ["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", val],
            ["amixer", "sset", "Capture", "mute" if state else "unmute"],
            ["amixer", "sset", "Mic", "mute" if state else "unmute"],
        ):
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except Exception:
                continue

    def _refresh_system_audio(self):
        if not self._dragging_vol:
            self.volume_level = self._get_sys_vol(sink=True)
        self.mic_muted = self._get_sys_mic_mute()
        if not self._dragging_mic:
            self.mic_level = self._get_sys_vol(sink=False)

    # ═══════════════════════════════════════════════════════════════════
    # Poll thread
    # ═══════════════════════════════════════════════════════════════════
    def _poll_loop(self):
        fw_counter = 0
        while not self._stop:
            ok, bat, sc, eq = self._query_hid()
            if ok:
                was_off = not self.connected
                self.connected = True
                self.connection_mode = "2.4G"
                self.battery_level = bat
                self.status_code = sc
                self.eq_mode = eq
                fw_counter += 1
                if (was_off and not self.fw_dongle) or fw_counter >= 60:
                    fw_counter = 0
                    fd, fh = self._get_firmware()
                    if fd:
                        self.fw_dongle = fd
                    if fh:
                        self.fw_headset = fh
            else:
                ok_bt, bat_bt = self._query_bluetooth()
                if ok_bt:
                    self.connected = True
                    self.connection_mode = "Bluetooth"
                    self.battery_level = bat_bt
                    self.status_code = 0x02
                else:
                    self.connected = False
                    self.connection_mode = None

            self._refresh_system_audio()
            self.after(0, self._refresh_ui)

            for _ in range(20):
                if self._stop:
                    break
                time.sleep(0.1)


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════
def main():
    app = MchoseBatteryApp()

    def on_close():
        app._stop = True

        def _wait(deadline):
            if app._thread.is_alive() and time.time() < deadline:
                app.after(50, _wait, deadline)
            else:
                if app.hid:
                    try:
                        app.hid.hid_exit()
                    except Exception:
                        pass
                try:
                    app.destroy()
                except Exception:
                    pass

        _wait(time.time() + 1.0)

    app.protocol("WM_DELETE_WINDOW", on_close)
    try:
        app.mainloop()
    except KeyboardInterrupt:
        on_close()


if __name__ == "__main__":
    main()

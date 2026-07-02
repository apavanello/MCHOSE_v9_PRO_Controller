#!/usr/bin/env python3
import ctypes
import ctypes.util
import subprocess
import re
import threading
import time
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
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
    """Create a CTkImage by drawing at 4x then downscaling."""
    px = size * _SCALE
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_fn(d, px, color)
    img = img.resize((size, size), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


# ── Speaker / Volume ──────────────────────────────────────────────
def icon_speaker(size=24, color="#4a9eff"):
    def draw(d, s, c):
        # speaker body
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
        # 3 sound waves (concentric arcs on the right side)
        w = max(2, int(s * 0.05))
        cx = s * 0.38
        cy = s * 0.50
        # Arc 1
        d.arc(
            [cx - s * 0.22, cy - s * 0.22, cx + s * 0.22, cy + s * 0.22],
            -45,
            45,
            fill=c,
            width=w,
        )
        # Arc 2
        d.arc(
            [cx - s * 0.35, cy - s * 0.35, cx + s * 0.35, cy + s * 0.35],
            -45,
            45,
            fill=c,
            width=w,
        )
        # Arc 3
        d.arc(
            [cx - s * 0.48, cy - s * 0.48, cx + s * 0.48, cy + s * 0.48],
            -45,
            45,
            fill=c,
            width=w,
        )

    return _make(draw, size, color)


# ── Speaker muted ─────────────────────────────────────────────────
def icon_speaker_muted(size=24, color="#f87171"):
    def draw(d, s, c):
        # speaker body
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
        # elegant 'X' on the right representing muted
        w = max(2, int(s * 0.06))
        d.line([(s * 0.62, s * 0.42), (s * 0.74, s * 0.58)], fill=c, width=w)
        d.line([(s * 0.62, s * 0.58), (s * 0.74, s * 0.42)], fill=c, width=w)

    return _make(draw, size, color)


# ── Microphone ────────────────────────────────────────────────────
def icon_mic(size=24, color="#4ade80"):
    def draw(d, s, c):
        w = max(2, int(s * 0.05))
        # mic capsule (rounded top)
        cx = s * 0.50
        cap_r = s * 0.16
        cap_top = s * 0.12
        cap_bot = s * 0.48
        d.rounded_rectangle(
            [cx - cap_r, cap_top, cx + cap_r, cap_bot], radius=int(cap_r), fill=c
        )
        # holder arc
        arc_r = s * 0.26
        d.arc(
            [cx - arc_r, s * 0.34, cx + arc_r, s * 0.74],
            0,
            180,
            fill=c,
            width=max(2, int(s * 0.05)),
        )
        # stand
        d.line([(cx, s * 0.68), (cx, s * 0.88)], fill=c, width=w)
        d.line([(s * 0.36, s * 0.88), (s * 0.64, s * 0.88)], fill=c, width=w)

    return _make(draw, size, color)


# ── Microphone muted ──────────────────────────────────────────────
def icon_mic_muted(size=24, color="#f87171"):
    def draw(d, s, c):
        w = max(2, int(s * 0.05))
        cx = s * 0.50
        cap_r = s * 0.16
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
        # slash
        d.line(
            [(s * 0.12, s * 0.88), (s * 0.88, s * 0.12)],
            fill=c,
            width=max(3, int(s * 0.07)),
        )

    return _make(draw, size, color)


# ── Equalizer ─────────────────────────────────────────────────────
def icon_equalizer(size=24, color="#f0c040"):
    def draw(d, s, c):
        w = max(2, int(s * 0.05))
        d.line([(s * 0.28, s * 0.20), (s * 0.28, s * 0.80)], fill=c, width=w)
        d.line([(s * 0.50, s * 0.20), (s * 0.50, s * 0.80)], fill=c, width=w)
        d.line([(s * 0.72, s * 0.20), (s * 0.72, s * 0.80)], fill=c, width=w)
        r = s * 0.08
        d.ellipse([s * 0.28 - r, s * 0.60 - r, s * 0.28 + r, s * 0.60 + r], fill=c)
        d.ellipse([s * 0.50 - r, s * 0.35 - r, s * 0.50 + r, s * 0.35 + r], fill=c)
        d.ellipse([s * 0.72 - r, s * 0.50 - r, s * 0.72 + r, s * 0.50 + r], fill=c)

    return _make(draw, size, color)


# ── WiFi / Wireless Signal ─────────────────────────────────────────
def icon_wifi(size=24, color="#4ade80"):
    def draw(d, s, c):
        w = max(2, int(s * 0.05))
        cx = s * 0.50
        cy = s * 0.72
        r = s * 0.06
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
        for rad_factor in [0.20, 0.40, 0.60]:
            rad = s * rad_factor
            d.arc(
                [cx - rad, cy - rad, cx + rad, cy + rad],
                220,
                320,
                fill=c,
                width=w,
            )

    return _make(draw, size, color)


# ── Bluetooth ─────────────────────────────────────────────────────
def icon_bluetooth(size=24, color="#4a9eff"):
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
        # controller outline
        d.rounded_rectangle(
            [s * 0.12, s * 0.28, s * 0.88, s * 0.72],
            radius=int(s * 0.16),
            outline=c,
            width=w,
        )
        # d-pad (cross)
        d.line([(s * 0.28, s * 0.40), (s * 0.28, s * 0.60)], fill=c, width=w)
        d.line([(s * 0.18, s * 0.50), (s * 0.38, s * 0.50)], fill=c, width=w)
        # 4 action buttons on the right (represented by small dots)
        r = s * 0.045
        d.ellipse([s * 0.68 - r, s * 0.42 - r, s * 0.68 + r, s * 0.42 + r], fill=c)
        d.ellipse([s * 0.78 - r, s * 0.50 - r, s * 0.78 + r, s * 0.50 + r], fill=c)
        d.ellipse([s * 0.68 - r, s * 0.58 - r, s * 0.68 + r, s * 0.58 + r], fill=c)
        d.ellipse([s * 0.58 - r, s * 0.50 - r, s * 0.58 + r, s * 0.50 + r], fill=c)

    return _make(draw, size, color)


# ── Target / Crosshair ────────────────────────────────────────────
def icon_target(size=24, color="#e2e4e9"):
    def draw(d, s, c):
        w = max(2, int(s * 0.06))
        cx = cy = s * 0.50
        # outer circle
        r = s * 0.32
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=w)
        # center dot
        cr = s * 0.05
        d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=c)
        # 4 short crosshair ticks on the edges
        d.line([(cx, cy - r - s * 0.10), (cx, cy - r + s * 0.06)], fill=c, width=w)
        d.line([(cx, cy + r - s * 0.06), (cx, cy + r + s * 0.10)], fill=c, width=w)
        d.line([(cx - r - s * 0.10, cy), (cx - r + s * 0.06, cy)], fill=c, width=w)
        d.line([(cx + r - s * 0.06, cy), (cx + r + s * 0.10, cy)], fill=c, width=w)

    return _make(draw, size, color)


# ── Music note ────────────────────────────────────────────────────
def icon_music(size=24, color="#e2e4e9"):
    def draw(d, s, c):
        w = max(2, int(s * 0.06))
        # Note 1 head (left)
        d.ellipse([s * 0.18, s * 0.60, s * 0.38, s * 0.76], fill=c)
        # Note 2 head (right)
        d.ellipse([s * 0.52, s * 0.50, s * 0.72, s * 0.66], fill=c)
        # Stems
        d.line([(s * 0.38, s * 0.68), (s * 0.38, s * 0.22)], fill=c, width=w)
        d.line([(s * 0.72, s * 0.58), (s * 0.72, s * 0.12)], fill=c, width=w)
        # Connecting beam (slanted bar at the top)
        beam_w = max(3, int(s * 0.12))
        d.line([(s * 0.38, s * 0.22), (s * 0.72, s * 0.12)], fill=c, width=beam_w)

    return _make(draw, size, color)


# ── Headset / Connected ────────────────────────────────────────────
def icon_headset(size=24, color="#e2e4e9"):
    def draw(d, s, c):
        w = max(2, int(s * 0.06))
        cx = s * 0.50
        cy = s * 0.50

        # Headband arc (upper half circle)
        hb_r = s * 0.30
        d.arc([cx - hb_r, cy - hb_r, cx + hb_r, cy + hb_r], 180, 360, fill=c, width=w)

        # Left and Right ear cups
        cup_w = s * 0.12
        cup_y1 = cy - s * 0.05
        cup_y2 = cy + s * 0.23

        # Left cup
        d.rounded_rectangle(
            [cx - hb_r - cup_w / 2, cup_y1, cx - hb_r + cup_w / 2, cup_y2],
            radius=int(cup_w / 2),
            fill=c,
        )

        # Right cup
        d.rounded_rectangle(
            [cx + hb_r - cup_w / 2, cup_y1, cx + hb_r + cup_w / 2, cup_y2],
            radius=int(cup_w / 2),
            fill=c,
        )

        # Mic boom (extending from left cup)
        d.line(
            [cx - hb_r, cy + s * 0.12, cx - s * 0.12, cy + s * 0.32],
            fill=c,
            width=max(2, int(w * 0.7)),
        )
        # Mic tip
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
def icon_battery_status(size=16, color="#4ade80"):
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
def icon_lightning(size=16, color="#f59e0b"):
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
def icon_check(size=16, color="#4ade80"):
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
def icon_moon(size=16, color="#9ca3af"):
    def draw(d, s, c):
        d.ellipse([s * 0.24, s * 0.24, s * 0.76, s * 0.76], fill=c)
        d.ellipse([s * 0.38, s * 0.20, s * 0.82, s * 0.72], fill="#1e2227")

    return _make(draw, size, color)


# ── Alert Cross ───────────────────────────────────────────────────
def icon_cross(size=16, color="#f87171"):
    def draw(d, s, c):
        w = max(2, int(s * 0.08))
        d.line([(s * 0.28, s * 0.28), (s * 0.72, s * 0.72)], fill=c, width=w)
        d.line([(s * 0.28, s * 0.72), (s * 0.72, s * 0.28)], fill=c, width=w)

    return _make(draw, size, color)


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Palette
BG = "#0f1117"
CARD_BG = "#1a1d26"
CARD_BORDER = "#2a2d38"
ACCENT_GOLD = "#f0c040"
ACCENT_BLUE = "#4a9eff"
ACCENT_GREEN = "#4ade80"
ACCENT_RED = "#f87171"
TEXT_WHITE = "#e2e4e9"
TEXT_DIM = "#6b7280"
TEXT_SEC = "#9ca3af"


# ── Battery color gradient (green → yellow → red) ───────────────────────────
def _lerp_rgb(c1, c2, t):
    """Linear interpolation between two RGB tuples (t in 0..1)."""
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
    )


def _battery_color(pct: int) -> str:
    """Map a battery percentage (0–100) to a smooth gradient hex color.

    100% → green, 50% → yellow, 0% → red. The tone transitions gradually as the
    level drops, so the ring never changes color abruptly.
    """
    pct = max(0, min(100, int(pct)))
    _GREEN = (74, 222, 128)   # #4ade80  (100%)
    _YELLOW = (250, 204, 21)  # #facc15  (50%)
    _RED = (248, 113, 113)    # #f87171  (0%)
    if pct >= 50:
        # green (100%) drifting toward yellow (50%)
        t = (100 - pct) / 50.0
        r, g, b = _lerp_rgb(_GREEN, _YELLOW, t)
    else:
        # yellow (50%) drifting toward red (0%)
        t = (50 - pct) / 50.0
        r, g, b = _lerp_rgb(_YELLOW, _RED, t)
    return f"#{int(round(r)):02x}{int(round(g)):02x}{int(round(b)):02x}"


class BatteryRing(tk.Canvas):
    """Lightweight canvas that draws a circular battery arc."""

    def __init__(self, master, size=180, **kw):
        super().__init__(
            master, width=size, height=size, bg=CARD_BG, highlightthickness=0, **kw
        )
        self._size = size
        self._pct = 0
        self._color = ACCENT_GREEN

    # ── public helpers ─────────────────────────────────────────────────
    def set_value(self, pct: int, color: str = ACCENT_GREEN):
        self._pct = max(0, min(100, pct))
        self._color = color
        self._draw()

    # ── internal draw ──────────────────────────────────────────────────
    def _draw(self):
        self.delete("all")
        s = self._size
        cx = cy = s // 2
        pad = 12
        r = (s - 2 * pad) // 2
        w = max(6, int(r * 0.16))

        # track
        self.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#2a2d38", width=w)
        # filled arc
        if self._pct > 0:
            extent = -self._pct * 3.6
            if extent <= -360:
                extent = -359.99
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
        # percentage text
        font_size = max(20, int(r * 0.52))
        self.create_text(
            cx,
            cy,
            text=f"{self._pct}%",
            fill=TEXT_WHITE,
            font=("Helvetica", font_size, "bold"),
        )


# ═══════════════════════════════════════════════════════════════════════════
# Main application
# ═══════════════════════════════════════════════════════════════════════════
class MchoseBatteryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MCHOSE V9 PRO")
        self.geometry("420x720")
        self.minsize(360, 620)
        self.configure(fg_color=BG)

        # ── state ─────────────────────────────────────────────────────
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

        # ── HID ───────────────────────────────────────────────────────
        self.hid = None
        self._init_hid()

        # ── UI ────────────────────────────────────────────────────────
        self._build_ui()

        # ── auto-poll thread ──────────────────────────────────────────
        self._stop = False
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

        # initial read
        self._refresh_system_audio()

    # ───────────────────────────────────────────────────────────────────
    # UI construction
    # ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # static main container
        self._main = ctk.CTkFrame(self, fg_color=BG)
        self._main.pack(fill="both", expand=True, padx=0, pady=0)
        self._main.columnconfigure(0, weight=1)

        self._build_header()
        self._build_volume_card()
        self._build_mic_card()
        self._build_eq_card()
        self._build_footer()

    # ── header ─────────────────────────────────────────────────────────
    def _build_header(self):
        frame = ctk.CTkFrame(
            self._main,
            fg_color=CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=CARD_BORDER,
        )
        frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        frame.columnconfigure(0, weight=1)

        # title
        ctk.CTkLabel(
            frame,
            text="MCHOSE V9 PRO",
            font=("Helvetica", 20, "bold"),
            text_color=ACCENT_GOLD,
        ).grid(row=0, column=0, pady=(14, 0))

        # firmware
        self._fw_label = ctk.CTkLabel(
            frame, text="", font=("Helvetica", 11), text_color=TEXT_DIM
        )
        self._fw_label.grid(row=1, column=0, pady=(0, 6))

        # battery ring
        self._ring = BatteryRing(frame, size=170)
        self._ring.grid(row=2, column=0, pady=(4, 4))

        # connection badge
        self._conn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._conn_frame.grid(row=3, column=0, pady=(2, 4))
        self._conn_icon_cv = ctk.CTkLabel(
            self._conn_frame, image=icon_headset(22, ACCENT_GREEN), text=""
        )
        self._conn_icon_cv.pack(side="left", padx=(0, 4))
        self._conn_text = ctk.CTkLabel(
            self._conn_frame,
            text="Desconectado",
            font=("Helvetica", 12, "bold"),
            text_color=TEXT_DIM,
        )
        self._conn_text.pack(side="left")

        # status pill
        self._status_label = ctk.CTkLabel(
            frame,
            text=" Fone não detectado",
            image=icon_cross(16, ACCENT_RED),
            compound="left",
            font=("Helvetica", 11, "bold"),
            text_color=ACCENT_RED,
            fg_color="#1e2227",
            corner_radius=10,
            padx=12,
            pady=4,
        )
        self._status_label.grid(row=4, column=0, pady=(4, 12))

    # ── volume card ────────────────────────────────────────────────────
    def _build_volume_card(self):
        card = self._make_card(row=1)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 0))
        vol_icon = ctk.CTkLabel(header, image=icon_speaker(22, ACCENT_BLUE), text="")
        vol_icon.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            header, text="Volume", font=("Helvetica", 13, "bold"), text_color=TEXT_WHITE
        ).pack(side="left")
        self._vol_pct = ctk.CTkLabel(
            header, text="50%", font=("Helvetica", 13), text_color=TEXT_SEC
        )
        self._vol_pct.pack(side="right")

        self._vol_slider = ctk.CTkSlider(
            card,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._on_vol_slide,
            button_color=ACCENT_BLUE,
            button_hover_color="#6ab4ff",
            progress_color=ACCENT_BLUE,
            button_length=18,
            button_corner_radius=9,
            height=18,
        )
        self._vol_slider.set(self.volume_level)
        self._vol_slider.pack(fill="x", padx=14, pady=(8, 14))
        # Reset drag flag on mouse release
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

    # ── microphone card ────────────────────────────────────────────────
    def _build_mic_card(self):
        card = self._make_card(row=2)

        # row 1: icon + label + mute switch
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 0))

        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left")
        self._mic_icon_cv = ctk.CTkLabel(
            left, image=icon_mic(22, ACCENT_GREEN), text=""
        )
        self._mic_icon_cv.pack(side="left", padx=(0, 6))
        self._mic_lbl = ctk.CTkLabel(
            left,
            text="Microfone",
            font=("Helvetica", 13, "bold"),
            text_color=TEXT_WHITE,
        )
        self._mic_lbl.pack(side="left")

        self._mic_switch = ctk.CTkSwitch(
            top,
            text="Mudo",
            onvalue=1,
            offvalue=0,
            command=self._on_mic_switch,
            font=("Helvetica", 11),
            button_color=ACCENT_RED if self.mic_muted else ACCENT_GREEN,
            button_hover_color="#fca5a5" if self.mic_muted else "#6ee8a0",
            progress_color=ACCENT_RED,
            text_color=TEXT_SEC,
        )
        self._mic_switch.pack(side="right")
        if self.mic_muted:
            self._mic_switch.select()

        # row 2: mic volume slider
        mic_vol_frame = ctk.CTkFrame(card, fg_color="transparent")
        mic_vol_frame.pack(fill="x", padx=14, pady=(8, 4))
        ctk.CTkLabel(
            mic_vol_frame,
            text="Volume Microfone",
            font=("Helvetica", 11),
            text_color=TEXT_SEC,
        ).pack(side="left")
        self._mic_pct = ctk.CTkLabel(
            mic_vol_frame, text="50%", font=("Helvetica", 11), text_color=TEXT_SEC
        )
        self._mic_pct.pack(side="right")

        self._mic_slider = ctk.CTkSlider(
            card,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._on_mic_slide,
            button_color=ACCENT_GREEN,
            button_hover_color="#6ee8a0",
            progress_color=ACCENT_GREEN,
            button_length=18,
            button_corner_radius=9,
            height=18,
        )
        self._mic_slider.set(self.mic_level)
        self._mic_slider.pack(fill="x", padx=14, pady=(0, 14))
        # Reset drag flag on mouse release
        self._mic_slider.bind(
            "<ButtonRelease-1>", lambda e: setattr(self, "_dragging_mic", False)
        )

    def _on_mic_switch(self):
        self.mic_muted = bool(self._mic_switch.get())
        color = ACCENT_RED if self.mic_muted else ACCENT_GREEN
        self._mic_icon_cv.configure(
            image=icon_mic_muted(22, color) if self.mic_muted else icon_mic(22, color)
        )
        self._mic_switch.configure(
            button_color=color,
            button_hover_color="#fca5a5" if self.mic_muted else "#6ee8a0",
        )
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

    # ── equalizer card ─────────────────────────────────────────────────
    def _build_eq_card(self):
        card = self._make_card(row=3)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 0))
        eq_icon = ctk.CTkLabel(top, image=icon_equalizer(20, ACCENT_GOLD), text="")
        eq_icon.pack(side="left", padx=(0, 6))
        self._eq_title = ctk.CTkLabel(
            top,
            text="Equalizador",
            font=("Helvetica", 13, "bold"),
            text_color=ACCENT_GOLD,
        )
        self._eq_title.pack(side="left")
        self._eq_hint = ctk.CTkLabel(
            top, text="", font=("Helvetica", 10), text_color=TEXT_DIM
        )
        self._eq_hint.pack(side="right")

        eq_frame = ctk.CTkFrame(card, fg_color="transparent")
        eq_frame.pack(fill="x", padx=14, pady=(8, 14))
        eq_frame.columnconfigure((0, 1, 2), weight=1)

        labels = ["Jogo 1", "Jogo 2", "Música"]
        self._eq_btns = []
        for i, txt in enumerate(labels):
            btn = ctk.CTkButton(
                eq_frame,
                text=txt,
                corner_radius=10,
                font=("Helvetica", 12, "bold"),
                height=36,
                fg_color="#1a1d26",
                hover_color="#252832",
                border_width=1,
                border_color=CARD_BORDER,
                text_color=TEXT_SEC,
                command=lambda m=i: self._change_eq(m),
            )
            btn.grid(row=0, column=i, sticky="ew", padx=4)
            self._eq_btns.append(btn)
        # EQ icon images
        self._eq_icon_imgs = [
            icon_gamepad(16, TEXT_SEC),
            icon_target(16, TEXT_SEC),
            icon_music(16, TEXT_SEC),
        ]
        for i in range(3):
            self._eq_btns[i].configure(image=self._eq_icon_imgs[i], compound="left")
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
                    fg_color=ACCENT_BLUE,
                    hover_color="#6ab4ff",
                    text_color="#ffffff",
                    border_color=ACCENT_BLUE,
                )
                ic_color = "#ffffff"
            elif enabled:
                btn.configure(
                    fg_color="#1a1d26",
                    hover_color="#252832",
                    text_color=TEXT_SEC,
                    border_color=CARD_BORDER,
                )
                ic_color = TEXT_SEC
            else:
                btn.configure(
                    fg_color="#15171e",
                    hover_color="#15171e",
                    text_color="#3a3d48",
                    border_color="#1e2028",
                )
                ic_color = "#3a3d48"
            if hasattr(self, "_eq_icon_imgs") and i < len(self._eq_icon_imgs):
                self._eq_icon_imgs[i] = eq_fns[i](16, ic_color)
                btn.configure(image=self._eq_icon_imgs[i])
        if not enabled:
            self._eq_hint.configure(text="somente 2.4G")
        else:
            self._eq_hint.configure(text="")

    # ── footer ─────────────────────────────────────────────────────────
    def _build_footer(self):
        self._footer = ctk.CTkLabel(
            self._main,
            text="MCHOSE V9 PRO Controller",
            font=("Helvetica", 10),
            text_color="#3a3d48",
        )
        self._footer.grid(row=4, column=0, pady=(4, 16))

    # ── card helper ────────────────────────────────────────────────────
    def _make_card(self, row):
        f = ctk.CTkFrame(
            self._main,
            fg_color=CARD_BG,
            corner_radius=14,
            border_width=1,
            border_color=CARD_BORDER,
        )
        f.grid(row=row, column=0, sticky="ew", padx=16, pady=6)
        return f

    # ═══════════════════════════════════════════════════════════════════
    # UI refresh (called from poll thread)
    # ═══════════════════════════════════════════════════════════════════
    def _refresh_ui(self):
        # battery color
        bat = self.battery_level
        bcolor = _battery_color(bat)

        self._ring.set_value(bat if self.connected else 0, bcolor)

        # connection status
        if self.connected:
            mode = self.connection_mode or ""
            icon_color = ACCENT_BLUE if mode == "Bluetooth" else ACCENT_GREEN
            if mode == "Bluetooth":
                self._conn_icon_cv.configure(image=icon_bluetooth(22, icon_color))
            else:
                self._conn_icon_cv.configure(image=icon_wifi(22, icon_color))
            self._conn_text.configure(text=mode, text_color=TEXT_WHITE)

            status_map = {
                0x02: ("Em uso", icon_battery_status(16, ACCENT_GREEN), ACCENT_GREEN),
                0x03: ("Carregando...", icon_lightning(16, "#f59e0b"), "#f59e0b"),
                0x04: ("Carregado (100%)", icon_check(16, ACCENT_GREEN), ACCENT_GREEN),
                0x1A: ("Modo de Suspensão", icon_moon(16, TEXT_DIM), TEXT_DIM),
            }
            if mode == "2.4G":
                mapped = status_map.get(self.status_code)
                if mapped:
                    txt, img, txt_color = mapped
                else:
                    txt, img, txt_color = (
                        f"Status: {hex(self.status_code)}",
                        icon_battery_status(16, ACCENT_GREEN),
                        ACCENT_GREEN,
                    )
            else:
                txt, img, txt_color = (
                    "Bluetooth conectado",
                    icon_bluetooth(16, ACCENT_BLUE),
                    ACCENT_BLUE,
                )

            # Badge style with native Pillow status icon (compound="left")
            self._status_label.configure(
                text=f" {txt}", image=img, text_color=txt_color, fg_color="#1e2227"
            )
        else:
            self._conn_icon_cv.configure(image=icon_wifi(22, "#3a3d48"))
            self._conn_text.configure(text="Desconectado", text_color=TEXT_DIM)
            self._status_label.configure(
                text=" Fone não detectado",
                image=icon_cross(16, ACCENT_RED),
                text_color=ACCENT_RED,
                fg_color="#1e2227",
            )
            self.fw_dongle = ""
            self.fw_headset = ""

        # firmware
        if self.connected:
            fw = f"FW: {self.fw_dongle or '--'} / HS: {self.fw_headset or '--'}"
        else:
            fw = ""
        self._fw_label.configure(text=fw)

        # volume slider (skip if user is dragging)
        if not self._vol_slider.get() == self.volume_level:
            self._vol_slider.set(self.volume_level)
        self._vol_pct.configure(text=f"{self.volume_level}%")

        # mic
        self._mic_slider.set(self.mic_level)
        self._mic_pct.configure(text=f"{self.mic_level}%")
        if self.mic_muted:
            if not self._mic_switch.get():
                self._mic_switch.select()
            self._mic_icon_cv.configure(image=icon_mic_muted(22, ACCENT_RED))
            self._mic_switch.configure(
                button_color=ACCENT_RED, button_hover_color="#fca5a5"
            )
        else:
            if self._mic_switch.get():
                self._mic_switch.deselect()
            self._mic_icon_cv.configure(image=icon_mic(22, ACCENT_GREEN))
            self._mic_switch.configure(
                button_color=ACCENT_GREEN, button_hover_color="#6ee8a0"
            )

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
            # battery query
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
            # eq query
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
            # 1. try 2.4G HID
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
                # 2. try bluetooth
                ok_bt, bat_bt = self._query_bluetooth()
                if ok_bt:
                    self.connected = True
                    self.connection_mode = "Bluetooth"
                    self.battery_level = bat_bt
                    self.status_code = 0x02
                else:
                    self.connected = False
                    self.connection_mode = None

            # refresh system audio state
            self._refresh_system_audio()

            # update UI on main thread
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

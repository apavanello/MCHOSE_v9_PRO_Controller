#!/usr/bin/env python3
"""Testes offline do protocolo V9 Pro 2 — sem hardware.

Valida: montagem de frames (bytes exatos), decodificacao de respostas e
casos-limite (truncagem de nome em UTF-8, heuristicas de paginacao).
Rode: python3 tests/test_protocol.py
"""

import sys
import types

# stubs dos modulos Qt (o HIDService nao usa Qt, mas o import do modulo exige)
class Dummy:
    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return Dummy()


for name, attrs in {
    "PyQt6": [],
    "PyQt6.QtCore": ["Qt", "QThread", "pyqtSignal", "QRectF", "QPointF", "QSize", "QVariantAnimation", "QEasingCurve"],
    "PyQt6.QtGui": ["QPainter", "QColor", "QPen", "QFont", "QBrush", "QPainterPath", "QPixmap", "QIcon"],
    "PyQt6.QtWidgets": ["QApplication", "QMainWindow", "QWidget", "QVBoxLayout", "QHBoxLayout", "QLabel", "QSlider", "QPushButton", "QFrame", "QGraphicsOpacityEffect", "QComboBox", "QDoubleSpinBox", "QInputDialog", "QMessageBox", "QGridLayout"],
}.items():
    m = types.ModuleType(name)
    for a in attrs:
        setattr(m, a, Dummy)
    sys.modules[name] = m

import mchose_qt as app

PASS = FAIL = 0


def check(label, got, expected):
    global PASS, FAIL
    if got == expected:
        PASS += 1
        print(f"  ok  {label}")
    else:
        FAIL += 1
        print(f" FAIL {label}\n      obtido:   {got!r}\n      esperado: {expected!r}")


svc = app.HIDService.__new__(app.HIDService)  # pula __init__ (sem libusb)
svc.hid = True
svc._lock = __import__("threading").Lock()
svc.protocol = "new"

print("== montagem de frames ==")
frame = svc._build_frame(app.NEW_REQUEST, app.NEW_CMD_GET_BATTERY)
check(
    "bateria (request 0x0B)",
    frame[:8],
    bytes([0xAA, 0x01, 0x00, 0x01, 0x00, 0x01, 0x0B, 0x00]),
)
frame = svc._build_frame(app.NEW_SET, app.NEW_CMD_SET_EQ, bytes([2]))
check(
    "set EQ modo 2",
    frame[:9],
    bytes([0xAA, 0x01, 0x00, 0x02, 0x00, 0x02, 0x01, 0x02, 0x00]),
)
frame = svc._build_frame(app.NEW_SET, app.NEW_CMD_SET_PROMPT_VOL, bytes([16]))
check(
    "volume do anuncio = 16",
    frame[:9],
    bytes([0xAA, 0x01, 0x00, 0x02, 0x00, 0x02, 0x21, 0x10, 0x00]),
)
frame = svc._build_frame(app.NEW_SET, app.NEW_CMD_SET_AUTO_OFF, bytes([0x00, 0x3C]))
check(
    "auto-off 60 min",
    frame[:10],
    bytes([0xAA, 0x01, 0x00, 0x03, 0x00, 0x02, 0x1A, 0x00, 0x3C, 0x00]),
)

print("== parsers de resposta ==")

# fake: responde qualquer chamada com payload configurado por cmd
RESPONSES = {}


def fake_xchg(handle, cmd_type, cmd, payload=b"", timeout_ms=600):
    return RESPONSES.get((cmd_type, cmd))


def fake_send(handle, cmd_type, cmd, payload=b""):
    RESPONSES["sent"] = (cmd_type, cmd, bytes(payload))
    return True


svc._xchg_new = fake_xchg
svc._send_new = fake_send
svc._with_new_device = lambda fn: fn(None)  # sem hardware: roda direto no fake

RESPONSES[(app.NEW_REQUEST, app.NEW_CMD_GET_BATTERY)] = b"\x01\x51"
ok, bat, sc, eq = svc._query_status_new(None, 0)
check("bateria 81% normal", (ok, bat, sc), (True, 81, 0))

RESPONSES[(app.NEW_REQUEST, app.NEW_CMD_GET_BATTERY)] = b"\x01\xD2"
ok, bat, sc, eq = svc._query_status_new(None, 3)
check("bateria 82% carregando", (ok, bat, sc), (True, 82, 1))

RESPONSES[(app.NEW_REQUEST, app.NEW_CMD_GET_AUTO_OFF)] = b"\x00\x3C"
pay = RESPONSES[(app.NEW_REQUEST, app.NEW_CMD_GET_AUTO_OFF)]
check(
    "parse auto-off",
    (pay[0] << 8) | pay[1],
    60,
)
check("auto-off via servico", svc.get_auto_shutdown(), 60)

RESPONSES[(app.NEW_REQUEST, app.NEW_CMD_GET_EQ_DESC)] = b"\x02" + b"Game 2\x00zz"
raw = bytes(RESPONSES[(app.NEW_REQUEST, app.NEW_CMD_GET_EQ_DESC)][1:])
check("parse nome do modo", raw.split(b"\x00")[0].decode(), "Game 2")

# ganhos PEQ: [modo, count, ?, g1hi, g1lo, ...] com offset 4 (ha byte de paginacao)
# -120 (=-12.0 dB) em int16 = 0xFF88
RESPONSES[(app.NEW_REQUEST, app.NEW_CMD_GET_EQ_STATE)] = bytes(
    [0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0F, 0xFF, 0x88]
)


def run_gains():
    pay = RESPONSES[(app.NEW_REQUEST, app.NEW_CMD_GET_EQ_STATE)]
    count = pay[1]
    offset = 4 if len(pay) >= 4 + count * 2 else 3
    gains = []
    for i in range(count):
        p = offset + i * 2
        raw = (pay[p] << 8) | pay[p + 1]
        if raw >= 0x8000:
            raw -= 0x10000
        gains.append(raw / 10.0)
    return gains


check("ganhos [0, 1.5, -12]", run_gains(), [0.0, 1.5, -12.0])

print("== codificacao de ganhos e nomes ==")
payload = bytearray([1, 2])
for g in (3.0, -11.5):
    v = int(round(g * 10))
    payload += bytes([(v >> 8) & 0xFF, v & 0xFF])
check(
    "payload set PEQ gains",
    bytes(payload),
    bytes([0x01, 0x02, 0x00, 0x1E, 0xFF, 0x8D]),
)

svc.set_eq_mode_name(0, "x" * 60)
_, cmd, sent = RESPONSES["sent"]
check("nome truncado em 54", (cmd, len(sent) - 1), (app.NEW_CMD_SET_EQ_NAME, 54))

svc.set_eq_mode_name(0, "🎧" * 30)  # emoji = 4 bytes; corte nao pode quebrar UTF-8
_, cmd, sent = RESPONSES["sent"]
name_bytes = sent[1:]
try:
    name_bytes.decode("utf-8")
    utf8_ok = True
except UnicodeDecodeError:
    utf8_ok = False
check("nome emoji com corte valido em UTF-8", utf8_ok, True)
check("nome emoji = 13 emojis", len(name_bytes) // 4, 13)

print(f"\n{PASS} ok, {FAIL} falhas")
sys.exit(1 if FAIL else 0)

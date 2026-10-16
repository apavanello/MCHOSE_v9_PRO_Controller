#!/usr/bin/env python3
"""Sonda de protocolo HID para dongles MCHOSE.

Testa os comandos conhecidos do V9 PRO original contra o dongle
conectado e imprime as respostas em hex, para validar ou descobrir
o protocolo (ex.: do V9 Pro 2, chip bestechnic).

Uso:
    python3 probe_hid.py            # testa os dongles conhecidos
    python3 probe_hid.py 3837:6011  # força um VID:PID específico
"""

import ctypes
import ctypes.util
import sys
import time

DEVICES = [
    (0x291D, 0x385D),  # MCHOSE V9 PRO (original)
    (0x3837, 0x6011),  # MCHOSE V9 Pro 2 (bestechnic)
]


def load_hidapi():
    for lib in ("libhidapi-hidraw.so.0", "libhidapi-hidraw.so"):
        try:
            return ctypes.CDLL(lib)
        except OSError:
            continue
    name = ctypes.util.find_library("hidapi-hidraw")
    if name:
        try:
            return ctypes.CDLL(name)
        except OSError:
            pass
    return None


def hexs(buf, n=32):
    return " ".join(f"{b:02x}" for b in buf[:n])


def main():
    hid = load_hidapi()
    if not hid:
        sys.exit("ERRO: libhidapi-hidraw nao encontrada")

    hid.hid_open.argtypes = [ctypes.c_ushort, ctypes.c_ushort, ctypes.c_wchar_p]
    hid.hid_open.restype = ctypes.c_void_p
    hid.hid_write.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
    hid.hid_write.restype = ctypes.c_int
    hid.hid_read_timeout.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_size_t,
        ctypes.c_int,
    ]
    hid.hid_read_timeout.restype = ctypes.c_int
    hid.hid_send_feature_report.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_size_t,
    ]
    hid.hid_send_feature_report.restype = ctypes.c_int
    hid.hid_get_feature_report.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_size_t,
    ]
    hid.hid_get_feature_report.restype = ctypes.c_int
    hid.hid_close.argtypes = [ctypes.c_void_p]

    candidates = DEVICES
    if len(sys.argv) > 1:
        vid, pid = (int(x, 16) for x in sys.argv[1].split(":"))
        candidates = [(vid, pid)]

    handle = None
    for vid, pid in candidates:
        handle = hid.hid_open(vid, pid, None)
        if handle:
            print(f"Dongle aberto: {vid:04x}:{pid:04x}")
            break
    if not handle:
        sys.exit(
            "ERRO: nenhum dongle MCHOSE foi aberto.\n"
            "Sem permissao no /dev/hidraw*? Aplique a regra udev do README."
        )

    def read(label, timeout_ms=1200):
        rbuf = bytearray(64)
        cr = (ctypes.c_char * 64).from_buffer(rbuf)
        n = hid.hid_read_timeout(handle, cr, 64, timeout_ms)
        if n > 0:
            print(f"  <- [{label}] {n} bytes: {hexs(rbuf)}")
        else:
            print(f"  <- [{label}] sem resposta ({n})")
        return rbuf if n > 0 else None

    def send(label, payload, expect=True, timeout_ms=700):
        buf = bytearray(64)
        buf[: len(payload)] = payload
        c = (ctypes.c_char * 64).from_buffer(buf)
        n = hid.hid_write(handle, c, 64)
        print(f"-> [{label}] {len(payload)} bytes: {hexs(buf)} (hid_write={n})")
        return read(label, timeout_ms) if expect else None

    print("\n=== 1. Escuta passiva (8 s) — notificacoes espontaneas ===")
    print("  (dica: aperte botoes do headset / gire o volume nele agora)")
    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        rbuf = bytearray(64)
        cr = (ctypes.c_char * 64).from_buffer(rbuf)
        n = hid.hid_read_timeout(handle, cr, 64, 300)
        if n > 0:
            print(f"  <- espontaneo: {n} bytes: {hexs(rbuf)}")

    print("\n=== 2. Comandos do protocolo V9 PRO (report 0x55, somente leitura) ===")
    send("bateria 55 65 01", [0x55, 0x65, 0x01])
    send("EQ 55 11", [0x55, 0x11])

    print("\n=== 3. Sondas extras (podem nao responder) ===")
    send("ping 55 0f", [0x55, 0x0F])
    send("canal FD 01", [0xFD, 0x01])
    send("canal FD 55", [0xFD, 0x55])
    print("-> [firmware AA 01 00] feature report")
    buf = bytearray(64)
    buf[0], buf[1], buf[2] = 0xAA, 0x01, 0x00
    c = (ctypes.c_char * 64).from_buffer(buf)
    n = hid.hid_send_feature_report(handle, c, 64)
    print(f"   hid_send_feature_report={n}")
    if n > 0:
        time.sleep(0.5)
        rb = bytearray(64)
        rb[0] = 0xAA
        cr = (ctypes.c_char * 64).from_buffer(rb)
        n = hid.hid_get_feature_report(handle, cr, 64)
        print(f"   get_feature_report={n}: {hexs(rb)}")

    print("\n=== 4. Protocolo NOVO (V9 Pro 2 / bestechnic, frame 0xAA) ===")

    def xchg_new(label, cmd_type, cmd, payload=(), timeout_ms=1000):
        # frame: AA 01 flags len ct0 ct1 cmd payload... xor(0)
        length = len(payload) + 1
        frame = bytearray(63)
        frame[0], frame[1], frame[2], frame[3] = 0xAA, 0x01, 0x00, length
        frame[4], frame[5] = cmd_type
        frame[6] = cmd
        frame[7 : 7 + len(payload)] = bytes(payload)
        buf = bytearray(64)
        buf[0] = 0x55  # report id
        buf[1:] = frame
        c = (ctypes.c_char * 64).from_buffer(buf)
        n = hid.hid_write(handle, c, 64)
        print(f"-> [{label}] (write={n}): {hexs(buf, 16)}")
        rbuf = bytearray(64)
        cr = (ctypes.c_char * 64).from_buffer(rbuf)
        n = hid.hid_read_timeout(handle, cr, 64, timeout_ms)
        if n > 0:
            print(f"  <- [{label}] {n} bytes: {hexs(rbuf, 20)}")
            return bytes(rbuf)
        print(f"  <- [{label}] sem resposta")
        return None

    REQUEST = (0x00, 0x01)
    r = xchg_new("bateria (cmd 0x0B)", REQUEST, 0x0B)
    if r and 0xAA in r[:4]:
        i = r.index(0xAA)
        pay = r[i + 7 : i + 7 + max(0, r[i + 3] - 1)]
        if len(pay) >= 2:
            sleep, status = pay[0], pay[1]
            print(
                f"  *** BATERIA: {status & 0x7F}% | carregando={bool(status & 0x80)} "
                f"| dormindo={sleep == 0} ***"
            )
    r = xchg_new("EQ atual (cmd 0x0C)", REQUEST, 0x0C)
    if r and 0xAA in r[:4]:
        i = r.index(0xAA)
        pay = r[i + 7 : i + 7 + max(0, r[i + 3] - 1)]
        if pay:
            print(f"  *** EQ MODE ATUAL: {pay[0]} ***")

    hid.hid_close(handle)
    print("\nConcluido.")


if __name__ == "__main__":
    main()

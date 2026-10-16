#!/usr/bin/env python3
"""Varredura de comandos HID no canal 0x55 do dongle MCHOSE.

Envia 0x55 <cmd> <arg> para cmd em 0x00..0xFF e registra qualquer
resposta do dispositivo. Respostas indicam comandos "vivos" — o primeiro
passo para mapear o protocolo de um modelo novo.

Uso: python3 scan_hid.py [vid:pid]   (padrao: 3837:6011)
"""

import ctypes
import ctypes.util
import sys
import time

DEFAULT_DEV = (0x3837, 0x6011)


def load_hidapi():
    for lib in ("libhidapi-hidraw.so.0", "libhidapi-hidraw.so"):
        try:
            return ctypes.CDLL(lib)
        except OSError:
            continue
    return None


def main():
    vid, pid = DEFAULT_DEV
    if len(sys.argv) > 1:
        vid, pid = (int(x, 16) for x in sys.argv[1].split(":"))

    hid = load_hidapi()
    if not hid:
        sys.exit("ERRO: libhidapi-hidraw nao encontrada")

    hid.hid_open.argtypes = [ctypes.c_ushort, ctypes.c_ushort, ctypes.c_wchar_p]
    hid.hid_open.restype = ctypes.c_void_p
    hid.hid_write.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
    hid.hid_write.restype = ctypes.c_int
    hid.hid_read_timeout.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int,
    ]
    hid.hid_read_timeout.restype = ctypes.c_int
    hid.hid_close.argtypes = [ctypes.c_void_p]

    handle = hid.hid_open(vid, pid, None)
    if not handle:
        sys.exit(f"ERRO: nao abriu {vid:04x}:{pid:04x} (permissoes udev?)")
    print(f"Varrendo comandos em {vid:04x}:{pid:04x} (canal 0x55)...")

    found = 0
    for cmd in range(0x100):
        for arg in (0x00, 0x01):
            buf = bytearray(64)
            buf[0], buf[1], buf[2] = 0x55, cmd, arg
            c = (ctypes.c_char * 64).from_buffer(buf)
            if hid.hid_write(handle, c, 64) <= 0:
                print(f"! write falhou no cmd 0x{cmd:02x}")
                continue
            rbuf = bytearray(64)
            cr = (ctypes.c_char * 64).from_buffer(rbuf)
            n = hid.hid_read_timeout(handle, cr, 64, 60)
            if n > 0:
                hexs = " ".join(f"{b:02x}" for b in rbuf[: min(n, 24)])
                print(f"RESPOSTA cmd=0x{cmd:02x} arg=0x{arg:02x}: {hexs}")
                found += 1
                time.sleep(0.1)
    hid.hid_close(handle)
    print(f"\nConcluido: {found} respostas.")


if __name__ == "__main__":
    main()

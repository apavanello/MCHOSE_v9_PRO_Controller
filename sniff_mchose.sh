#!/bin/bash
# sniff_mchose.sh — captura o trafego USB do dongle MCHOSE (formato texto do usbmon)
#
# Uso:  sudo ./sniff_mchose.sh [duracao_segundos]     (padrao: 60)
#
# Enquanto captura: abra o hub da MCHOSE e navegue (bateria, EQ, configs)
# para o trafego ser gravado. Ctrl+C interrompe antes do tempo.
set -e

DUR=${1:-60}
OUT="$PWD/mchose_usb_sniff.txt"
DEV=${DEV:-3837:6011}

# descobre o barramento onde o dongle esta (fallback: 3)
BUS=$(lsusb | grep -i "$DEV" | awk '{print $2}' | head -1)
BUS=$((10#${BUS:-3}))

modprobe usbmon 2>/dev/null || true
MON=/sys/kernel/debug/usb/usbmon/${BUS}u

if [ ! -r "$MON" ]; then
    echo "ERRO: $MON nao legivel — rode com sudo." >&2
    exit 1
fi

echo "Capturando barramento USB $BUS por ${DUR}s -> $OUT"
echo "Use o hub da MCHOSE AGORA ( headset ligado em 2.4G ). Ctrl+C para parar."
echo "-------------------------------------------------------------"

rm -f "$OUT"
timeout --signal=INT "${DUR}" cat "$MON" | tee "$OUT" >/dev/null || true

chown "${SUDO_USER:-$USER}" "$OUT" 2>/dev/null || true
LINES=$(wc -l < "$OUT")
echo "-------------------------------------------------------------"
echo "Concluido: $LINES linhas em $OUT"

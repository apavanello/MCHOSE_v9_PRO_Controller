# MCHOSE V9 PRO Controller

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Qt6](https://img.shields.io/badge/PyQt6-6.0+-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![Wayland](https://img.shields.io/badge/Wayland-Hyprland-0055FF?style=for-the-badge)

O **MCHOSE V9 PRO Controller (`mchose_qt.py`)** é uma aplicação desktop nativa desenvolvida em Python e PyQt6 para gerenciamento e controle completo dos headsets sem fio **MCHOSE V9 PRO** e **MCHOSE V9 Pro 2** no Linux. O projeto oferece monitoramento de bateria em tempo real, controle de volume/microfone sincronizado com o sistema operacional, chaveamento de perfis de equalizador via comandos USB HID e suporte a conexões 2.4G e Bluetooth.

> **Suporte ao V9 Pro 2:** o app detecta automaticamente qual dongle está conectado (V9 PRO original ou V9 Pro 2, chip Bestechnic) e usa o protocolo correto para cada um. O utilitário `probe_hid.py` permite diagnosticar o dongle conectado (somente leitura — não altera nada no headset).

## Protocolos suportados

**V9 PRO (original, dongle `291d:385d`):** pacotes `[0x55, cmd, ...]` — bateria `55 65 01`, EQ `55 11` / `55 21 01 <modo>`, firmware via feature report `0xAA`.

**V9 Pro 2 (Bestechnic, dongle `3837:6011`):** frames de 63 bytes no report `0x55` com a estrutura:

```
[0]=0xAA  [1]=0x01  [2]=flags  [3]=len  [4:6]=tipo  [6]=cmd  [7:]=payload  [..]=xor
tipo: 00 01 (request/response) · 00 02 (set) · 00 04 (notify) · 00 06 (OTA)
cmd:  01 set EQ · 0B bateria · 0C EQ atual · 04 estado PEQ · 50 OTA query
bateria (payload de resposta): [acordado, status] — status&0x7F = %, bit7 = carregando
modos de EQ: 0=Jogo 1 · 1=Jogo 2 · 2=Jogo 3
```

Protocolo documentado por engenharia reversa do código do hub oficial (renderer WebHID em `cdn.mchose.com.cn`) — sem USB sniffing necessário.

## Stack Técnica

- **GUI & Linguagem:** Python 3, PyQt6 (Qt6 Native Controls & Custom QPainter Vector Widgets)
- **Comunicação USB HID:** `ctypes`, `libhidapi-hidraw.so` (Comunicação de baixo nível via pacotes de 64 bytes)
- **Suporte Bluetooth:** `dbus` / BlueZ (`org.bluez.Battery1`)
- **Integração de Áudio:** PipeWire (`wpctl`) e ALSA (`amixer`)

## Funcionalidades e Recursos

1. **Gauge de Bateria Animado (60 FPS)**
   - Anel circular personalizado renderizado via `QPainter` com interpolação suave (`QEasingCurve.OutCubic`).
   - Gradiente dinâmico de cores (Verde -> Amarelo -> Vermelho) baseado na carga da bateria e efeito de brilho (*glow*).

2. **Indicador de Conexão Híbrido**
   - Suporte a conexão via **2.4G Wireless Dongle** (USB HID) e **Bluetooth** (D-Bus / BlueZ).
   - Atualização automática de ícones e status de conexão conforme a interface ativa no headset.

3. **Controle de Volume e Microfone Sincronizado**
   - Sliders horizontais responsivos com animação de ajuste e botões pill vetoriais com suporte a Mute.
   - Sincronização bidirecional em tempo real com o servidor de áudio do Linux (PipeWire / ALSA).

4. **Perfis de Equalizador Hardware (EQ)**
   - Seleção dos perfis armazenados no DSP interno do headset (**Jogo 1**, **Jogo 2**, **Música**).
   - Proteção *thread-safe* (`threading.Lock`) para evitar colisão de pacotes no barramento USB.
   - **Opacidade:** Em conexão Bluetooth (onde o EQ de hardware não é suportado pelo firmware), o card de equalização fica opaco e exibe a indicação `somente 2.4G`.

5. **Design Nativo & Suporte Hyprland / Wayland**
   - Dimensionamento inteligente adaptado à altura dos cards sem desperdício de espaço vertical.
   - Compatível com gerenciadores de janela em grade (*Tiling Window Managers*) no Wayland.

## Como Executar o Projeto

### Pré-requisitos

- **Python 3.10+**
- **PyQt6**
- **libhidapi-hidraw** (para comunicação USB com o Dongle 2.4G)
- **python-dbus** (opcional, para leitura de bateria em conexões Bluetooth)
- **wireplumber** (`wpctl`) ou **alsa-utils** (`amixer`) (para integração de volume do áudio do sistema)

#### Instalação das Dependências

No **Arch Linux / Manjaro / Omarchy**:
```bash
sudo pacman -S python-pyqt6 hidapi python-dbus wireplumber alsa-utils
```

No **Ubuntu / Debian / Pop!_OS**:
```bash
sudo apt install python3-pyqt6 libhidapi-hidraw0 python3-dbus wireplumber alsa-utils
```

### Permissões USB HID (Opcional - Executar sem sudo)

Para permitir que a aplicação acesse o Dongle USB em modo de usuário sem necessitar de `sudo`, crie a regra udev em `/etc/udev/rules.d/99-mchose.rules`:

```udev
# MCHOSE V9 PRO (original)
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="291d", ATTRS{idProduct}=="385d", MODE="0666"

# MCHOSE V9 Pro 2 (chip Bestechnic)
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="3837", ATTRS{idProduct}=="6011", MODE="0666"
```

Em seguida, recarregue as regras de udev:
```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### Sondando o Protocolo HID (ferramenta de diagnóstico)

Se o app não reconhecer um novo modelo de headset, rode a sonda para verificar quais comandos o dongle aceita:

```bash
python3 probe_hid.py            # testa os dongles conhecidos
python3 probe_hid.py 3837:6011  # força um VID:PID específico
```

### Executando a Aplicação

Navegue até o diretório do projeto e inicie a interface:

```bash
python3 mchose_qt.py
```

### Criar Atalho no Menu de Aplicativos (Ubuntu / GNOME / Linux Desktop)

Para adicionar o aplicativo ao menu do sistema de forma genérica (independente de usuário ou caminho da pasta):

```bash
# 1. Torne o script executável
chmod +x mchose_qt.py

# 2. Crie o atalho .desktop registrando o caminho do diretório atual
cat <<EOF > ~/.local/share/applications/mchose-v9-pro.desktop
[Desktop Entry]
Type=Application
Name=MCHOSE V9 PRO
Comment=Status de bateria e controle do headset MCHOSE V9 PRO
Exec=python3 $(pwd)/mchose_qt.py
Icon=$(pwd)/icon.png
Path=$(pwd)
Terminal=false
Categories=Utility;Settings;AudioVideo;
Keywords=headset;mchose;battery;bateria;fone;
StartupWMClass=mchose_qt
EOF

# 3. Atualize o banco de dados de atalhos
update-desktop-database ~/.local/share/applications
```

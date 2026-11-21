# Setup on Linux (Ubuntu, Kali, Raspberry Pi OS)

Status: **not yet verified on hardware** — see the Linux validation issue. Update this
file with what actually worked.

bleak talks to **BlueZ** over D-Bus. No `sudo` needed for scanning/connecting once your
user can access BlueZ.

## 1. Bluetooth stack

```bash
sudo apt update
sudo apt install -y bluez
sudo systemctl enable --now bluetooth
sudo usermod -aG bluetooth "$USER"     # log out/in afterwards
bluetoothctl show                      # should list a controller, "Powered: yes"
```

If `Powered: no`: `bluetoothctl power on`. If blocked: `rfkill list` → `sudo rfkill unblock bluetooth`.

- **Kali:** the Bluetooth service is often disabled by default — `systemctl enable --now`
  matters. In a VM, pass the USB Bluetooth adapter through to the guest.
- **Raspberry Pi:** the built-in adapter works (Pi 3B+ / 4 / 5 / Zero 2 W). Prefer 64-bit OS.

## 2. uv and project

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/intruder1912/lego-boost.git && cd lego-boost
uv sync
uv run boost-scan
```

On Linux the address is the hub's **MAC address** (`00:16:53:…`), the same on every
Linux/Windows machine.

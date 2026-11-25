# Setup on Linux (Ubuntu, Kali, Raspberry Pi OS)

Status: **verified on Kali** (bare-metal laptop, 2026-11-22; see `docs/hardware-notes.md`).
Ubuntu and Raspberry Pi OS are not tested yet (#3).

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

- **Kali:** every step above was needed (service enable, `bluetooth` group, log out/in).
  The Bluetooth service is often disabled by default — `systemctl enable --now`
  matters. Without it `hubbit-scan` reports that BlueZ is not running
  (`Unit dbus-org.bluez.service not found`). In a VM, pass the USB Bluetooth adapter through to the guest.
- **Raspberry Pi:** the built-in adapter works (Pi 3B+ / 4 / 5 / Zero 2 W). Prefer 64-bit OS.

## 2. uv and project

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/intruder1912/hubbit.git && cd hubbit
uv sync
uv run hubbit-scan
```

Right after the hub was switched off and on again, BlueZ sometimes fails the first
connect ("failed to discover services"); the scripts then try once more by themselves. If a
connect still fails, wait a few seconds, press the green button and try again.

**Caution: Bluetooth on Linux can get flaky after broken connections** (the hub switched
off mid-session, many reconnects in a row). BlueZ then keeps a stale connection to the hub,
and new connects fail again and again, even from a fresh start. `journalctl -u bluetooth`
shows `Device 00:16:53:... is already connected` / `No matching connection for device`.
Older adapters (seen with a 2012 MacBook's Broadcom BCM20702) are hit hardest. Reset:

```bash
bluetoothctl disconnect 00:16:53:XX:XX:XX   # your hub's address
bluetoothctl remove 00:16:53:XX:XX:XX
sudo systemctl restart bluetooth
```

Then take the hub's batteries out for ~10 s, put them back, press the green button and
run `uv run experiments/02_hub_info.py`. Still failing: reboot the computer.

On Linux the address is the hub's **MAC address** (`00:16:53:…`), the same on every
Linux/Windows machine.

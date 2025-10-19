# PyQt5 Wireless ADB + scrcpy QR Pair & Mirror Tool

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](#) [![License](https://img.shields.io/badge/license-MIT-green)](#) [![scrcpy](https://img.shields.io/badge/scrcpy-required-orange)](#)

A small, aesthetic PyQt5 GUI that generates an ADB wireless-debugging QR code (Android 11+) and provides manual pairing / connect controls — then launches `scrcpy` to mirror your Android device over Wi‑Fi.

> Built for quickly pairing and mirroring devices on the same network. Perfect for demos, testing, and quick remote screen control.

---

## Preview

![Screenshot](./docs/f3d1ee83-a9da-417c-a032-b57ca4b01d67.png)

## Features

* Generates a valid ADB Wireless Debugging QR payload you can scan from **Settings → Developer options → Wireless debugging → Pair device with QR code**.
* Manual pairing flow (enter IP, pairing port, and pairing code) for devices that show pairing details.
* Connect-only flow (typical `adb connect IP:5555`) after pairing.
* One-click start of `scrcpy` for screen mirroring once connected.
* Auto-detects local IP and pre-fills common ports to make pairing faster.
* Lightweight: single Python file, minimal dependencies.

---

## Quick Demo

1. Launch the app.
2. On the phone: **Settings → Developer options → Wireless debugging → Pair device with QR code** and scan the QR shown in the app.
3. Or use Manual Pair: copy the IP, pairing port and code shown on the phone into the app and click **Manual Pair**.
4. Click **Connect Only** (target port usually `5555`).
5. Click **Start scrcpy** to mirror your phone.

---

## Requirements

* **Python 3.8+**
* `PyQt5`, `qrcode[pil]`, `pillow`
* `adb` (Android Platform Tools) in your `PATH` (`adb` command must be accessible)
* `scrcpy` in your `PATH`

### Recommended install (Unix/macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install PyQt5 qrcode[pil] pillow
# Ensure adb & scrcpy are installed and in PATH
```

### Recommended install (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install PyQt5 qrcode[pil] pillow
# Install platform-tools and scrcpy and add them to PATH
```

---

## Installation notes

* `adb` comes with Android SDK Platform Tools. Download and add to `PATH`: [https://developer.android.com/studio/releases/platform-tools](https://developer.android.com/studio/releases/platform-tools)
* `scrcpy` installation instructions: [https://github.com/Genymobile/scrcpy](https://github.com/Genymobile/scrcpy) (Homebrew, apt, choco, or manual binary)
* Verify both commands are available:

```bash
adb version
scrcpy --version
```

---

## Usage (run locally)

```bash
# from the directory containing the script
python wireless_adb_scrcpy_qr.py
```

> The GUI will open and show a QR code. You can also use the manual fields at the bottom to pair or connect.

### Manual terminal commands (what the GUI runs under the hood)

* Pairing (if you have pairing IP, port and code):

```bash
adb pair <IP>:<PORT> <PAIRING_CODE>
# Example
adb pair 192.168.1.102:39083 123456
```

* Connect after pairing (`5555` is standard):

```bash
adb connect 192.168.1.102:5555
```

* Start scrcpy for a specific device serial:

```bash
scrcpy -s 192.168.1.102:5555 --stay-awake
```

---

## How the QR payload works

The QR follows Android's ADB pairing schema:

```
WIFI:T:ADB;S:<name>;P:<password>;;
```

* `S` is the pairing *name* the app generates (random by default).
* `P` is the pairing *password/code*. Android's scanner consumes this and displays the IP/port/code on the phone.

The app also logs the exact payload so you can use `adb pair IP:PORT <password>` manually.

---

## UI guide

* **Regenerate QR** — creates a new random name / password payload. Rescan on phone.
* **Manual Pair** — use when your phone shows pairing details under *Pair device with pairing code*.
* **Connect Only** — use to connect to device after pairing (or if your device already allows `adb connect`).
* **Start scrcpy** — enabled after successful `adb connect`.
* **Log window** — shows adb / scrcpy output and errors for easy troubleshooting.

---

## Troubleshooting

* **`adb not found in PATH`**: install platform-tools and add `adb` to your PATH. Re-open the app after adjusting PATH.
* **`Pairing failed`**: check the pairing code, ensure the phone shows the same pairing port & code, and the device and PC are on the same network.
* **`Connection timed out` / `adb connect failed`**: confirm IP address and port, check firewall, and ensure Wireless debugging is enabled on the phone.
* **`scrcpy not found in PATH`**: install `scrcpy` and add it to PATH.
* If the device isn’t listed in `adb devices`, it’s not connected — try pairing again or connect the phone with a USB cable and `adb tcpip 5555`.
* **`target device rejects/refused connection (10061)`**: please where there is port 5555 replace it with the port number that is just below the device name section, you will see ip address & port use that port instead.
---

## Advanced / Packaging

* To bundle into a single executable, use `PyInstaller`:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed wireless_adb_scrcpy_qr.py
```



---

## Security & Privacy

* This tool only generates the QR payload and issues `adb pair` / `adb connect` commands. It does not exfiltrate data.
* Ensure you only connect to devices you own or have permission to access.

---

## Contributing

1. Fork the repo
2. Create a feature branch `feat/my-feature`
3. Open a pull request with a clear description


---

## License

MIT — see `LICENSE`.

---

## Credits

Inspired by `scrcpy` and ADB wireless debug flow. Built with ❤️ using PyQt5, scrcpy and wireless debugging by `Illusivehacks`.
Check out more projects in my github 

---


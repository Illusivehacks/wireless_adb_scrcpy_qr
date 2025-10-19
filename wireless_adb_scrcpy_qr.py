#!/usr/bin/env python3
"""
PyQt5 Wireless ADB + scrcpy QR Pair & Mirror Tool
-------------------------------------------------

What it does
- Shows a QR code that your Android device (Android 11+) can scan from
  Settings → Developer options → Wireless debugging → Pair device with QR code.
- Provides manual pairing option for quick connection
- Connects to the device over Wi‑Fi and launches scrcpy to mirror the screen.

Requirements
- Python 3.8+
- pip install: PyQt5 qrcode[pil] pillow
- platform-tools (adb) in PATH
- scrcpy in PATH (https://github.com/Genymobile/scrcpy)

Note
- QR payload uses the ADB pairing schema: WIFI:T:ADB;S:<name>;P:<password>;;
- Manual pairing option for quick connection
"""

from __future__ import annotations

import os
import random
import string
import subprocess
import sys
import re
import socket
from dataclasses import dataclass
from typing import Optional, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets
import qrcode


def rand_text(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


@dataclass
class PairingParams:
    name: str
    password: str

    @property
    def qr_payload(self) -> str:
        # Officially consumed by Android's Wireless Debugging scanner
        return f"WIFI:T:ADB;S:{self.name};P:{self.password};;"


class LogBuffer(QtCore.QObject):
    message = QtCore.pyqtSignal(str)

    def log(self, text: str) -> None:
        self.message.emit(text)
        print(text, flush=True)


class Worker(QtCore.QObject):
    update = QtCore.pyqtSignal(str)
    paired = QtCore.pyqtSignal(str, str)  # ip, port for connection
    connected = QtCore.pyqtSignal()
    scrcpyStarted = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)

    def __init__(self, logger: LogBuffer):
        super().__init__()
        self.logger = logger
        self._adb_ok = False
        self._scrcpy_proc: Optional[subprocess.Popen] = None
        self._connected_ip = ""
        self._connected_port = ""

    @QtCore.pyqtSlot()
    def check_adb(self):
        try:
            out = subprocess.check_output(["adb", "version"], stderr=subprocess.STDOUT, text=True)
            self.logger.log(out.strip())
            # ensure server is running
            subprocess.run(["adb", "start-server"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self._adb_ok = True
        except Exception as e:
            self._adb_ok = False
            self.error.emit("adb not found in PATH. Install platform-tools and ensure 'adb' is in PATH.")
            self.logger.log(str(e))

    @QtCore.pyqtSlot(str, str, str)
    def do_pair(self, ip: str, port: str, password: str):
        if not self._adb_ok:
            return
            
        target = f"{ip}:{port}"
        self.logger.log(f"Pairing with {target}…")
        
        try:
            # Try pairing with timeout
            proc = subprocess.run(
                ["adb", "pair", target, password], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            output = proc.stdout.strip() or proc.stderr.strip()
            self.logger.log(output)
            
            if proc.returncode == 0 and "successfully paired" in output.lower():
                # After pairing, we need to connect to the standard ADB port (5555)
                self.paired.emit(ip, "5555")
            else:
                self.error.emit("Pairing failed. Check the pairing code and try again.")
        except subprocess.TimeoutExpired:
            self.error.emit("Pairing timed out. Please try again.")
        except Exception as e:
            self.error.emit(f"adb pair error: {e}")

    def _try_connect(self, ip: str, port: str):
        """Try to connect to the device after pairing"""
        target = f"{ip}:{port}"
        self.logger.log(f"Connecting to {target}…")
        try:
            proc = subprocess.run(
                ["adb", "connect", target], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            output = proc.stdout.strip() or proc.stderr.strip()
            self.logger.log(output)
            
            if proc.returncode == 0 and "connected" in output.lower():
                self._connected_ip = ip
                self._connected_port = port
                self.connected.emit()
            else:
                self.error.emit("adb connect failed. Ensure Wireless debugging is ON and same Wi‑Fi.")
        except subprocess.TimeoutExpired:
            self.error.emit("Connection timed out. Please try again.")
        except Exception as e:
            self.error.emit(f"adb connect error: {e}")

    @QtCore.pyqtSlot(str, str)
    def do_connect(self, ip: str, port: str):
        if not self._adb_ok:
            return
            
        self._try_connect(ip, port)

    @QtCore.pyqtSlot()
    def start_scrcpy(self):
        try:
            # Check if any devices are connected
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')[1:]  # Skip first line
            connected_devices = [line.split('\t')[0] for line in lines if line.strip() and 'device' in line]
            
            if not connected_devices:
                self.error.emit("No devices connected. Please connect first.")
                return
            
            # Find the wireless device (TCP/IP connection)
            wireless_device = None
            for device in connected_devices:
                if device.startswith(self._connected_ip) or ':5555' in device:
                    wireless_device = device
                    break
            
            if not wireless_device:
                self.error.emit("Wireless device not found. Please connect first.")
                return
                
            # Launch scrcpy with the specific device serial
            args = ["scrcpy", "--stay-awake", "-s", wireless_device]
            self.logger.log(f"Starting scrcpy with device: {wireless_device}...")
            self._scrcpy_proc = subprocess.Popen(args)
            self.scrcpyStarted.emit()
        except FileNotFoundError:
            self.error.emit("scrcpy not found in PATH. Install scrcpy and ensure it is in PATH.")
        except Exception as e:
            self.error.emit(f"Failed to start scrcpy: {e}")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wireless ADB + scrcpy (QR)")
        self.setMinimumSize(880, 560)

        # Generate pairing params
        self.params = PairingParams(name=rand_text(5), password=rand_text(6))

        # UI
        self.qr_label = QtWidgets.QLabel()
        self.qr_label.setAlignment(QtCore.Qt.AlignCenter)
        self.qr_label.setStyleSheet("background:#111; padding:16px; border-radius:16px;")

        self.hint = QtWidgets.QLabel(
            "1) On phone: Settings → Developer options → Wireless debugging → Pair device with QR code\n"
            "2) Note the IP, pairing code, pairing port shown on your phone under the pair with pairing code\n"
            "3) Enter them below and click 'Manual Pair'\n"
            "4) After pairing, use 'Connect Only' with the same IP but port 5555 or the port in grey under device name section"
        )
        self.hint.setWordWrap(True)

        self.status = QtWidgets.QTextEdit()
        self.status.setReadOnly(True)

        # Manual pairing inputs
        self.ip_input = QtWidgets.QLineEdit()
        self.ip_input.setPlaceholderText("Enter IP address")
        self.port_input = QtWidgets.QLineEdit()
        self.port_input.setPlaceholderText("Enter pairing port")
        self.pairing_code_input = QtWidgets.QLineEdit()
        self.pairing_code_input.setPlaceholderText("Enter pairing code")
        
        # Connection inputs
        self.connect_ip_input = QtWidgets.QLineEdit()
        self.connect_ip_input.setPlaceholderText("IP for connection")
        self.connect_port_input = QtWidgets.QLineEdit()
        self.connect_port_input.setPlaceholderText("5555")
        
        # Buttons
        self.btn_regen = QtWidgets.QPushButton("Regenerate QR")
        self.btn_manual_pair = QtWidgets.QPushButton("Manual Pair")
        self.btn_connect = QtWidgets.QPushButton("Connect Only")
        self.btn_mirror = QtWidgets.QPushButton("Start scrcpy")
        self.btn_mirror.setEnabled(False)

        # Layout
        top = QtWidgets.QWidget()
        self.setCentralWidget(top)
        layout = QtWidgets.QGridLayout(top)
        
        # QR code section
        layout.addWidget(self.qr_label, 0, 0, 4, 1)
        layout.addWidget(self.hint, 0, 1)
        layout.addWidget(self.status, 1, 1, 3, 1)
        
        # Manual pairing section
        manual_layout = QtWidgets.QHBoxLayout()
        manual_layout.addWidget(QtWidgets.QLabel("Pair IP:"))
        manual_layout.addWidget(self.ip_input)
        manual_layout.addWidget(QtWidgets.QLabel("Pair Port:"))
        manual_layout.addWidget(self.port_input)
        manual_layout.addWidget(QtWidgets.QLabel("Code:"))
        manual_layout.addWidget(self.pairing_code_input)
        layout.addLayout(manual_layout, 4, 1)
        
        # Connection section
        connect_layout = QtWidgets.QHBoxLayout()
        connect_layout.addWidget(QtWidgets.QLabel("Connect IP:"))
        connect_layout.addWidget(self.connect_ip_input)
        connect_layout.addWidget(QtWidgets.QLabel("Connect Port:"))
        connect_layout.addWidget(self.connect_port_input)
        layout.addLayout(connect_layout, 5, 1)
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.btn_regen)
        btn_layout.addWidget(self.btn_manual_pair)
        btn_layout.addWidget(self.btn_connect)
        btn_layout.addWidget(self.btn_mirror)
        layout.addLayout(btn_layout, 6, 1)

        # Logging
        self.logger = LogBuffer()
        self.logger.message.connect(lambda s: self.status.append(s))

        # Worker
        self.worker = Worker(self.logger)
        self.thread = QtCore.QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.start()

        # Signals
        self.btn_regen.clicked.connect(self.regenerate_qr)
        self.btn_manual_pair.clicked.connect(self.manual_pair)
        self.btn_connect.clicked.connect(self.connect_only)
        self.btn_mirror.clicked.connect(lambda: QtCore.QMetaObject.invokeMethod(self.worker, "start_scrcpy"))

        self.worker.paired.connect(self.on_paired)
        self.worker.connected.connect(self.on_connected)
        self.worker.scrcpyStarted.connect(lambda: self.logger.log("scrcpy started"))
        self.worker.update.connect(self.status.append)
        self.worker.error.connect(self.on_error)

        # Prepare
        self.render_qr()
        QtCore.QMetaObject.invokeMethod(self.worker, "check_adb")
        
        # Try to auto-fill common IP patterns
        self.try_auto_detect_ip()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            self.thread.quit()
            self.thread.wait(1500)
        finally:
            super().closeEvent(event)

    def try_auto_detect_ip(self):
        """Try to auto-detect the local network IP"""
        try:
            # Get local IP address using socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Doesn't even have to be reachable
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                
                # Set a common IP pattern (replace last octet with common phone IPs)
                ip_parts = local_ip.split('.')
                ip_parts[3] = '102'  # Common phone IP ending
                suggested_ip = '.'.join(ip_parts)
                
                self.ip_input.setText(suggested_ip)
                self.connect_ip_input.setText(suggested_ip)
                self.port_input.setText("39083")  # Common pairing port
                self.connect_port_input.setText("5555")  # Common ADB port
                self.logger.log(f"Auto-detected network: {local_ip}. Suggested IP: {suggested_ip}")
            except Exception:
                self.logger.log("Could not auto-detect network IP. Please enter manually.")
            finally:
                s.close()
                
        except Exception:
            self.logger.log("Socket error. Please enter IP and port manually.")

    def render_qr(self):
        # Generate QR using qrcode (PIL Image)
        img = qrcode.make(self.params.qr_payload).convert("RGB")

        # Convert PIL Image → bytes
        data = img.tobytes("raw", "RGB")

        # Create QImage from bytes
        qimg = QtGui.QImage(
            data, img.size[0], img.size[1], 3 * img.size[0], QtGui.QImage.Format_RGB888
        )

        # Scale nicely for display
        pix = QtGui.QPixmap.fromImage(qimg).scaled(
            380, 380, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        )
        self.qr_label.setPixmap(pix)

        # Debug log
        self.logger.log(f"QR ready: {self.params.qr_payload}")
        self.logger.log(f"Manual pairing: adb pair IP:PORT {self.params.password}")

    def regenerate_qr(self):
        self.params = PairingParams(name=rand_text(5), password=rand_text(6))
        self.render_qr()
        self.logger.log("Regenerated QR. Tap 'Pair device with QR code' again on the phone and rescan.")

    def manual_pair(self):
        ip = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        pairing_code = self.pairing_code_input.text().strip() or self.params.password
        
        if not ip or not port:
            self.logger.log("❌ Please enter both IP and port")
            return
            
        self.logger.log(f"Attempting manual pairing with {ip}:{port}")
        QtCore.QMetaObject.invokeMethod(
            self.worker, 
            "do_pair", 
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, ip),
            QtCore.Q_ARG(str, port),
            QtCore.Q_ARG(str, pairing_code)
        )

    def connect_only(self):
        ip = self.connect_ip_input.text().strip()
        port = self.connect_port_input.text().strip()
        
        if not ip or not port:
            self.logger.log("❌ Please enter both IP and port")
            return
            
        self.logger.log(f"Attempting connection to {ip}:{port}")
        QtCore.QMetaObject.invokeMethod(
            self.worker, 
            "do_connect", 
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, ip),
            QtCore.Q_ARG(str, port)
        )

    def on_paired(self, ip: str, port: str):
        self.logger.log("✔ Paired with device")
        # Auto-fill the connection fields with the same IP but port 5555
        self.connect_ip_input.setText(ip)
        self.connect_port_input.setText(port)
        self.logger.log(f"Ready to connect to {ip}:{port}")
        self.logger.log("Click 'Connect Only' to establish the connection")

    def on_connected(self):
        self.logger.log("✔ Connected over Wi‑Fi. Ready to launch scrcpy…")
        self.btn_mirror.setEnabled(True)

    def on_error(self, msg: str):
        self.logger.log(f"❌ {msg}")


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
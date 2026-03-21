"""Read ESP32 sensor data over USB serial and forward it to the backend.

Run this script from the backend directory with:
    python serial_bridge.py
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timezone

import requests
import serial
from serial import SerialException
from serial.tools import list_ports

# Configure bridge constants so they are easy to update.
DEFAULT_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
RECONNECT_DELAY = 5
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/sensors/data")
SENSOR_DEVICE_ID = os.getenv("SENSOR_DEVICE_ID", "serial-bridge-esp32").strip() or "serial-bridge-esp32"
REQUEST_TIMEOUT = 30
MIN_SEND_INTERVAL = 5  # seconds between POSTs to avoid overwhelming the backend

# Compile the exact sensor-line regex once for reuse.
SENSOR_PATTERN = re.compile(
    r"Temp(?:erature)?:\s*([\d.]+).*?Humidity:\s*([\d.]+).*?Soil(?: Moisture)?:\s*([\d.]+)"
)

# Match common ESP32 USB-to-serial adapter identifiers.
ESP32_PORT_KEYWORDS = (
    "cp210",
    "cp210x",
    "silicon labs",
    "ch340",
    "wch",
)


# Configure logging once for readable bridge output.
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# Search connected serial ports for a likely ESP32 adapter.
def detect_esp32_port() -> str | None:
    for port in list_ports.comports():
        port_details = " ".join(
            filter(
                None,
                [
                    port.device,
                    port.description,
                    port.manufacturer,
                    port.product,
                    port.hwid,
                ],
            )
        ).lower()
        if any(keyword in port_details for keyword in ESP32_PORT_KEYWORDS):
            return port.device
    return None


# Parse a serial line into sensor floats when it matches the expected format.
def parse_sensor_line(line: str) -> tuple[float, float, float] | None:
    match = SENSOR_PATTERN.search(line)
    if match is None:
        return None
    temperature, humidity, soil_moisture = match.groups()
    return float(temperature), float(humidity), float(soil_moisture)


# Build the backend payload with a UTC ISO 8601 timestamp.
def build_payload(temperature: float, humidity: float, soil_moisture: float) -> dict[str, float | str]:
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "device_id": SENSOR_DEVICE_ID,
        "temperature": temperature,
        "humidity": humidity,
        "soil_moisture": soil_moisture,
        "timestamp": timestamp,
    }


# Post a parsed sensor payload to the FastAPI backend.
def post_sensor_payload(payload: dict[str, float | str]) -> None:
    try:
        response = requests.post(BACKEND_URL, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.RequestException:
        logger.exception("[ERROR] Failed to POST sensor payload to backend")
        return

    if response.status_code in (200, 201):
        logger.info(
            "[OK] temperature=%s humidity=%s soil_moisture=%s",
            payload["temperature"],
            payload["humidity"],
            payload["soil_moisture"],
        )
        return

    logger.error(
        "[ERROR] Backend returned status=%s body=%s",
        response.status_code,
        response.text.strip(),
    )


# Read serial lines continuously until the connection is interrupted.
def listen_for_sensor_data(port: str) -> None:
    with serial.Serial(port, BAUD_RATE, timeout=1) as connection:
        logger.info("[BRIDGE] Connecting to backend at: %s", BACKEND_URL)
        logger.info("[BRIDGE] Using sensor device ID: %s", SENSOR_DEVICE_ID)
        logger.info("[BRIDGE] Sending every %s seconds", MIN_SEND_INTERVAL)
        logger.info("[BRIDGE] Listening for sensor data...")

        last_send_time = 0

        while True:
            # Decode the next serial line, replacing malformed bytes instead of crashing.
            raw_line = connection.readline().decode("utf-8", errors="replace").strip()

            # Skip blank serial output while waiting for the next reading.
            if not raw_line:
                continue

            # Parse valid sensor readings and log unexpected output appropriately.
            parsed_values = parse_sensor_line(raw_line)
            if parsed_values is None:
                if "error" in raw_line.lower():
                    logger.warning("[WARN] %s", raw_line)
                continue

            temperature, humidity, soil_moisture = parsed_values

            # Throttle sends to avoid overwhelming the backend.
            now = time.time()
            if now - last_send_time < MIN_SEND_INTERVAL:
                continue

            payload = build_payload(temperature, humidity, soil_moisture)
            post_sensor_payload(payload)
            last_send_time = now


# Keep retrying port detection and serial connection so the bridge self-recovers.
def run_bridge() -> None:
    logger.info("[BRIDGE] Starting serial bridge...")

    while True:
        logger.info("[BRIDGE] Scanning for ESP32 on available ports...")
        port = detect_esp32_port()

        if port is None:
            port = DEFAULT_PORT
            logger.info("[BRIDGE] Auto-detection failed. Using default port: %s", port)
            logger.info("[BRIDGE] If this is wrong, update DEFAULT_PORT in serial_bridge.py")
        else:
            logger.info("[BRIDGE] Found ESP32 on port: %s", port)

        try:
            listen_for_sensor_data(port)
        except SerialException:
            logger.exception("[ERROR] Serial port unavailable or disconnected: %s", port)
        except Exception:
            logger.exception("[ERROR] Unexpected bridge failure")

        logger.info("[BRIDGE] Reconnecting in %s seconds...", RECONNECT_DELAY)
        time.sleep(RECONNECT_DELAY)


# Run the reconnecting bridge loop when executed as a script.
if __name__ == "__main__":
    run_bridge()

#!/usr/bin/env python3
import os
import sys
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
import requests
import time
import traceback
import subprocess
import paho.mqtt.client as mqtt

# --- Required env vars ---
REQUIRED_ENV = [
    "SAVE_DIR",
    "ERROR_DIR",
    "MQTT_BROKER",
    "MQTT_PORT",
    "MQTT_TOPIC_TRIGGER",
    "MQTT_TOPIC_STATUS",
    "TLS_VERIFY",
    "SNAPSHOT_MODE"
]

missing = [var for var in REQUIRED_ENV if var not in os.environ]
if missing:
    sys.exit(f"Missing required environment variables: {', '.join(missing)}")

# --- Configuration from env ---
SAVE_DIR = Path(os.environ["SAVE_DIR"])
ERROR_DIR = Path(os.environ["ERROR_DIR"])
MQTT_BROKER = os.environ["MQTT_BROKER"]
MQTT_PORT = int(os.environ["MQTT_PORT"])
MQTT_USER = os.environ.get("MQTT_USER")
MQTT_PASS = os.environ.get("MQTT_PASS")
MQTT_TOPIC_TRIGGER = os.environ["MQTT_TOPIC_TRIGGER"]
MQTT_TOPIC_STATUS = os.environ["MQTT_TOPIC_STATUS"]
TLS_VERIFY = os.environ["TLS_VERIFY"] not in ("0", "false", "False", "")
QOS = int(os.environ.get("QOS", "1"))
CLIENT_ID = os.environ.get("CLIENT_ID", f"snapshotter-{int(time.time())}")
SNAPSHOT_MODE = os.environ["SNAPSHOT_MODE"].lower()  # "web" vagy "rtsp"

# Kamera adatok
CAMERA_USER = os.environ.get("CAMERA_USER")
CAMERA_PASS = os.environ.get("CAMERA_PASS")
CAMERA_IP = os.environ.get("CAMERA_IP")
SNAPSHOT_URL_TEMPLATE = os.environ.get("SNAPSHOT_URL_TEMPLATE")
RTSP_URL = os.environ.get("RTSP_URL")

# --- Logging setup ---
SAVE_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

log_level = os.environ.get("LOG_LEVEL", "INFO")
logger = logging.getLogger("snapshotter")
logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(console_handler)

error_log_file = ERROR_DIR / "error.log"
error_handler = logging.FileHandler(error_log_file, encoding="utf-8")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(error_handler)

# MQTT client
client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)
if MQTT_USER:
    client.username_pw_set(MQTT_USER, MQTT_PASS)

# --- Snapshot functions ---
def build_snapshot_url():
    if not SNAPSHOT_URL_TEMPLATE:
        raise RuntimeError("SNAPSHOT_URL_TEMPLATE is not set")
    return SNAPSHOT_URL_TEMPLATE.format(ip=CAMERA_IP, user=CAMERA_USER, password=CAMERA_PASS)

def take_snapshot_web(save_dir: Path, filename_prefix: str = "snapshot"):
    url = build_snapshot_url()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = save_dir / f"{filename_prefix}_{timestamp}.jpg"
    try:
        logger.info("Requesting snapshot from %s", url)
        resp = requests.get(url, stream=True, timeout=20, verify=TLS_VERIFY)
        resp.raise_for_status()
        with open(filename, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
        logger.info("Saved snapshot to %s", filename)
        return True, str(filename)
    except Exception as e:
        logger.error("Failed to take snapshot (web): %s", e)
        logger.error(traceback.format_exc())
        return False, str(e)

def take_snapshot_rtsp(save_dir: Path, filename_prefix: str = "snapshot"):
    if not RTSP_URL:
        return False, "RTSP_URL is not set"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = save_dir / f"{filename_prefix}_{timestamp}.jpg"
    try:
        logger.info("Capturing snapshot from RTSP stream %s", RTSP_URL)
        cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", RTSP_URL,
            "-frames:v", "1",
            "-q:v", "2",
            "-y", str(filename)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Saved snapshot to %s", filename)
        return True, str(filename)
    except Exception as e:
        logger.error("Failed to take snapshot (RTSP): %s", e)
        logger.error(traceback.format_exc())
        return False, str(e)

def take_snapshot(save_dir: Path, filename_prefix: str = "snapshot"):
    if SNAPSHOT_MODE == "rtsp":
        return take_snapshot_rtsp(save_dir, filename_prefix)
    elif SNAPSHOT_MODE == "web":
        return take_snapshot_web(save_dir, filename_prefix)
    else:
        return False, f"Unknown SNAPSHOT_MODE: {SNAPSHOT_MODE}"

# --- MQTT callbacks ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT broker %s:%s", MQTT_BROKER, MQTT_PORT)
        client.subscribe(MQTT_TOPIC_TRIGGER, qos=QOS)
        logger.info("Subscribed to trigger topic: %s", MQTT_TOPIC_TRIGGER)
    else:
        logger.error("MQTT connect failed with rc=%s", rc)

def publish_status(success: bool, info: str, request_payload=None):
    payload = {
        "timestamp": datetime.now().isoformat(),
        "success": bool(success),
        "info": info,
        "request_payload": request_payload
    }
    try:
        client.publish(MQTT_TOPIC_STATUS, json.dumps(payload), qos=QOS, retain=False)
        logger.debug("Published status to %s: %s", MQTT_TOPIC_STATUS, payload)
    except Exception as e:
        logger.error("Failed to publish status: %s", e)

def process_trigger_message(topic, payload_bytes):
    try:
        payload_text = payload_bytes.decode("utf-8") if payload_bytes else ""
    except Exception:
        payload_text = str(payload_bytes)

    logger.info("Trigger message received on %s: %s", topic, payload_text)

    def job():
        prefix = "snapshot"
        if payload_text:
            try:
                maybe = json.loads(payload_text)
                if isinstance(maybe, dict):
                    prefix = maybe.get("prefix", prefix)
            except Exception:
                pass
        ok, info = take_snapshot(SAVE_DIR, filename_prefix=prefix)
        publish_status(ok, info, request_payload=payload_text)

    threading.Thread(target=job, daemon=True).start()

def on_message(client, userdata, msg):
    try:
        process_trigger_message(msg.topic, msg.payload)
    except Exception as e:
        logger.error("Error in on_message: %s", e)
        logger.error(traceback.format_exc())

def on_disconnect(client, userdata, rc):
    logger.warning("Disconnected from MQTT (rc=%s). Will attempt reconnect.", rc)

# --- Main loop ---
def main():
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    while True:
        try:
            logger.info("Connecting to MQTT broker %s:%s ...", MQTT_BROKER, MQTT_PORT)
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            break
        except Exception as e:
            logger.error("MQTT connect error: %s — retrying in 5s", e)
            logger.error(traceback.format_exc())
            time.sleep(5)

    client.loop_start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()

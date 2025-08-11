
# Reolink Camera Snapshotter

A lightweight Python application that takes snapshots from a configured Reolink camera, triggered by MQTT messages. The application runs inside a Docker container for easy deployment.

---

## Features

- Connects to Reolink cameras to fetch snapshots on demand.
- Triggered remotely via MQTT messages.
- Publishes snapshot success/failure status back to MQTT.
- Configurable via environment variables.
- Encapsulated in a Docker container for portability.
- Supports TLS verification options for HTTPS connections.
- Logs errors to a separate folder for easy debugging.

---

## How It Works

- Listens to an MQTT topic (`MQTT_TOPIC_TRIGGER`) for trigger messages.
- On trigger, requests a snapshot image from the camera using the configured URL.
- Saves the snapshot image with a timestamped filename.
- Publishes the result (success/failure and details) on a status MQTT topic (`MQTT_TOPIC_STATUS`).
- Errors are logged both to console and an error log file.

---

## Requirements

- Reolink camera accessible via IP with snapshot URL API.
- MQTT broker accessible for publishing and subscribing.
- Docker environment (recommended) or Python 3.11+ to run natively.

---

## Configuration

All settings are controlled via environment variables. Below are the main ones:

| Variable              | Description                                        | Example                         |
|-----------------------|----------------------------------------------------|---------------------------------|
| `CAMERA_USER`          | Username for the camera                             | `admin`                        |
| `CAMERA_PASS`          | Password for the camera                             | `password123`                  |
| `CAMERA_IP`            | IP address or hostname of the camera               | `192.168.1.100`                |
| `SNAPSHOT_URL_TEMPLATE`| URL template to fetch snapshot; use `{ip}`, `{user}`, `{password}` placeholders | `https://{ip}/cgi-bin/api.cgi?cmd=Snap&channel=0&user={user}&password={password}` |
| `SAVE_DIR`             | Directory path to save snapshots                    | `/snapshots`                   |
| `ERROR_DIR`            | Directory path to save error logs                   | `/errors`                      |
| `MQTT_BROKER`          | MQTT broker hostname or IP                          | `mqtt.local`                   |
| `MQTT_PORT`            | MQTT broker port                                    | `1883`                        |
| `MQTT_USER`            | MQTT username (optional)                            |                               |
| `MQTT_PASS`            | MQTT password (optional)                            |                               |
| `MQTT_TOPIC_TRIGGER`   | MQTT topic to listen for snapshot triggers         | `camera/snapshot/trigger`      |
| `MQTT_TOPIC_STATUS`    | MQTT topic to publish snapshot status              | `camera/snapshot/status`       |
| `TLS_VERIFY`           | Whether to verify TLS certificates (1=true, 0=false)| `0`                          |
| `LOG_LEVEL`            | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`)| `INFO`                   |
| `QOS`                  | MQTT Quality of Service level (0, 1, or 2)          | `1`                           |

---

## Usage

### Run with Docker Compose

1. Clone or download the repository.
2. Customize `.env` file with your settings.
3. Run the container:

```bash
docker-compose up -d
```

Snapshots will be saved inside the mapped `./snapshots` directory on your host.

### Triggering a Snapshot

Send any MQTT message (can be empty) to the configured trigger topic, e.g.:

```bash
mosquitto_pub -h mqtt.local -t camera/snapshot/trigger -m ""
```

Optionally, send JSON to specify filename prefix:

```bash
mosquitto_pub -h mqtt.local -t camera/snapshot/trigger -m '{"prefix":"frontdoor"}'
```

### Status Messages

The snapshotter publishes JSON status messages on the configured status topic indicating success or failure:

```json
{
  "timestamp": "2025-08-11T20:40:00.123456",
  "success": true,
  "info": "/snapshots/snapshot_20250811_204000.jpg",
  "request_payload": "{"prefix":"frontdoor"}"
}
```

---

## Dockerfile

The container is based on `python:3.11-slim`, installs dependencies, and runs the `snapshotter.py` script. Volumes for snapshots and error logs are exposed.

---

## Development / Running Locally

1. Install Python 3.11+.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set required environment variables (or export from `.env`).
4. Run the script:

```bash
python snapshotter.py
```

---

## Logging

- Info and debug logs are output to console.
- Errors are additionally logged to `/errors/error.log` file (inside container or host volume).

---

## Notes

- Ensure the camera URL template matches your camera model and API.
- If using HTTPS and self-signed certificates, set `TLS_VERIFY=0` to skip verification.
- MQTT credentials are optional if your broker allows anonymous access.
- Filenames include timestamps and optional prefixes for easier organization.

---

## License

MIT License

---

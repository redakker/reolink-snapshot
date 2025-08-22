
# Reolink Camera Snapshotter

A lightweight Python service that captures snapshots from a Reolink camera triggered by MQTT messages.
Snapshots can be taken either directly from the camera's **HTTP snapshot API** or from the **RTSP stream** using `ffmpeg`.
The application runs in a Docker container for easy deployment.

---

## Features

- Capture snapshots from Reolink cameras via HTTP API or RTSP stream.
- Trigger snapshots remotely using MQTT messages.
- Publish success/error status to MQTT.
- Fully configurable via environment variables.
- Runs inside Docker.
- Option to disable SSL certificate verification.
- Error logging to file.

---

## How It Works

- The service subscribes to the MQTT topic defined in `MQTT_TOPIC_TRIGGER`.
- When a message is received:
  - **HTTP mode**: calls the camera’s HTTP snapshot API.
  - **RTSP mode**: uses `ffmpeg` to extract a single frame from the RTSP stream.
- Saves the image with a timestamped filename.
- Publishes the result (success/error) as JSON to the `MQTT_TOPIC_STATUS` topic.
- Logs errors both to console and to a logfile.

---

## Requirements

- Reolink camera with either HTTP API or RTSP stream available.
- MQTT broker.
- Docker environment (recommended) or Python 3.11+ with `ffmpeg` installed.

---

## Configuration

The service is configured via environment variables.
Two snapshot modes are available:

### 1. HTTP Snapshot API mode
| Variable                | Description                                        | Example |
|-------------------------|----------------------------------------------------|---------|
| `CAMERA_USER`           | Camera username                                    | `admin` |
| `CAMERA_PASS`           | Camera password                                    | `password123` |
| `CAMERA_IP`             | Camera IP address                                  | `192.168.1.50` |
| `SNAPSHOT_URL_TEMPLATE` | HTTP template for snapshot API                     | `https://{ip}/cgi-bin/api.cgi?cmd=Snap&channel=0&user={user}&password={password}` |

### 2. RTSP mode
| Variable      | Description                        | Example |
|---------------|------------------------------------|---------|
| `RTSP_URL`    | RTSP stream URL of the camera      | `rtsp://admin:password123@192.168.1.50:554/h264Preview_01_main` |

### Common variables
| Variable            | Description                     | Example |
|---------------------|---------------------------------|---------|
| `SNAPSHOT_MODE`     | Selects `http` or `rtsp` mode   | `http` or `rtsp` |
| `SNAPSHOT_PATH`     | Path to save snapshots          | `/snapshots` |
| `MQTT_HOST`         | MQTT broker host                | `mqtt.local` |
| `MQTT_PORT`         | MQTT broker port                | `1883` |
| `MQTT_USER`         | MQTT username                   | `mqttuser` |
| `MQTT_PASS`         | MQTT password                   | `mqttpass` |
| `MQTT_TOPIC_TRIGGER`| MQTT topic for trigger messages | `camera/snapshot/trigger` |
| `MQTT_TOPIC_STATUS` | MQTT topic for status messages  | `camera/snapshot/status` |
| `VERIFY_TLS`        | Verify SSL certificates         | `true` or `false` |

---

## Running with Docker

Example `docker-compose.yml`:

```yaml
version: '3.9'
services:
  snapshotter:
    image: snapshotter:latest
    container_name: reolink-snapshotter
    restart: unless-stopped
    environment:
      - SNAPSHOT_MODE=rtsp
      - RTSP_URL=rtsp://admin:password123@192.168.1.50:554/h264Preview_01_main
      - SNAPSHOT_PATH=/snapshots
      - MQTT_HOST=mqtt.local
      - MQTT_PORT=1883
      - MQTT_USER=mqttuser
      - MQTT_PASS=mqttpass
      - MQTT_TOPIC_TRIGGER=camera/snapshot/trigger
      - MQTT_TOPIC_STATUS=camera/snapshot/status
      - VERIFY_TLS=false
    volumes:
      - ./snapshots:/snapshots
```

---

## Triggering a Snapshot

Send an MQTT message to the trigger topic:

```bash
mosquitto_pub -h mqtt.local -t camera/snapshot/trigger -m "take_picture"
```

The service will respond on the status topic with a JSON message:

```json
{ "status": "success", "file": "snapshot_2025-08-21_12-00-00.jpg" }
```

or

```json
{ "status": "error", "message": "RTSP stream not reachable" }
```

---

## Notes

- In **HTTP mode**, make sure the camera’s snapshot API is enabled.
- In **RTSP mode**, `ffmpeg` must be available inside the container.
- Recommended to mount the `/snapshots` directory as a persistent volume.

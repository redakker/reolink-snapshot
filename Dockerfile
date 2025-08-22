# Snapshotter with optional RTSP (ffmpeg)
FROM python:3.11.8-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    ffmpeg \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy script
COPY snapshotter.py /app/snapshotter.py
RUN chmod +x /app/snapshotter.py

# create dirs
RUN mkdir -p /snapshots /errors
VOLUME ["/snapshots", "/errors"]

# defaults
ENV SAVE_DIR=/snapshots
ENV ERROR_DIR=/errors
ENV SNAPSHOT_URL_TEMPLATE="https://{ip}/cgi-bin/api.cgi?cmd=Snap&channel=0&user={user}&password={password}"
ENV MQTT_TOPIC_TRIGGER="camera/snapshot/trigger"
ENV MQTT_TOPIC_STATUS="camera/snapshot/status"
ENV TLS_VERIFY=0
ENV SNAPSHOT_MODE=web

CMD ["/usr/local/bin/python", "/app/snapshotter.py"]

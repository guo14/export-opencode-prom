#!/usr/bin/bash

DB_PATH="${HOME}/.local/share/opencode/opencode.db"
LISTEN_IP="${LISTEN_IP:-0.0.0.0}"
METRICS_PORT="${METRICS_PORT:-9092}"

docker rm -f opencode-exporter 2>/dev/null || true
docker build -t opencode-exporter .
docker run -d --name opencode-exporter --restart=always --net=host \
    --read-only \
    --cap-drop ALL \
    -v "$HOME:$HOME:ro,rslave" \
    -e DB_PATH="$DB_PATH" \
    -e LISTEN_IP="$LISTEN_IP" \
    -e METRICS_PORT="$METRICS_PORT" \
    opencode-exporter

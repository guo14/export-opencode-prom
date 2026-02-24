#!/usr/bin/env bash

DB_PATH="${HOME}/.local/share/opencode/opencode.db"
METRICS_PORT="${METRICS_PORT:-9092}"

docker rm -f opencode-exporter 2>/dev/null || true
docker build -t opencode-exporter .
docker run -d --name opencode-exporter --restart=always \
    -p "${METRICS_PORT}:${METRICS_PORT}" \
    --read-only \
    --cap-drop ALL \
    -v "$HOME:$HOME:ro" \
    -e DB_PATH="$DB_PATH" \
    -e METRICS_PORT="$METRICS_PORT" \
    opencode-exporter

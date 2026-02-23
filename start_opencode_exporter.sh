#!/usr/bin/bash

DB_PATH="${HOME}/.local/share/opencode/opencode.db"

docker rm -f opencode-exporter 2>/dev/null || true
docker build -t opencode-exporter .
docker run -d --name opencode-exporter --restart=always --net="host" \
    -v "$HOME:$HOME:ro,rslave" \
    -e DB_PATH="$DB_PATH" \
    opencode-exporter

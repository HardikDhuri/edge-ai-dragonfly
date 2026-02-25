#!/bin/bash
# Manually trigger a dfget pull through Dragonfly client
# (The TUI app does this automatically, but you can test it here)
echo "📡 Triggering model pull via Dragonfly client..."
docker compose exec client \
    dfget \
    --url "http://model-server/models/model.bin" \
    --output "/tmp/model.bin" \
    --log-level info
echo "✅ Model pulled to /tmp/model.bin inside the client container"
#!/bin/bash
# Standalone script to regenerate the model file
mkdir -p models
echo "🧠 Generating 1GB fake model (10 × 100MB)..."
dd if=/dev/urandom of=models/model.bin bs=100M count=10 status=progress
echo "✅ Done: $(du -sh models/model.bin)"
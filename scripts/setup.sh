#!/bin/bash
# ─────────────────────────────────────────────────────────
# ONE SCRIPT TO SET EVERYTHING UP
# Run: chmod +x scripts/setup.sh && ./scripts/setup.sh
# ─────────────────────────────────────────────────────────
set -e

echo ""
echo "🐉 Edge AI Model Propagator — Setup"
echo "════════════════════════════════════"

# ── Step 1: Get Host IP ──────────────────────────────────
export IP=$(docker network inspect bridge -f '{{range .IPAM.Config}}{{.Gateway}}{{end}}' 2>/dev/null || hostname -I | awk '{print $1}')
echo "✅ Host IP detected: $IP"

# ── Step 2: Generate config files from templates ─────────
echo "📝 Generating Dragonfly config files..."
mkdir -p config log/manager log/scheduler log/seed-client log/client

sed "s,__IP__,$IP,g" template/manager.template.yaml    > config/manager.yaml
sed "s,__IP__,$IP,g" template/scheduler.template.yaml  > config/scheduler.yaml
sed "s,__IP__,$IP,g" template/seed-client.template.yaml > config/seed-client.yaml
sed "s,__IP__,$IP,g" template/client.template.yaml     > config/client.yaml
echo "✅ Config files written to ./config/"

# ── Step 3: Generate the fake 1GB model file ────────────
echo ""
echo "🧠 Generating fake 1GB model file (10 × 100MB chunks)..."
mkdir -p models
if [ ! -f models/model.bin ]; then
    dd if=/dev/urandom of=models/model.bin bs=100M count=10 status=progress
    echo "✅ models/model.bin created ($(du -sh models/model.bin | cut -f1))"
else
    echo "⏭  models/model.bin already exists, skipping"
fi

# ── Step 4: Start all Docker services ───────────────────
echo ""
echo "🐳 Starting Docker Compose stack..."
docker compose up -d --build

# ── Step 5: Wait for all services to be healthy ──────────
echo ""
echo "⏳ Waiting for all services to be healthy..."
for i in $(seq 1 30); do
    total=$(docker compose ps --services | wc -l)
    healthy=$(docker compose ps | grep -c "healthy" || true)
    echo "   [$i/30] Healthy: $healthy / $total"
    if [ "$healthy" -ge "$total" ]; then
        break
    fi
    sleep 3
done

# ── Step 6: Install Python deps ──────────────────────────
echo ""
echo "🐍 Installing Python dependencies..."
pip3 install -q rich requests

# ── Done ─────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
echo "✅ Setup complete!"
echo ""
echo "📊 Manager UI  → http://localhost:8080"
echo "               (user: root / pass: dragonfly)"
echo "🧠 Model Server → http://localhost:8888/models/model.bin"
echo ""
echo "▶️  Run the TUI app:"
echo "   python3 app/tui.py"
echo "════════════════════════════════════════════"
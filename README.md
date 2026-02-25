# edge-ai-dragonfly# 🐉 Edge AI Model Propagator

Demonstrates Nydus lazy chunk loading + Dragonfly P2P distribution locally.

## Quick Start

```bash
# 1. Clone / create the project folder with all files above

# 2. Run the one-time setup (generates model, starts Docker, installs deps)
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. Launch the TUI app
python3 app/tui.py
```

## What You'll See

- **Left panel** — 10 × 100MB chunks loading one by one
- **Top-right** — Live bandwidth stats (origin vs P2P saved)
- **Bottom-right** — Chat with the "model" once chunk 3 is ready

## Chat Commands to Try

| Input | What it shows |
|-------|--------------|
| `hello` | Model identifies itself |
| `chunks` | Chunk loading stats |
| `bandwidth` | Origin vs P2P MB breakdown |
| `dragonfly` | Explains the P2P layer |
| `nydus` | Explains lazy loading |
| `status` | Live chunk summary |

## Services

| Service | URL |
|---------|-----|
| Manager UI | http://localhost:8080 (root/dragonfly) |
| Model Server | http://localhost:8888/models/model.bin |
| Dragonfly Proxy | http://localhost:4001 |

## Tear Down

```bash
docker compose down -v
```
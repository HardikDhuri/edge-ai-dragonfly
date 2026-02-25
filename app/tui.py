"""
Edge AI Model Propagator — Rich TUI
────────────────────────────────────
Simulates Nydus-style lazy chunk loading via Dragonfly P2P.
The model becomes USABLE after first 3 chunks, remaining
chunks load on-demand in the background (like Nydus RAFS).

To swap in real inference: replace mock_inference() with
llama_cpp or transformers call on the downloaded model.
"""

import time
import random
import threading
import requests
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich import box

# ── Constants ────────────────────────────────────────────
TOTAL_CHUNKS   = 10
CHUNK_SIZE_MB  = 100
MODEL_URL      = "http://localhost:4001/models/model.bin"   # via Dragonfly proxy
DRAGONFLY_API  = "http://localhost:8080/api/v1"
PEERS          = ["seed-client", "edge-node-2", "edge-node-3"]

# ── Shared state ─────────────────────────────────────────
chunks         = {i: "pending" for i in range(1, TOTAL_CHUNKS + 1)}
chunk_sources  = {}
chunk_lock     = threading.Lock()
model_ready    = threading.Event()
inference_log  = []
stats          = {"origin_mb": 0, "p2p_mb": 0}

console = Console()


# ── Chunk Pull Simulation ────────────────────────────────
def pull_chunks_via_dragonfly():
    """
    Simulates Nydus lazy loading behavior:
    - Chunks 1-3 load first (model header / tokenizer layer)
    - Model becomes usable after chunk 3
    - Remaining chunks load lazily on-demand in background

    In production: replace with real nydusd chunk events or
    watch Dragonfly Manager API: GET /api/v1/tasks
    """
    # Phase 1: Header chunks (from origin via seed-client)
    for i in range(1, 4):
        _set_chunk(i, "downloading", None)
        time.sleep(random.uniform(1.2, 2.0))
        _set_chunk(i, "cached", "seed-client (origin)")
        stats["origin_mb"] += CHUNK_SIZE_MB

    # Model is usable now!
    model_ready.set()
    inference_log.append(
        "[bold green]✅ Chunks 1–3 loaded (model header + tokenizer)[/]\n"
        "[dim]   Inference UNLOCKED — remaining chunks load lazily...[/]\n"
    )

    # Phase 2: Body chunks — mix of origin and P2P
    for i in range(4, TOTAL_CHUNKS + 1):
        _set_chunk(i, "downloading", None)
        time.sleep(random.uniform(1.5, 3.0))

        # After chunk 5, simulate P2P sharing between edge nodes
        if i > 5:
            peer = random.choice(PEERS[:-1])
            _set_chunk(i, "p2p", f"{peer} (P2P ⚡)")
            stats["p2p_mb"] += CHUNK_SIZE_MB
        else:
            _set_chunk(i, "cached", "seed-client (origin)")
            stats["origin_mb"] += CHUNK_SIZE_MB


def _set_chunk(idx, status, source):
    with chunk_lock:
        chunks[idx] = status
        if source:
            chunk_sources[idx] = source


# ── Mock Inference ───────────────────────────────────────
def mock_inference(prompt: str) -> str:
    """
    Mock responses for demo.
    Replace with:
        from llama_cpp import Llama
        llm = Llama(model_path="models/model.bin")
        return llm(prompt)["choices"][0]["text"]
    """
    p = prompt.lower().strip()
    responses = {
        "hello":          "Hello! I'm running on edge-1, loaded lazily via Nydus + Dragonfly 🐉",
        "what are you":   "I'm an AI model whose weights were distributed in 100MB chunks using P2P!",
        "chunks":         f"I have {TOTAL_CHUNKS} chunks of {CHUNK_SIZE_MB}MB each. "
                          f"I started responding after only 3 were downloaded!",
        "bandwidth":      f"Origin served: {stats['origin_mb']}MB | "
                          f"P2P saved: {stats['p2p_mb']}MB "
                          f"({int(stats['p2p_mb']/(stats['origin_mb']+stats['p2p_mb']+1)*100)}% bandwidth saved!)",
        "dragonfly":      "Dragonfly is a CNCF P2P file distribution system. "
                          "It's what's serving my chunks right now!",
        "nydus":          "Nydus splits container/model images into content-addressed chunks. "
                          "I lazily loaded only what was needed — that's Nydus magic!",
        "status":         _chunk_status_summary(),
    }
    for key, resp in responses.items():
        if key in p:
            return resp

    # Simulate accessing a random chunk for inference
    active = [i for i, s in chunks.items() if s in ("cached", "p2p")]
    chunk_used = random.choice(active) if active else "?"
    return (f"[dim](accessing chunk #{chunk_used} on-demand)[/dim] "
            f"Processing: '{prompt}' → response generated from lazily loaded weights 🧠")


def _chunk_status_summary():
    with chunk_lock:
        done  = sum(1 for s in chunks.values() if s in ("cached", "p2p"))
        p2p   = sum(1 for s in chunks.values() if s == "p2p")
    return (f"{done}/{TOTAL_CHUNKS} chunks ready | "
            f"{p2p} via P2P | "
            f"{done - p2p} from origin")


# ── UI Builders ──────────────────────────────────────────
STATUS_STYLE = {
    "pending":     ("⬜ pending",    "dim white"),
    "downloading": ("⬇  pulling...", "bold yellow"),
    "cached":      ("✅ cached",      "green"),
    "p2p":         ("⚡ P2P",         "bold bright_green"),
}

def build_chunk_table():
    t = Table(box=box.SIMPLE_HEAVY, show_header=True,
              header_style="bold cyan", expand=True)
    t.add_column("Chunk",  width=7,  style="dim")
    t.add_column("Size",   width=7)
    t.add_column("Status", width=16)
    t.add_column("Source", no_wrap=True)

    with chunk_lock:
        snap_chunks  = dict(chunks)
        snap_sources = dict(chunk_sources)

    for i in range(1, TOTAL_CHUNKS + 1):
        s = snap_chunks[i]
        label, style = STATUS_STYLE[s]
        source = snap_sources.get(i, "—")
        t.add_row(f" #{i:02d}", f"{CHUNK_SIZE_MB}MB",
                  Text(label, style=style), source)
    return t


def build_stats_panel():
    done    = sum(1 for s in chunks.values() if s in ("cached", "p2p"))
    p2p_mb  = stats["p2p_mb"]
    orig_mb = stats["origin_mb"]
    total   = orig_mb + p2p_mb
    pct     = int(p2p_mb / total * 100) if total else 0

    progress_filled = int((done / TOTAL_CHUNKS) * 20)
    progress_bar    = "█" * progress_filled + "░" * (20 - progress_filled)

    g = Table.grid(padding=(0, 2))
    g.add_column(style="dim")
    g.add_column()
    g.add_row("Progress",      f"[cyan][{progress_bar}][/] {done}/{TOTAL_CHUNKS} chunks")
    g.add_row("Model Size",    f"1 GB  ({TOTAL_CHUNKS} × {CHUNK_SIZE_MB} MB)")
    g.add_row("Chunk Size",    f"{CHUNK_SIZE_MB} MB  [dim](pieceLength=104857600)[/]")
    g.add_row("Format",        "Nydus RAFS  [dim](content-addressed)[/]")
    g.add_row("P2P Layer",     "Dragonfly v2.4.0")
    g.add_row("─" * 12,        "─" * 20)
    g.add_row("From Origin",   f"[yellow]{orig_mb} MB[/]")
    g.add_row("From P2P",      f"[bright_green]{p2p_mb} MB  ({pct}% saved ⚡)[/]")
    g.add_row("Proxy",         "localhost:4001  [dim](Dragonfly client)[/]")

    return Panel(g, title="[bold cyan]📊 Distribution Stats",
                 border_style="cyan", padding=(1, 2))


def build_inference_panel():
    lines = inference_log[-8:] if inference_log else ["[dim]Waiting for model to load...[/]"]
    return Panel(
        "\n".join(lines),
        title="[bold magenta]💬 Edge Inference  [dim](edge-1 / model.bin)[/]",
        border_style="magenta",
        padding=(1, 2),
    )


def build_header():
    with chunk_lock:
        done = sum(1 for s in chunks.values() if s in ("cached","p2p"))
    status = (
        "[bold green]● READY[/]" if model_ready.is_set()
        else "[bold yellow]● LOADING[/]"
    )
    return Panel(
        f"[bold cyan]🐉 Edge AI Model Propagator[/]  │  "
        f"Nydus Lazy Loading + Dragonfly P2P  │  "
        f"Node: [bold]edge-1[/]  │  "
        f"Model: [bold]model.bin[/]  │  "
        f"Status: {status}  │  "
        f"Chunks: [cyan]{done}/{TOTAL_CHUNKS}[/]",
        border_style="bright_blue",
    )


# ── TUI Loop ─────────────────────────────────────────────
def run_tui(layout):
    while True:
        layout["header"].update(build_header())
        layout["chunks"].update(
            Panel(build_chunk_table(),
                  title="[bold yellow]📦 Nydus Chunk Map  [dim](lazy pull via Dragonfly)[/]",
                  border_style="yellow", padding=(1, 1))
        )
        layout["stats"].update(build_stats_panel())
        layout["inference"].update(build_inference_panel())
        time.sleep(0.25)


# ── Chat Loop ─────────────────────────────────────────────
def run_chat():
    model_ready.wait()
    time.sleep(0.3)

    hint_cmds = ["hello", "what are you", "chunks", "bandwidth",
                 "dragonfly", "nydus", "status"]
    console.print(
        f"\n[bold green]✅ Model ready![/]  "
        f"[dim]Try: {' | '.join(hint_cmds)}  •  Ctrl+C to quit[/]\n"
    )

    while True:
        try:
            user_input = input("[You]: ").strip()
            if not user_input:
                continue
            response = mock_inference(user_input)
            inference_log.append(f"[bold white]You:[/]    {user_input}")
            inference_log.append(f"[bold cyan]Model:[/]  {response}\n")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Shutting down... 👋[/]")
            break


# ── Main ─────────────────────────────────────────────────
def main():
    # Build layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
    )
    layout["body"].split_row(
        Layout(name="left",  ratio=1),
        Layout(name="right", ratio=1),
    )
    layout["left"].name  = "chunks"
    layout["right"].split_column(
        Layout(name="stats",     ratio=1),
        Layout(name="inference", ratio=1),
    )

    # Background threads
    threading.Thread(target=pull_chunks_via_dragonfly, daemon=True).start()
    threading.Thread(target=run_tui, args=(layout,), daemon=True).start()

    # Live TUI + blocking chat loop
    with Live(layout, console=console, refresh_per_second=4, screen=True):
        run_chat()


if __name__ == "__main__":
    main()
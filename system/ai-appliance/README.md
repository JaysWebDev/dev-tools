# AI Appliance Setup

One-shot bootstrapper for a private local AI stack on a Linux machine. No cloud, no subscriptions.

## Stack

| Component | Purpose |
|-----------|---------|
| [Ollama](https://ollama.com) | Local LLM runtime |
| Qwen2.5-1.5B | Default model (~1GB, runs on CPU) |
| [Open WebUI](https://github.com/open-webui/open-webui) | Browser-based chat UI |
| Claude Code CLI | Optional agentic layer (v1 only) |

## Usage

```bash
bash setup-appliance.sh
```

Runs once on first boot. Installs Ollama, pulls the default model, sets up Open WebUI as a systemd service, and prints access URLs.

## Requirements

- Ubuntu 22.04+ (or Debian-based)
- 2GB+ RAM (4GB recommended for Qwen2.5-1.5B)
- No GPU required — CPU inference supported

## Access

After setup: `http://localhost:3000` for the chat UI, `http://localhost:11434` for the Ollama API.

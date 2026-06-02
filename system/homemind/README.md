# HomeMind Appliance 🍓

Local AI backend designed for a Raspberry Pi 4 (ARM64). FastAPI + llama-cpp-python inference server with streaming responses and a simple web chat UI. Runs fully offline — no cloud, no API keys required.

Part of [dev-tools](../../README.md) · [jays.website/appdevelopment](https://jays.website/appdevelopment/)

## Stack

- **FastAPI** — HTTP server with streaming responses
- **llama-cpp-python** — CPU/ARM64 inference (GGUF models)
- **systemd** — Runs as a persistent background service

## Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app — `/chat` endpoint with streaming |
| `build.sh` | Install script — creates venv, installs dependencies |
| `factory_flash.sh` | Factory reset — wipes and reinstalls from scratch |
| `homemind.service` | systemd unit template |
| `index.html` | Simple web chat UI |

## Setup

```bash
bash build.sh
# Edit homemind.service to set INSTALL_DIR, SERVICE_USER, VENV_DIR
sudo cp homemind.service /etc/systemd/system/
sudo systemctl enable --now homemind
```

## Config (env vars)

| Var | Default | Notes |
|-----|---------|-------|
| `HOMEMIND_DIR` | `/opt/homemind` | Install root |
| `HOMEMIND_PORT` | `8080` | HTTP port |
| `HOMEMIND_CTX` | `2048` | Context window |
| `HOMEMIND_THREADS` | `cpu_count - 1` | Inference threads |

## Model

Download any GGUF model into `models/`. Tested with TinyLlama-1.1B and Mistral-7B-Q4.

```bash
wget https://huggingface.co/.../model.gguf -O models/default.gguf
```

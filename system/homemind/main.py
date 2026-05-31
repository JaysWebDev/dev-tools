"""
HomeMind — local AI appliance backend
FastAPI + llama-cpp-python, optimised for Raspberry Pi 4 ARM64
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import AsyncIterator, Optional

import psutil
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from llama_cpp import Llama
from pydantic import BaseModel

# ── Config (override with env vars) ──────────────────────────────────────────
INSTALL_DIR = Path(os.environ.get("HOMEMIND_DIR", "/opt/homemind"))
MODEL_DIR   = INSTALL_DIR / "models"
PORT        = int(os.environ.get("HOMEMIND_PORT", 8080))
HOST        = os.environ.get("HOMEMIND_HOST", "0.0.0.0")
N_CTX       = int(os.environ.get("HOMEMIND_CTX", 2048))
# Leave one core for the OS; use the rest for inference
N_THREADS   = int(os.environ.get("HOMEMIND_THREADS", max(2, (os.cpu_count() or 4) - 1)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("homemind")

app = FastAPI(title="HomeMind", version="1.0.0", docs_url=None, redoc_url=None)

# ── Global inference state ────────────────────────────────────────────────────
_llm: Optional[Llama]   = None
_loaded_model: str      = ""
_gpu_layers_used: int   = 0
_startup_time: float    = time.time()
_easter_egg_shown: bool = False
_EASTER_EGG_FLAG        = INSTALL_DIR / ".first_rag_done"


# ── RAM-based default model selection ────────────────────────────────────────
def pick_default_model() -> Optional[Path]:
    """
    Returns the best available .gguf for the installed RAM.
    Preference order per tier, falls back to any .gguf found.
    """
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    log.info(f"System RAM: {ram_gb:.1f} GB  |  threads: {N_THREADS}  |  ctx: {N_CTX}")

    if ram_gb >= 7:
        preference = [
            "phi-3-mini-4k-instruct-q4.gguf",
            "qwen2-1_5b-instruct-q4_k_m.gguf",
            "tinyllama-1.1b-chat-v1.0.q4_k_m.gguf",
        ]
    elif ram_gb >= 3:
        preference = [
            "qwen2-1_5b-instruct-q4_k_m.gguf",
            "tinyllama-1.1b-chat-v1.0.q4_k_m.gguf",
        ]
    else:
        preference = ["tinyllama-1.1b-chat-v1.0.q4_k_m.gguf"]

    for name in preference:
        p = MODEL_DIR / name
        if p.exists():
            return p

    # Fallback: load whatever .gguf is there
    gguf_files = sorted(MODEL_DIR.glob("*.gguf"))
    return gguf_files[0] if gguf_files else None


# ── GPU offload probe ─────────────────────────────────────────────────────────
def _probe_gpu_layers(model_path: str) -> int:
    """
    Attempt to load the model with full GPU offload (-1 = all layers).
    On Pi 4 this will fail gracefully and return 0 (CPU-only).
    On Pi 5 with Hailo or a machine with CUDA this may succeed.
    """
    for layers in (-1, 0):
        try:
            probe = Llama(
                model_path=model_path,
                n_gpu_layers=layers,
                n_ctx=64,       # tiny context just to test load
                n_batch=32,
                verbose=False,
            )
            del probe
            if layers != 0:
                log.info(f"GPU offload available — n_gpu_layers={layers}")
            else:
                log.info("GPU offload unavailable — running CPU-only (normal on Pi 4)")
            return layers
        except Exception as exc:
            if layers == 0:
                raise RuntimeError(f"Model failed to load even CPU-only: {exc}") from exc
            log.warning(f"GPU offload probe failed: {exc} — retrying CPU-only")
    return 0


# ── Model loader ──────────────────────────────────────────────────────────────
def load_model(model_path: str) -> None:
    global _llm, _loaded_model, _gpu_layers_used

    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    log.info(f"Loading: {path.name}")
    t0 = time.time()

    n_gpu_layers = _probe_gpu_layers(model_path)

    _llm = Llama(
        model_path=model_path,
        n_gpu_layers=n_gpu_layers,
        n_ctx=N_CTX,
        n_batch=512,
        n_threads=N_THREADS,
        verbose=False,
    )
    _loaded_model     = path.name
    _gpu_layers_used  = n_gpu_layers
    elapsed = time.time() - t0
    accel   = f"GPU layers={n_gpu_layers}" if n_gpu_layers else "CPU-only"
    log.info(f"Ready in {elapsed:.1f}s — {accel} — threads={N_THREADS}")


# ── App startup ───────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    default = pick_default_model()
    if default:
        try:
            load_model(str(default))
        except Exception as exc:
            log.error(f"Could not load default model: {exc}")
    else:
        log.warning(
            "No .gguf models found in %s\n"
            "Drop a quantised GGUF file there and call POST /reload",
            MODEL_DIR,
        )


# ── Schemas ───────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    model: Optional[str]        = None   # filename, e.g. "qwen2-1_5b..."
    system_prompt: Optional[str] = "You are a helpful, concise assistant running entirely offline on a local device."
    max_tokens: int             = 512
    temperature: float          = 0.7
    stream: bool                = True


class ReloadRequest(BaseModel):
    model: str                           # filename only


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    index = INSTALL_DIR / "static" / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    return HTMLResponse(
        "<h1>HomeMind</h1>"
        "<p>index.html missing — place it at /opt/homemind/static/index.html</p>"
    )


@app.get("/health")
async def health():
    """
    Lightweight health check — safe to poll every few seconds from the UI.
    Returns system stats and current model state.
    """
    mem  = psutil.virtual_memory()
    cpu  = psutil.cpu_percent(interval=0.1)
    temp = _read_soc_temp()
    return {
        "status":        "ok" if _llm else "no_model",
        "model":         _loaded_model or None,
        "gpu_layers":    _gpu_layers_used,
        "acceleration":  ("GPU" if _gpu_layers_used else "CPU+OpenBLAS"),
        "uptime_s":      int(time.time() - _startup_time),
        "cpu_pct":       cpu,
        "cpu_temp_c":    temp,
        "ram_total_mb":  round(mem.total  / 1024 / 1024),
        "ram_used_mb":   round(mem.used   / 1024 / 1024),
        "ram_free_mb":   round(mem.available / 1024 / 1024),
        "ram_pct":       mem.percent,
        "n_threads":     N_THREADS,
        "n_ctx":         N_CTX,
    }


@app.get("/models")
async def list_models():
    """List all .gguf files in the models directory."""
    files = sorted(MODEL_DIR.glob("*.gguf"))
    return {
        "models": [
            {
                "filename": f.name,
                "size_mb":  round(f.stat().st_size / 1024 / 1024),
                "loaded":   f.name == _loaded_model,
            }
            for f in files
        ],
        "loaded": _loaded_model or None,
    }


@app.post("/reload")
async def reload_model(req: ReloadRequest):
    """Hot-swap to a different model without restarting the service."""
    path = MODEL_DIR / req.model
    try:
        load_model(str(path))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "ok", "model": _loaded_model, "gpu_layers": _gpu_layers_used}


@app.post("/chat")
async def chat(req: ChatRequest):
    global _easter_egg_shown

    # Hot-swap model if requested
    if req.model and req.model != _loaded_model:
        try:
            load_model(str(MODEL_DIR / req.model))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Model swap failed: {exc}")

    if not _llm:
        raise HTTPException(status_code=503, detail="No model loaded")

    prompt = _build_chatML_prompt(req.system_prompt or "", req.message)

    # Easter egg: first successful RAG-like query on this device (one-time, never repeats)
    easter = None
    if not _EASTER_EGG_FLAG.exists() and not _easter_egg_shown:
        easter = (
            "\n\n---\n"
            "*Nice. Your knowledge is now 100% yours — no monthly bill, "
            "no surprise takedowns, no leaked source code required. "
            "Welcome to OpenClaw.*"
        )
        _EASTER_EGG_FLAG.touch()
        _easter_egg_shown = True

    if req.stream:
        return StreamingResponse(
            _stream_tokens(prompt, req.max_tokens, req.temperature, easter),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    result = _llm(prompt, max_tokens=req.max_tokens, temperature=req.temperature, echo=False)
    text   = result["choices"][0]["text"].strip()
    if easter:
        text += easter
    return {"response": text, "model": _loaded_model}


# ── Internal helpers ──────────────────────────────────────────────────────────
def _build_chatML_prompt(system: str, user: str) -> str:
    """
    ChatML format — compatible with Phi-3, Qwen2, TinyLlama, and most
    modern instruction-tuned GGUF models.
    """
    return (
        f"<|system|>\n{system}<|end|>\n"
        f"<|user|>\n{user}<|end|>\n"
        f"<|assistant|>\n"
    )


async def _stream_tokens(
    prompt: str,
    max_tokens: int,
    temperature: float,
    append_after: Optional[str],
) -> AsyncIterator[str]:
    try:
        for chunk in _llm(          # type: ignore[misc]
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            echo=False,
        ):
            token = chunk["choices"][0]["text"]
            if token:
                yield f"data: {json.dumps({'token': token})}\n\n"

        if append_after:
            yield f"data: {json.dumps({'token': append_after})}\n\n"

        yield "data: [DONE]\n\n"
    except Exception as exc:
        log.error(f"Streaming error: {exc}")
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"


def _read_soc_temp() -> Optional[float]:
    """Read ARM SoC temperature — works on Pi 4/5 and DietPi."""
    thermal = Path("/sys/class/thermal/thermal_zone0/temp")
    try:
        return round(int(thermal.read_text().strip()) / 1000, 1) if thermal.exists() else None
    except Exception:
        return None


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        log_level="info",
        loop="uvloop",      # faster event loop (bundled with uvicorn[standard])
        workers=1,          # single worker — LLM state is not fork-safe
    )

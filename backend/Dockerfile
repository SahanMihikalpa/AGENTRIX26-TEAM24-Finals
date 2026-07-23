# syntax=docker/dockerfile:1.7
#
# GovGuide backend — FastAPI + LangGraph, CPU-only.
#
# No CUDA: the single GPU-capable workload is the local bge embedder, and it is
# not the bottleneck. Measured on this stack, one query embedding costs ~63 ms
# on CPU while the LLM gateway (app/infrastructure/llm_gateway.py) throttles
# Gemini/Groq to 15 rpm — i.e. seconds per agent call. A CUDA image would add
# ~4 GB to shave ~50 ms off a multi-second turn. See ../DOCKER.md.

# ── Stage 1: builder — resolve the Python stack into a self-contained venv ────
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# Only needed for any dependency that still ships an sdist; dropped in runtime.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# torch FIRST, from the CPU-only wheel index. This line is load-bearing: on
# Linux the default PyPI torch is the CUDA build, which drags in nvidia-cudnn /
# cublas / cusparse (~4 GB). Installing +cpu up front means the requirements
# install below finds torch already satisfying sentence-transformers.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.12.1

COPY requirements.txt ./
RUN pip install -r requirements.txt


# ── Stage 2: runtime — the venv, the app, and the embedding model ────────────
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/opt/hf

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY app ./app
COPY pyproject.toml README.md ./

# Bake bge-base-en-v1.5 (~440 MB) into the image so the container needs no
# HuggingFace round-trip at boot and the first /api/chat request skips the
# download. Same model for writes (B3) and reads (A4) — the AD-4 invariant.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-en-v1.5')" \
 && rm -rf /opt/hf/hub/*/blobs/*.bin.lock /root/.cache

# Non-root. The uid is fixed so a bind-mounted ./backend/data keeps stable
# ownership across rebuilds; /opt/hf must stay readable for the model load.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin govguide \
 && mkdir -p /app/data \
 && chown -R govguide:govguide /app \
 && chmod -R a+rX /opt/hf
USER govguide

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).status == 200 else 1)"]

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

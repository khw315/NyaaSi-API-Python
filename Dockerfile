# ──────────────────────────────────────────────────────────────
# NyaaSi-API Python — Docker image
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Keep Python output unbuffered so logs appear in real time
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

LABEL org.opencontainers.image.source=https://github.com/khw315/NyaaSi-API-Python
LABEL org.opencontainers.image.licenses=GPL-3.0
LABEL org.opencontainers.image.description="API for nyaa.si and sukebei.nyaa.si"

# ── Install system deps required by lxml ──────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# ── Upgrade toolchain so setuptools.backends.legacy is available
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ── Copy only the requirements first (cache-friendly) ───────────
COPY requirements.txt ./

# Install runtime dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy the rest of the source ───────────────────────────────
COPY . .

# Expose the port for the FastAPI service
EXPOSE 88

# Default command: span the API web service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "88"]

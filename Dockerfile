# ArchGen Hugging Face Spaces Dockerfile
# Provides a minimal environment with Tectonic for TikZ -> PDF compilation.

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860

# System deps + TeX Live (TikZ + standalone + latexmk). This is larger but stable.
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget ca-certificates fontconfig curl \
        texlive-latex-base texlive-latex-recommended texlive-pictures texlive-latex-extra \
        latexmk \
        poppler-utils ghostscript imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Verify latex tools
RUN pdflatex --version && latexmk --version || true

WORKDIR /workspace

# Install Python dependencies first for layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 7860

# Default command for Spaces
CMD ["python", "app.py"]

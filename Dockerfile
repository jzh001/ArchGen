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
                wget ca-certificates fontconfig curl tar \
                texlive-latex-base texlive-latex-recommended texlive-pictures texlive-latex-extra \
                latexmk \
                poppler-utils ghostscript imagemagick \
                libssl3 \
        && rm -rf /var/lib/apt/lists/*

# Install Tectonic (Linux, arch-aware)
ENV TECTONIC_VERSION=0.15.0
RUN set -eux; \
        arch="$(dpkg --print-architecture)"; \
        case "$arch" in \
            amd64)  TT_FILE="tectonic-${TECTONIC_VERSION}-x86_64-unknown-linux-gnu.tar.gz" ;; \
            arm64)  TT_FILE="tectonic-${TECTONIC_VERSION}-aarch64-unknown-linux-musl.tar.gz" ;; \
            i386)   TT_FILE="tectonic-${TECTONIC_VERSION}-i686-unknown-linux-gnu.tar.gz" ;; \
            *) echo "Unsupported architecture: $arch" >&2; exit 1 ;; \
        esac; \
        TT_URL="https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/$TT_FILE"; \
        echo "Downloading $TT_URL"; \
        curl -fsSL "$TT_URL" -o /tmp/tectonic.tgz; \
        mkdir -p /opt/tectonic; \
        tar -xzf /tmp/tectonic.tgz -C /opt/tectonic; \
        # Place binary on PATH (handles different archive layouts)
        if [ -x /opt/tectonic/tectonic ]; then \
            mv /opt/tectonic/tectonic /usr/local/bin/tectonic; \
        elif [ -x /opt/tectonic/bin/tectonic ]; then \
            mv /opt/tectonic/bin/tectonic /usr/local/bin/tectonic; \
        else \
            TPATH=$(find /opt/tectonic -maxdepth 3 -type f -name tectonic | head -n1); \
            mv "$TPATH" /usr/local/bin/tectonic; \
        fi; \
        chmod +x /usr/local/bin/tectonic; \
        rm -f /tmp/tectonic.tgz; \
        tectonic --version || (echo "Tectonic not installed correctly" >&2; exit 1)

# Verify latex tools (tectonic preferred, fallbacks available)
RUN tectonic --version && pdflatex --version && latexmk --version || true

WORKDIR /workspace

# Install Python dependencies first for layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 7860

# Default command for Spaces
CMD ["python", "app.py"]

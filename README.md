---
title: "ArchGen"
language: "python"
license: "apache-2.0"
tags:
    - space
    - architecture
    - visualization
sdk: docker
sdk_version: "4.36.0"
app_file: frontend/app.py
pinned: false
# thumbnail: "thumbnail.png"
---

# ArchGen

Prototype architecture diagram generator for PyTorch modules.

## Packages

This repository now exposes two Python packages:

1. `archgen` – core parsing, diagram generation, exporting.
2. `archgen_llm` – (future) LLM-assisted layout hint generation.

The legacy import `from archgen.llm import generate_layout_hints` still works via a shim, but new code should use:

```python
from archgen_llm import generate_layout_hints
```

## Quickstart (development)

Install in editable mode and run the UI locally:

```bash
pip install -e .
python -m archgen.app
```

## Environment Keys

Create a `.env` (copy `.env.example`) for provider keys used by the optional LLM integrations:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
HUGGINGFACEHUB_API_TOKEN=...
```

If no key is set or the provider is `None`, a deterministic layout hint set is used.

## Docker

Build and run (exposes port 7860):

```bash
docker build -t archgen .
docker run --rm -p 7860:7860 archgen
```

Or use docker compose:

```bash
docker compose up --build
```

For rapid iteration, consider live-mounting the source by enabling the volume in `docker-compose.yml`.

## Hugging Face Space

This repository is mirrored to a Hugging Face Space (`hf` remote). To keep the Space in sync with GitHub (recommended), either push explicitly to both remotes or use a CI mirror.

Manual sync (safe):

```bash
# update local from GitHub
git fetch origin --prune
git pull --rebase origin main

# push to GitHub
git push origin main

# push to Hugging Face Space
git push hf main
```

If the Hugging Face remote has divergent history, create a backup branch first and then force-push with lease:

```bash
git fetch hf --prune
git checkout -b hf-main-backup hf/main || echo "no hf/main found"
git push origin hf-main-backup
git push --force-with-lease hf main
```

For long-term automation, consider adding a GitHub Action that pushes to the Space on every push to `main` (requires `HF_TOKEN` in GitHub Secrets).

## Contributing

Contributions welcome. Open an issue or PR for bugs, features, or docs improvements.

## License

Apache-2.0 (intended) — update if you choose a different license.
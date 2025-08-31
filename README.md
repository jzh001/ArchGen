# ArchGen

Prototype architecture diagram generator for PyTorch modules.

## Packages

This repository now exposes two Python packages:

1. `archgen` – core parsing, diagram generation, exporting.
2. `archgen_llm` – (future) LLM assisted layout hint generation.

The legacy import `from archgen.llm import generate_layout_hints` still works via a shim, but new code should use:

```python
from archgen_llm import generate_layout_hints
```

## Installation (editable dev)

```bash
pip install -e .
```

## Environment Keys

Create a `.env` (copy `.env.example`) for any provider keys you want:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
HUGGINGFACEHUB_API_TOKEN=...
```

If no key is set or provider is `None`, a deterministic layout hint set is used.

## Run UI

```bash
python -m archgen.app
```

### Docker (one-off)

Build the image and run exposing port 7860:

```bash
docker build -t archgen .
docker run --rm -p 7860:7860 archgen
```

### Docker Compose (simpler)

After first build you can just use compose:

```bash
docker compose up --build
```

Subsequent runs:

```bash
docker compose up
```

Stop with Ctrl+C (or `docker compose down`).

Optional: uncomment the volume in `docker-compose.yml` to live mount the source for rapid iteration.

## License

TBD
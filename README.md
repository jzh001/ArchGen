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
# thumbnail: "images/CNN2.png"
---

# ArchGen

**ArchGen** is a professional tool for generating architecture diagrams from PyTorch `nn.Module` code. Designed for researchers, engineers, and educators, ArchGen streamlines the visualization of deep learning models.

---

## 🚀 Try it out

[Launch ArchGen on Hugging Face Spaces](https://huggingface.co/spaces/jzh001/ArchGen)

---

## Quickstart (Development)

Install in editable mode and run locally:

```bash
pip install -e .
python -m archgen.app
```

## Environment Keys

To enable optional LLM integrations, create a `.env` file (copy `.env.example`) and add your provider keys:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
DB_CONNECTION=...
ADMIN_PASSWORD=...
```

## Docker

Build and run (port 7860):

```bash
docker build -t archgen .
docker run --rm -p 7860:7860 archgen
```

Or use Docker Compose:

```bash
docker compose up --build
```

## Hugging Face Space

ArchGen is also available as a [Hugging Face Space](https://huggingface.co/spaces/jzh001/ArchGen). To keep the Space in sync with GitHub, push to both remotes or use CI automation.

## Contributing

Contributions are welcome! Please open an issue or pull request for bugs, features, or documentation improvements.

## Example Usage

Paste or select a PyTorch `nn.Module` in the UI to generate an architecture diagram. Example presets are available.

---

## License

Apache-2.0

---

## References

- [NNTikZ - TikZ Diagrams for Deep Learning and Neural Networks](https://github.com/fraserlove/nntikz)
- [Collection of LaTeX resources and examples](https://github.com/davidstutz/latex-resources)
- [tikz.net](https://tikz.net)
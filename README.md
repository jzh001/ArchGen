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


## Agentic RAG

ArchGen uses a streamlined form of agentic Retrieval-Augmented Generation (RAG). In this system, each agent (generator or critic) can make tool calls per invocation to search the TikZ example database. The agent incorporates the retrieved results into its reasoning and output. The multi-agent workflow (generator and critic) allows for iterative improvement and critique, with each agent invocation optionally leveraging the retrieval tool.

ArchGen’s agentic RAG workflow:
- The generator and critic agents can each invoke the TikZ search tool to retrieve relevant examples.
- Retrieved results are integrated into the agent’s reasoning and responses for that turn.
- The multi-agent loop enables iterative refinement, with retrieval available at each agent step.

This design makes ArchGen suitable for research, education, and engineering scenarios where deep model understanding and knowledge integration are required, while keeping the retrieval process simple and predictable.

---

## License

Apache-2.0

---

## References

- [NNTikZ - TikZ Diagrams for Deep Learning and Neural Networks](https://github.com/fraserlove/nntikz)
- [Collection of LaTeX resources and examples](https://github.com/davidstutz/latex-resources)
- [tikz.net](https://tikz.net)
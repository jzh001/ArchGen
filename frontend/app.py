"""Gradio application for ArchGen prototype."""
from __future__ import annotations

import gradio as gr
import os
import base64
from dotenv import load_dotenv
from .diagram import render_graph
from .exporters import save_outputs
from .presets import PRESETS
import time


load_dotenv()  # Load environment variables from .env if present


ENV_KEY_MAP = {
    "OpenAI": "OPENAI_API_KEY",
    "Anthropic": "ANTHROPIC_API_KEY",
    "HuggingFace": "HUGGINGFACEHUB_API_TOKEN",
    "Ollama": None,  # usually local, no key required
}


def build_interface():
    with gr.Blocks(title="ArchGen") as demo:
        gr.Markdown("# ArchGen\nPaste or select a PyTorch nn.Module to generate an architecture diagram.")
        with gr.Row():
            preset = gr.Dropdown(choices=list(PRESETS.keys()), value="SimpleMLP", label="Preset Model")
            provider = gr.Dropdown(choices=["None", "OpenAI", "Anthropic", "HuggingFace", "Ollama"], value="Ollama", label="LLM Provider")
        code = gr.Code(label="PyTorch nn.Module code", language="python", value=PRESETS["SimpleMLP"])
        status = gr.Markdown(visible=False)
        with gr.Row():
            generate_btn = gr.Button("Generate", variant="primary")
        pdf_viewer = gr.HTML(label="Preview (JPEG if available else PDF/TikZ)")
        download_files = gr.File(label="Downloads (JPEG/PDF/TikZ)", file_count="multiple")

        def _ensure_code(preset_choice, current_code):
            return PRESETS[preset_choice] if preset_choice and PRESETS.get(preset_choice) else current_code

        def generate(preset_choice, code_text, provider_choice):
            t0 = time.time()
            env_var = ENV_KEY_MAP.get(provider_choice)
            api_key = os.getenv(env_var) if env_var else None
            outputs = render_graph(code_text, want_jpeg=True)
            paths = save_outputs(outputs)
            downloads = [p for k, p in paths.items() if k in ("jpeg", "pdf", "tex")]
            elapsed = time.time() - t0
            status_text = "Generation Complete\n"
            if "pdf" not in outputs:
                status_text += " — PDF compilation unavailable (install tectonic or pdflatex)."
            if paths.get("jpeg") and os.path.exists(paths["jpeg"]):
                try:
                    with open(paths["jpeg"], "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    html_preview = (
                        '<div style="text-align:center;">'
                        f'<img src="data:image/jpeg;base64,{b64}" '
                        'style="max-width:90%;height:auto;border:1px solid #ccc;display:inline-block;" '
                        'alt="Diagram preview" />'
                        '</div>'
                    )
                except Exception:
                    html_preview = "<p>Failed to load JPEG preview.</p>"
            elif paths.get("pdf") and os.path.exists(paths["pdf"]):
                try:
                    with open(paths["pdf"], "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    html_preview = f'<iframe src="data:application/pdf;base64,{b64}" style="width:100%;height:600px;" frameborder="0"></iframe>'
                except Exception:
                    html_preview = "<p>Failed to load PDF preview.</p>"
            else:
                if paths.get("tex") and os.path.exists(paths["tex"]):
                    try:
                        with open(paths["tex"], "r", encoding="utf-8", errors="ignore") as f:
                            tikz_snippet = f.read()[:2000]
                        html_preview = (
                            "<p>No PDF generated. Showing first part of TikZ source:</p><pre style='white-space:pre-wrap;font-size:12px;border:1px solid #ccc;padding:8px;max-height:600px;overflow:auto;'>" +
                            gr.utils.sanitize_html(tikz_snippet) +
                            "</pre>"
                        )
                    except Exception:
                        html_preview = "<p>No PDF generated.</p>"
                else:
                    html_preview = "<p>No PDF generated.</p>"
            return html_preview, downloads, gr.update(value=status_text, visible=True)

        preset.change(_ensure_code, [preset, code], [code])
        generate_btn.click(
            generate,
            [preset, code, provider],
            [pdf_viewer, download_files, status],
        )

    return demo


if __name__ == "__main__":
    build_interface().launch()

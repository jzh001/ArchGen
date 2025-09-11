"""Gradio application for ArchGen prototype."""
from __future__ import annotations

import gradio as gr
import os
import base64
from dotenv import load_dotenv
from frontend.diagram import render_graph
from frontend.exporters import save_outputs
from frontend.presets import PRESETS
from constants import LLM_OPTIONS
from vector_db.index import add_documents_to_vector_db

load_dotenv()  # Load environment variables from .env file if present


def build_interface():
    with gr.Blocks(title="ArchGen") as demo:
        gr.Markdown("# ArchGen\nPaste or select a PyTorch nn.Module to generate an architecture diagram.")
        
        with gr.Tabs():
            with gr.TabItem("Generate Diagram"):
                with gr.Row():
                    preset = gr.Dropdown(choices=list(PRESETS.keys()), value="SimpleMLP", label="Preset Model")
                    provider = gr.Dropdown(choices=LLM_OPTIONS, value=LLM_OPTIONS[0], label="LLM Provider")
                code = gr.Code(label="PyTorch nn.Module code", language="python", value=PRESETS["SimpleMLP"])
                status = gr.Markdown(visible=False)
                with gr.Row():
                    generate_btn = gr.Button("Generate", variant="primary")
                pdf_viewer = gr.HTML(label="Preview (JPEG if available else PDF/TikZ)")
                download_files = gr.File(label="Downloads (JPEG/PDF/TikZ)", file_count="multiple")

                def _ensure_code(preset_choice, current_code):
                    return PRESETS[preset_choice] if preset_choice and PRESETS.get(preset_choice) else current_code

                def generate(preset_choice, code_text, provider_choice):
                    outputs = render_graph(code_text, provider_choice, want_jpeg=True)
                    paths = save_outputs(outputs)
                    downloads = [p for k, p in paths.items() if k in ("jpeg", "pdf", "tex")]
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

            with gr.TabItem("Admin - Add Documents"):
                admin_password = gr.Textbox(label="Admin Password", type="password")
                document_text = gr.Textbox(label="Enter Documents (separate multiple documents with '---')", lines=10, placeholder="Type your documents here...")
                upload_status = gr.Markdown(visible=False)
                upload_btn = gr.Button("Submit", variant="primary")


                def upload_documents(password, text):
                    if password != os.getenv("ADMIN_PASSWORD"):
                        return gr.update(value="Invalid password.", visible=True)

                    if not text.strip():
                        return gr.update(value="No text provided.", visible=True)

                    try:
                        documents = [doc.strip() for doc in text.split('---') if doc.strip()]
                        count = add_documents_to_vector_db(documents)
                        return gr.update(value=f"✅ Successfully added {count} document(s) to the database.", visible=True)
                    except Exception as e:
                        return gr.update(value=f"Error adding documents: {str(e)}", visible=True)

                upload_btn.click(upload_documents, [admin_password, document_text], [upload_status])

    return demo


if __name__ == "__main__":
    build_interface().launch()

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
import time

load_dotenv()  # Load environment variables from .env file if present

def build_interface():
    with gr.Blocks(title="ArchGen") as demo:
        gr.Markdown("""
        # ArchGen
        Paste or select a PyTorch nn.Module to generate an architecture diagram.

        """
        )

        # Persistent states for loading and results
        loading_state = gr.State(False)
        result_state = gr.State(None)

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

                def set_loading():
                    return gr.update(visible=True, value="Loading..."), True, None

                def generate(preset_choice, code_text, provider_choice):
                    # Set loading state
                    status_update, loading, _ = set_loading()
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
                    # Set states: loading False, result
                    return html_preview, downloads, gr.update(value=status_text, visible=True), False, status_text

                # When preset changes, update code
                preset.change(_ensure_code, [preset, code], [code])
                # When generate is clicked, set loading state, then run generate
                generate_btn.click(
                    set_loading,
                    [],
                    [status, loading_state, result_state],
                    queue=True
                )
                generate_btn.click(
                    generate,
                    [preset, code, provider],
                    [pdf_viewer, download_files, status, loading_state, result_state],
                    queue=True
                )

                # Remove status.select, as Markdown does not support .select. Status is updated only via callbacks.

            with gr.TabItem("Admin Dashboard"):
                # State to track password validation
                admin_authenticated = gr.State(False)
                admin_password = gr.Textbox(label="Enter Admin Password", type="password", visible=True)
                password_status = gr.Markdown(visible=False)

                # All admin options are hidden until password is validated
                with gr.Column(visible=False) as admin_panel:
                    doc_desc = gr.Textbox(label="Description", lines=2, placeholder="Describe the document...")
                    doc_tikz = gr.Textbox(label="TikZ Code", lines=8, placeholder="Paste TikZ code here...")
                    upload_status = gr.Markdown(visible=False)
                    upload_btn = gr.Button("Submit", variant="primary")

                    rag_query = gr.Textbox(label="Test RAG Query", placeholder="Type your query here...")
                    rag_response = gr.Markdown(visible=False)
                    rag_btn = gr.Button("Test Query", variant="secondary")

                from vector_db.index import is_vector_db_ready, get_vector_db_error

                def check_admin_password(pw):
                    if pw == os.getenv("ADMIN_PASSWORD"):
                        # Hide password box and status, show admin panel
                        return gr.update(visible=False), gr.update(visible=False), True, gr.update(visible=True)
                    else:
                        # Show status, keep password box visible, keep admin panel hidden
                        return gr.update(visible=True, value="Invalid password."), gr.update(visible=True), False, gr.update(visible=False)

                def upload_documents(desc, tikz):
                    if not is_vector_db_ready():
                        error = get_vector_db_error()
                        if error:
                            return gr.update(value=f"Vector DB error: {error}", visible=True)
                        return gr.update(value="Connecting to vector database... Please wait.", visible=True)
                    if not desc.strip() and not tikz.strip():
                        return gr.update(value="No description or TikZ code provided.", visible=True)
                    try:
                        import json
                        doc_obj = {"description": desc.strip(), "tikz": tikz.strip()}
                        doc_json = json.dumps(doc_obj, ensure_ascii=False)
                        count = add_documents_to_vector_db([doc_json])
                        return gr.update(value=f"✅ Successfully added {count} document to the database.", visible=True)
                    except Exception as e:
                        return gr.update(value=f"Error adding documents: {str(e)}", visible=True)

                def test_rag_query(query):
                    if not query.strip():
                        return gr.update(value="No query provided.", visible=True)
                    try:
                        from vector_db.rag import perform_rag
                        response = perform_rag(query)
                        return gr.update(value=f"**RAG Response:**\n\n```text\n{response}\n```", visible=True)
                    except Exception as e:
                        return gr.update(value=f"Error during RAG query: {str(e)}", visible=True)

                # Password check: reveal admin panel if correct, hide password box/status
                admin_password.submit(
                    check_admin_password,
                    [admin_password],
                    [password_status, admin_password, admin_authenticated, admin_panel],
                )

                # Only allow upload/rag actions if authenticated
                upload_btn.click(upload_documents, [doc_desc, doc_tikz], [upload_status])
                rag_btn.click(test_rag_query, [rag_query], [rag_response])
        gr.Markdown("""
        ## References
        - [NNTikZ - TikZ Diagrams for Deep Learning and Neural Networks](https://github.com/fraserlove/nntikz)  
            Fraser Love, 2024. GitHub repository.  
            `@misc{love2024nntikz, author = {Fraser Love}, title = {NNTikZ - TikZ Diagrams for Deep Learning and Neural Networks}, year = 2024, url = {https://github.com/fraserlove/nntikz}, note = {GitHub repository} }`
        - [Collection of LaTeX resources and examples](https://github.com/davidstutz/latex-resources)  
            David Stutz, 2022. GitHub repository.  
            `@misc{Stutz2022, author = {David Stutz}, title = {Collection of LaTeX resources and examples}, publisher = {GitHub}, journal = {GitHub repository}, howpublished = {\\url{https://github.com/davidstutz/latex-resources}}, note = {Accessed on MM.DD.YYYY}}`
        - [tikz.net](https://tikz.net)  
            A collection of TikZ examples and resources.
        """)
    return demo


if __name__ == "__main__":
    build_interface().launch()

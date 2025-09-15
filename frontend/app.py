from __future__ import annotations

import gradio as gr
import os
import base64
from dotenv import load_dotenv
from frontend.diagram import render_graph, render_graph_stream
from frontend.exporters import save_outputs
from frontend.presets import PRESETS
from constants import LLM_OPTIONS
from vector_db.index import add_documents_to_vector_db, is_vector_db_ready, get_vector_db_error

load_dotenv()  # Load environment variables from .env file if present

def get_db_status():
    if is_vector_db_ready():
        return "✅ Vector DB: Ready"
    error = get_vector_db_error()
    if error:
        return f"❌ Vector DB: Error - {error}"
    else:
        return "⏳ Vector DB: Initializing..."

def update_display(status):
    return status

CSS = """
/* Controls card */
#controls_row { gap: 12px; }
#controls_row .gradio-row { gap: 12px; }
#controls_row .gradio-container { /* allow components to share the row */ }
#gen_btn_col { display: flex; align-items: flex-end; }
#generate_btn { width: 100%; }

/* Side-by-side editor and logs */
#code_col, #logs_col { min-height: 620px; }
#code_col { display: flex; flex-direction: column; gap: 12px; }
#code_col .ace_editor { height: 400px !important; min-height: 400px !important; max-height: 400px !important; overflow-y: auto !important; border: 1px solid #e5e7eb; border-radius: 8px; }
#code_col .ace_editor .ace_scrollbar { display: block !important; }
/* Fix for TikZ code editor */
#code_col .ace_editor:last-of-type { height: 400px !important; min-height: 400px !important; max-height: 400px !important; }
#logs_col { display: flex; align-items: stretch; }
#logs_panel { flex: 1; height: 812px; min-height: 812px; max-height: 812px; overflow-y: auto; white-space: pre-wrap; background: #0b1021; color: #e5e7eb; padding: 12px; border-radius: 8px; border: 1px solid #1f2937; }
#logs_panel a { color: #93c5fd; }
#logs_panel code, #logs_panel pre { color: #e5e7eb; }

/* Ensure textarea elements also have fixed heights and scrolling */
#code_col .gr-textbox textarea { height: 400px !important; min-height: 400px !important; max-height: 400px !important; overflow-y: auto !important; resize: none !important; }
#code_col .gr-code textarea { height: 400px !important; min-height: 400px !important; max-height: 400px !important; overflow-y: auto !important; resize: none !important; }
#code_col .gr-code:last-of-type textarea { height: 400px !important; min-height: 400px !important; max-height: 400px !important; }

/* Preview/download card */
#preview_card { border: 0; border-radius: 10px; padding: 12px; background: transparent; box-shadow: none; }

/* Remove white border around Downloads component */
#downloads { border: 0 !important; background: transparent !important; box-shadow: none !important; }
#downloads * { box-shadow: none !important; }
#downloads .container, #downloads .wrap, #downloads .prose, #downloads .grid, #downloads .file-preview { border: 0 !important; background: transparent !important; }
"""

def build_interface():
    with gr.Blocks(title="ArchGen", css=CSS) as demo:
        gr.Markdown(
            """
            # ArchGen
            Paste or select a PyTorch nn.Module to generate an architecture diagram.

            <span style='color:orange; font-weight:bold;'>⚠️ Please note: Generation may take up to a few minutes depending on model and server load.</span>
            """
        )

        db_status = gr.Markdown(value=get_db_status())

        db_status_state = gr.State(value=get_db_status())

        # Persistent states for loading and results
        loading_state = gr.State(False)
        result_state = gr.State(None)

        with gr.Tabs():
            with gr.TabItem("Generate Diagram"):
                # Controls: preset & provider on one row, then the button below
                with gr.Row(elem_id="controls_row"):
                    preset = gr.Dropdown(choices=list(PRESETS.keys()), value="SimpleMLP", label="Preset Model")
                    provider = gr.Dropdown(choices=LLM_OPTIONS, value=LLM_OPTIONS[0], label="LLM Provider")
                with gr.Row():
                    generate_btn = gr.Button("Generate", variant="primary", elem_id="generate_btn")

                # Side-by-side: left column (input + latest TikZ), right column (logs)
                with gr.Row():
                    with gr.Column(scale=6, elem_id="code_col"):
                        code = gr.Code(label="PyTorch nn.Module code", language="python", value=PRESETS["SimpleMLP"], lines=20, max_lines=20)
                        latest_tikz = gr.Code(label="Latest TikZ Code", language="latex", value="% Latest TikZ will appear here during generation", lines=20, max_lines=20)
                    with gr.Column(scale=6, elem_id="logs_col"):
                        status = gr.Markdown(value="### Logs\nWaiting for output...", visible=True, elem_id="logs_panel")

                # Output preview and downloads in a card
                with gr.Column(elem_id="preview_card"):
                    pdf_viewer = gr.HTML(label="Preview (JPEG if available else PDF/TikZ)")
                    download_files = gr.File(label="Downloads (JPEG/PDF/TikZ)", file_count="multiple", elem_id="downloads")

                def _ensure_code(preset_choice, current_code):
                    return PRESETS[preset_choice] if preset_choice and PRESETS.get(preset_choice) else current_code

                def set_loading():
                    return gr.update(visible=True, value="Loading..."), True, None

                def generate(preset_choice, code_text, provider_choice):
                    # Streaming generator for Gradio
                    log_accum = []
                    # Relay logs
                    for evt in render_graph_stream(code_text, provider_choice, want_jpeg=True):
                        if isinstance(evt, dict) and evt.get("type") == "log":
                            log_accum.append(evt.get("text", ""))
                            logs_md = "### Logs\n" + "\n\n".join(log_accum)
                            yield gr.update(), gr.update(), None, gr.update(value=logs_md, visible=True), True, "\n\n".join(log_accum)
                        elif isinstance(evt, dict) and evt.get("type") == "tikz":
                            tikz_text = evt.get("tikz", "") or "% (empty)"
                            yield gr.update(value=tikz_text), gr.update(), None, gr.update(), True, None
                        elif isinstance(evt, dict) and evt.get("type") == "final":
                            outputs = evt.get("outputs", {}) or {}
                            paths = save_outputs(outputs)
                            downloads = [p for k, p in paths.items() if k in ("jpeg", "pdf", "tex")]
                            status_text = "Generation Complete\n"
                            if "pdf" not in outputs:
                                status_text += " — PDF compilation unavailable (install tectonic or pdflatex)."
                            # Build preview
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

                            # Final UI update: preview, downloads, status markdown, loading False, result text
                            yield gr.update(), html_preview, downloads, gr.update(value=status_text, visible=True), False, status_text
                    return

                # When preset changes, update code
                preset.change(_ensure_code, [preset, code], [code])
                # When generate is clicked, set loading state, then run generate
                # Fast UI update should not claim a queue job; avoid extra SSE stream
                generate_btn.click(
                    set_loading,
                    [],
                    [status, loading_state, result_state],
                    queue=False
                )
                generate_btn.click(
                    generate,
                    [preset, code, provider],
                    [latest_tikz, pdf_viewer, download_files, status, loading_state, result_state],
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
        ## Citation
        If you use ArchGen in your research or teaching, please cite:

        ```
        @software{jiang_archgen_2025,
          author    = {Zhiheng Jiang},
          title     = {ArchGen: Automated Neural Network Architecture Diagram Generation},
          year      = {2025},
          url       = {https://github.com/jzh001/ArchGen},
          license   = {Apache-2.0},
          note      = {Version: latest}
        }
        ```

        ---
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

        # Reduce polling frequency to lower SSE churn (was 0.2s). Must remain inside Blocks context.
        timer = gr.Timer(2.0)
        timer.tick(get_db_status, [], [db_status_state])

        # When db status state changes, update visible markdown.
        db_status_state.change(update_display, [db_status_state], [db_status])

    return demo


if __name__ == "__main__":
    build_interface().launch()

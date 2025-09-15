"""Diagram rendering pipeline (PDF-focused with optional JPEG preview).

Produces compiled PDF (if LaTeX engine available) plus raw TikZ. Optionally can
return a JPEG raster (first page) if caller requests and conversion tools are present.
"""
from __future__ import annotations

from typing import Dict, Any, Generator
from llm.workflow import run as llm_workflow, run_stream as llm_workflow_stream
from tikzconvert import tikz_to_formats

def render_graph(input_code, provider_choice, want_jpeg: bool = False) -> Dict[str, bytes]:
    """Render TikZ -> PDF (+ optional JPEG) and raw TeX.

    Returns keys: tex (always), pdf (if compiled), jpeg (if requested & succeeded).
    """
    outputs: Dict[str, bytes] = {}
    try:
        tikz_doc = llm_workflow(input_code=input_code, provider_choice=provider_choice)
    except Exception:
        tikz_doc = "% TikZ generation failed"
    try:
        fmts = ["tikz", "pdf"]
        if want_jpeg:
            fmts.append("jpeg")
        tikz_formats = tikz_to_formats(tikz_doc, formats=tuple(fmts))
    except Exception:
        tikz_formats = {"tikz": tikz_doc.encode("utf-8")}
    if "tikz" in tikz_formats:
        outputs["tex"] = tikz_formats["tikz"]
    if "pdf" in tikz_formats:
        outputs["pdf"] = tikz_formats["pdf"]
    if want_jpeg and "jpeg" in tikz_formats:
        outputs["jpeg"] = tikz_formats["jpeg"]
    return outputs

def render_graph_stream(input_code, provider_choice, want_jpeg: bool = True) -> Generator[Dict[str, Any], None, None]:
    """Yield step-wise status logs and tikz updates, and finally compiled outputs.

    Yields dict events for the UI:
    - {"type": "log", "text": str}
    - {"type": "tikz", "tikz": str, "stage": "generated"|"compiled"}
    - Final: {"type": "final", "outputs": {tex/pdf/jpeg bytes present}}
    """
    print(f"[DEBUG] render_graph_stream called with input_code length: {len(input_code) if input_code else 0}, provider_choice: {provider_choice}")
    
    last_tikz = ""
    # Relay backend events directly and capture latest tikz
    for evt in llm_workflow_stream(input_code=input_code, provider_choice=provider_choice):
        if not isinstance(evt, dict):
            continue
        etype = evt.get("type")
        if etype == "log":
            text = evt.get("text", "")
            # Hide verbose LaTeX compile logs in the UI
            if text.startswith("[Compile Log]"):
                continue
            yield {"type": "log", "text": text}
        elif etype == "tikz":
            last_tikz = evt.get("tikz", last_tikz)
            # forward along with stage if provided
            out = {"type": "tikz", "tikz": last_tikz}
            if "stage" in evt:
                out["stage"] = evt["stage"]
            yield out
        elif etype == "final":
            last_tikz = evt.get("tikz", last_tikz)
        else:
            # Unknown; ignore
            pass

    # Convert TikZ to requested formats (best-effort)
    try:
        fmts = ["tikz", "pdf"]
        if want_jpeg:
            fmts.append("jpeg")
        conv = tikz_to_formats(last_tikz, formats=tuple(fmts)) if last_tikz else {"tikz": b"% empty"}
    except Exception as e:
        conv = {"tikz": (last_tikz or f"% error: {e}").encode("utf-8", errors="ignore")}
    outputs: Dict[str, bytes] = {}
    if "tikz" in conv:
        outputs["tex"] = conv["tikz"]
    if "pdf" in conv:
        outputs["pdf"] = conv["pdf"]
    if want_jpeg and "jpeg" in conv:
        outputs["jpeg"] = conv["jpeg"]

    yield {"type": "final", "outputs": outputs}

__all__ = ["render_graph", "render_graph_stream"]

"""Diagram rendering pipeline (PDF-focused with optional JPEG preview).

Produces compiled PDF (if LaTeX engine available) plus raw TikZ. Optionally can
return a JPEG raster (first page) if caller requests and conversion tools are present.
"""
from __future__ import annotations

from typing import Dict, Any
from llm.workflow import run as llm_workflow
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

__all__ = ["render_graph"]

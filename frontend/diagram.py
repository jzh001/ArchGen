"""Diagram rendering pipeline (PDF-focused).

Now produces only a compiled PDF (if LaTeX engine available) plus raw TikZ.
SVG preview removed per updated requirement.
"""
from __future__ import annotations

from typing import Dict, Any
from llm.workflow import run as llm_workflow  # placeholder LLM producing TikZ
from tikzconvert import tikz_to_formats

def render_graph(graph_ir: Dict[str, Any]) -> Dict[str, bytes]:
    """Render using TikZ -> PDF only; return {'pdf': bytes, 'tex': bytes}.

    If PDF compilation fails (no engine), only 'tex' is returned.
    """
    outputs: Dict[str, bytes] = {}
    try:
        tikz_doc = llm_workflow()
    except Exception:
        tikz_doc = "% TikZ generation failed"
    try:
        tikz_formats = tikz_to_formats(tikz_doc, formats=("tikz", "pdf"))
    except Exception:
        tikz_formats = {"tikz": tikz_doc.encode("utf-8")}
    if "tikz" in tikz_formats:
        outputs["tex"] = tikz_formats["tikz"]
    if "pdf" in tikz_formats:
        outputs["pdf"] = tikz_formats["pdf"]
    return outputs

__all__ = ["render_graph"]

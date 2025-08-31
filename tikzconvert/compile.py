"""Utilities to compile TikZ/LaTeX into PDF & SVG.

We try to be resilient: if LaTeX toolchain not installed, we still return the
raw TikZ source under key 'tikz' and skip others.

Strategy (progressive enhancement):
1. Normalize input into a full LaTeX document (standalone class) if needed.
2. Write to temp directory main.tex
3. Prefer `tectonic` (single self-contained engine) if available for PDF.
4. Else try `latexmk` -> PDF, else 2x `pdflatex`.
5. For SVG try (in order):
    a. `dvisvgm` (requires producing DVI via `latex`)
    b. `pdf2svg` (PDF -> SVG)
    c. `pdftocairo -svg` (poppler)
6. Gracefully fall back to only raw TikZ if none succeed.

Given deployment constraints (HF Spaces CPU), absence of toolchain is common; we degrade gracefully.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Dict, Iterable, List, Tuple

class TikzConversionError(Exception):
    pass

_MIN_DOC = r"""\documentclass[tikz,border=5pt]{standalone}
\usetikzlibrary{positioning}
\begin{document}
%s
\end{document}
"""

def _which(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def _ensure_document(tikz_source: str) -> str:
    if "\\documentclass" in tikz_source:
        return tikz_source
    # assume snippet (maybe contains just tikzpicture or not)
    if "\\begin{tikzpicture}" not in tikz_source:
        tikz_source = f"\\begin{{tikzpicture}}\n{tikz_source}\n\\end{{tikzpicture}}"
    return _MIN_DOC % tikz_source

def _run(cmd: List[str], cwd: str) -> Tuple[bool, bytes]:
    try:
        cp = subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=70)
        return True, cp.stdout
    except Exception as e:
        return False, getattr(e, 'output', b'') or b''

def _compile_pdf(td: str) -> Tuple[bool, str, bytes]:
    """Attempt multiple backends; return (ok, pdf_path, log)."""
    pdf_path = os.path.join(td, "main.pdf")
    log_all = b''
    # tectonic first
    if _which("tectonic"):
        ok, out = _run(["tectonic", "--keep-intermediates", "--outdir", td, "main.tex"], td)
        log_all += out
        if ok and os.path.exists(pdf_path):
            return True, pdf_path, log_all
    # latexmk
    if _which("latexmk"):
        ok, out = _run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], td)
        log_all += out
        if ok and os.path.exists(pdf_path):
            return True, pdf_path, log_all
    # pdflatex fallback
    if _which("pdflatex"):
        for _ in range(2):
            ok, out = _run(["pdflatex", "-interaction=nonstopmode", "main.tex"], td)
            log_all += out
        if os.path.exists(pdf_path):
            return True, pdf_path, log_all
    return False, pdf_path, log_all

def _produce_svg_from_pdf(td: str, pdf_path: str) -> Tuple[bool, bytes]:
    svg_candidate = os.path.join(td, "main.svg")
    # dvisvgm path (needs latex -> dvi)
    if _which("dvisvgm") and _which("latex"):
        ok_latex, _ = _run(["latex", "-interaction=nonstopmode", "main.tex"], td)
        dvi_path = os.path.join(td, "main.dvi")
        if ok_latex and os.path.exists(dvi_path):
            ok_svg, _ = _run(["dvisvgm", "main.dvi", "-n", "-o", "main.svg"], td)
            if ok_svg and os.path.exists(svg_candidate):
                return True, open(svg_candidate, "rb").read()
    # pdf2svg
    if _which("pdf2svg"):
        ok, _ = _run(["pdf2svg", pdf_path, svg_candidate], td)
        if ok and os.path.exists(svg_candidate):
            return True, open(svg_candidate, "rb").read()
    # pdftocairo
    if _which("pdftocairo"):
        ok, _ = _run(["pdftocairo", "-svg", pdf_path, svg_candidate], td)
        # pdftocairo may append -1.svg
        if not os.path.exists(svg_candidate):
            alt = os.path.join(td, "main-1.svg")
            if os.path.exists(alt):
                svg_candidate = alt
        if ok and os.path.exists(svg_candidate):
            return True, open(svg_candidate, "rb").read()
    return False, b''

def tikz_to_formats(tikz_source: str, formats: Iterable[str] = ("tikz", "pdf", "svg")) -> Dict[str, bytes]:
    wanted = list(dict.fromkeys(formats))  # preserve order unique
    outputs: Dict[str, bytes] = {"tikz": tikz_source.encode("utf-8")}
    need_pdf = any(f in ("pdf", "svg") for f in wanted)
    if not need_pdf:
        return {k: v for k, v in outputs.items() if k in wanted}

    doc = _ensure_document(tikz_source)
    with tempfile.TemporaryDirectory(prefix="archgen_tikz_") as td:
        with open(os.path.join(td, "main.tex"), "w", encoding="utf-8") as f:
            f.write(doc)
        ok_pdf, pdf_path, _ = _compile_pdf(td)
        if ok_pdf and os.path.exists(pdf_path):
            if "pdf" in wanted:
                outputs["pdf"] = open(pdf_path, "rb").read()
            if "svg" in wanted:
                ok_svg, svg_bytes = _produce_svg_from_pdf(td, pdf_path)
                if ok_svg:
                    outputs["svg"] = svg_bytes
        # else fall back silently

    return {k: v for k, v in outputs.items() if k in wanted}

__all__ = ["tikz_to_formats", "TikzConversionError"]

"""Utilities to compile TikZ/LaTeX into PDF (& optional JPEG raster).

Resilient conversion: if LaTeX toolchain isn't present we still return only the
raw TikZ source (key 'tikz'). If PDF compiles, we can optionally derive a JPEG
preview using whatever external converter happens to be installed.

Strategy (progressive enhancement):
1. Normalize input into a full LaTeX standalone document if needed.
2. Write `main.tex` in a temporary directory.
3. Attempt PDF via (in order) `tectonic`, `latexmk`, `pdflatex`.
4. If JPEG requested, attempt (in order) `pdftoppm -jpeg`, `pdftocairo -jpeg`,
   ImageMagick (`magick` / `convert`), Ghostscript (`gs`). First success wins.
5. Gracefully fall back; never raise unless an unexpected internal error occurs.
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

def _produce_jpeg_from_pdf(td: str, pdf_path: str) -> Tuple[bool, bytes]:
    """Try to rasterize first page of the PDF into a JPEG.

    We intentionally avoid adding Python deps; rely on common CLI tools.
    Returns (ok, bytes).
    """
    # 1. pdftoppm (poppler)
    if _which("pdftoppm"):
        # Limit to first page to avoid accidental multi-page output
        ok, _ = _run(["pdftoppm", "-jpeg", "-f", "1", "-l", "1", pdf_path, "main"], td)
        if ok:
            # pdftoppm writes main-1.jpg (unless singlefile option available)
            cand = os.path.join(td, "main.jpg")
            if not os.path.exists(cand):
                cand = os.path.join(td, "main-1.jpg")
            if os.path.exists(cand):
                return True, open(cand, "rb").read()
    # 2. pdftocairo
    if _which("pdftocairo"):
        # pdftocairo outputs main-1.jpg for first page unless -singlefile present
        ok, _ = _run(["pdftocairo", "-jpeg", pdf_path, "main"], td)
        if ok:
            cand = os.path.join(td, "main.jpg")
            if not os.path.exists(cand):
                cand = os.path.join(td, "main-1.jpg")
            if os.path.exists(cand):
                return True, open(cand, "rb").read()
    # 3. ImageMagick
    if _which("magick") or _which("convert"):
        tool = "magick" if _which("magick") else "convert"
        ok, _ = _run([tool, "-density", "200", pdf_path, "-quality", "90", "main.jpg"], td)
        if ok:
            cand = os.path.join(td, "main.jpg")
            if os.path.exists(cand):
                return True, open(cand, "rb").read()
    # 4. Ghostscript
    if _which("gs"):
        ok, _ = _run([
            "gs", "-sDEVICE=jpeg", "-dBATCH", "-dNOPAUSE", "-dSAFER", "-r200",
            "-sOutputFile=main.jpg", pdf_path
        ], td)
        if ok:
            cand = os.path.join(td, "main.jpg")
            if os.path.exists(cand):
                return True, open(cand, "rb").read()
    return False, b""

def tikz_to_formats(tikz_source: str, formats: Iterable[str] = ("tikz", "pdf")) -> Dict[str, bytes]:
    wanted = list(dict.fromkeys(formats))  # preserve order unique
    outputs: Dict[str, bytes] = {"tikz": tikz_source.encode("utf-8")}
    need_pdf = any(f in ("pdf", "jpeg") for f in wanted)
    log_bytes = b''
    if not need_pdf:
        return {k: v for k, v in outputs.items() if k in wanted}

    doc = _ensure_document(tikz_source)
    with tempfile.TemporaryDirectory(prefix="archgen_tikz_") as td:
        with open(os.path.join(td, "main.tex"), "w", encoding="utf-8") as f:
            f.write(doc)
        ok_pdf, pdf_path, log_bytes = _compile_pdf(td)
        outputs["log"] = log_bytes  # Always include log, even if PDF fails
        if ok_pdf and os.path.exists(pdf_path):
            if "pdf" in wanted:
                outputs["pdf"] = open(pdf_path, "rb").read()
            if "jpeg" in wanted:
                ok_jpeg, jpeg_bytes = _produce_jpeg_from_pdf(td, pdf_path)
                if ok_jpeg:
                    outputs["jpeg"] = jpeg_bytes
        # else fall back silently

    return {k: v for k, v in outputs.items() if k in wanted or k == "log"}

__all__ = ["tikz_to_formats", "TikzConversionError"]

"""TikZ conversion package.

Converts a TikZ/LaTeX snippet or document into PDF (and optionally JPEG raster)
while always returning the raw TikZ source.

Notes:
- If a standalone LaTeX document is not detected we wrap the snippet.
- JPEG generation is opportunistic (uses external CLI tools if present) and may be absent.
"""
from .compile import tikz_to_formats, TikzConversionError

__all__ = ["tikz_to_formats", "TikzConversionError"]

"""TikZ conversion package.

Converts a TikZ/LaTeX document or snippet into other formats (SVG, PDF).

MVP constraints:
- Avoid system LaTeX dependency on Hugging Face Spaces by using an optional lightweight approach.
- If a full standalone LaTeX document is provided (has \documentclass), we attempt to compile.
- If only a tikzpicture environment is provided, we wrap it in a minimal preamble.
- Compilation uses a temporary directory and returns bytes for requested formats.

Future:
- Caching, error reporting improvements, TikZ -> PNG (via dvisvgm + rsvg or pillow), async worker.
"""
from .compile import tikz_to_formats, TikzConversionError

__all__ = ["tikz_to_formats", "TikzConversionError"]

from llm.agent import Agent
from constants import RUBRICS_PROMPT_PATH, GENERATOR_PROMPT_PATH, CRITIC_PROMPT_PATH, MAX_ITER
from tikzconvert.compile import tikz_to_formats
import re, base64, shutil, tempfile, os
from llm.tools import search_tikz_database

def run(input_code: str, provider_choice: str) -> str:
    """Run the generator-critic loop with rendering and self-approval.

    Process:
    - Generator produces TikZ.
    - We attempt to compile to JPEG. If it fails, feed this back to the generator to fix.
    - If it compiles, we ask the generator to self-assess the rendered image,
      reworking until the generator sets approval=true.
    - Then we pass the final JPEG (base64) to the critic for an external critique. If the critic rejects, we
      feed back the critique to the generator and continue.

    We dynamically extend MAX_ITER locally to keep looping until success (with a reasonable safety bound).
    """
    with open(RUBRICS_PROMPT_PATH, 'r') as f:
        rubrics = f.read()

    tikz_code = ""
    jpeg_b64 = ""
    iteration = 0
    max_iter = MAX_ITER  # will be increased whenever we need more attempts

    # Initial ask to the generator
    msg_to_generator = (
        f"Here is the content to depict as a TikZ diagram:\n{input_code}\n\n"
        "Return ONLY the TikZ/LaTeX source inside a single fenced code block labelled 'latex' like:\n"
        "```latex\n... code ...\n```\n"
        "No surrounding prose."
    )

    tools = [search_tikz_database]

    # Hard safety ceiling to avoid truly infinite loops in pathological cases
    safety_ceiling = MAX_ITER + 25
    generator_agent = Agent(
        GENERATOR_PROMPT_PATH,
        rubrics=rubrics,
        provider_choice=provider_choice,
        tools=tools,
    )

    critic_agent = Agent(
        CRITIC_PROMPT_PATH,
        rubrics=rubrics,
        provider_choice=provider_choice,
        tools=tools,
    )

    # print("[Generator Prompt] ", generator_agent.messages[0])
    # print("[Critic Prompt] ", critic_agent.messages[0])

    # Detect whether a LaTeX toolchain / rasterizer is available in the runtime.
    # If not present (common when a Spaces runtime doesn't include TeX), we
    # short-circuit the compile->fix loop to avoid infinite retries: return
    # the generator's TikZ source after the first successful generation.
    def _latex_available() -> bool:
        return any(shutil.which(x) for x in ("tectonic", "latexmk", "pdflatex"))

    def _rasterizer_available() -> bool:
        return any(shutil.which(x) for x in ("pdftoppm", "pdftocairo", "magick", "convert", "gs"))

    def _pillow_available():
        try:
            import PIL.Image as PILImage  # type: ignore
            return PILImage
        except Exception:
            return None

    def _make_tikz_variants(raw: str):
        """Return the TikZ content as-is. No escaping/normalization needed with code fences."""
        return [("as_is", raw)]

    compile_possible = _latex_available()
    raster_possible = _rasterizer_available()
    if not compile_possible:
        print("[workflow] No LaTeX engine detected in PATH. Will skip compile/critic loop and return TikZ source when produced.")

    while iteration < max_iter and iteration < safety_ceiling:
        iteration += 1

        # 1) Ask generator to produce TikZ
        ai_msg = generator_agent.invoke(msg_to_generator, image=jpeg_b64 if jpeg_b64 else None)
        print("[Generator]", ai_msg)
        tikz_code = extract_tikz_code(ai_msg)

        # Build cautious transformation variants for compile attempts
        variants = _make_tikz_variants(tikz_code) if tikz_code else []

        if not tikz_code:
            # No code produced—ask for a retry with explicit notice
            msg_to_generator = (
                "Your previous response did not include a fenced LaTeX block. "
                "Please respond with ONLY one code fence labelled 'latex' containing the full, compilable diagram.\n\n"
                f"Original input to depict:\n{input_code}"
            )
            print("No LaTeX fenced block found in generator response; retrying.")
            max_iter += 1
            continue

        # 2) Try compiling to JPEG (if possible in this runtime)
        if not compile_possible:
            # We cannot compile here (no TeX toolchain). Return the generated TikZ
            # as the best-effort result to avoid looping forever in Spaces.
            print("No LaTeX toolchain detected; skipping compile/critic loop and returning TikZ source.")
            return tikz_code

        # Attempt compile over variants; accept JPEG if available; otherwise accept PDF if rasterizer missing
        chosen_variant = None
        outputs = {}
        compile_error_log = ""
        last_log = ""
        for tag, variant_code in variants:
            try:
                outputs = tikz_to_formats(variant_code, formats=("jpeg", "pdf", "tikz"))
            except Exception as e:
                last_log = str(e)
                outputs = {"log": last_log.encode("utf-8", errors="ignore")}

            # Capture log if present
            if "log" in outputs:
                try:
                    last_log = outputs["log"].decode("utf-8", errors="replace")
                except Exception:
                    last_log = str(outputs["log"]) if outputs.get("log") is not None else last_log

            if "jpeg" in outputs and outputs.get("jpeg"):
                chosen_variant = (tag, variant_code)
                break
            # If no rasterizer is available, accept a successful PDF as success path
            if not raster_possible and ("pdf" in outputs and outputs.get("pdf")):
                chosen_variant = (tag, variant_code)
                break

        if not chosen_variant:
            compile_error_log = last_log or "No detailed error log available."
            # Compilation failed; ask generator to fix and include the error log
            msg_to_generator = (
                "The TikZ code failed to compile. Please correct any LaTeX/TikZ errors and return a new fenced LaTeX block.\n"
                "Focus on syntactic correctness first (missing packages, unmatched braces, environments, math delimiters).\n\n"
                f"Here was your last TikZ source:\n{tikz_code}\n"
                f"\n--- TikZ Compile Error Log ---\n{compile_error_log}\n"
            )
            max_iter += 1
            print("TikZ code failed to compile to JPEG/PDF; asking generator to fix.")
            continue

        # Update tikz_code to the successfully compiled variant
        tikz_code = chosen_variant[1]

        # 3) We have a JPEG or at least a PDF (if rasterizer missing)
        jpeg_bytes = outputs.get("jpeg", b"")
        jpeg_b64 = base64.b64encode(jpeg_bytes).decode("ascii") if jpeg_bytes else ""

        # Check aspect ratio of the image
        PILImage = _pillow_available()
        if jpeg_b64 and PILImage is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpeg") as temp_jpeg:
                temp_jpeg.write(jpeg_bytes)
                temp_jpeg_path = temp_jpeg.name

            try:
                with PILImage.open(temp_jpeg_path) as img:
                    width, height = img.size
                    aspect_ratio = max(width / height, height / width)
                    if aspect_ratio > 5:
                        msg_to_generator = (
                            "The generated image has an extreme aspect ratio exceeding 5:1 or 1:5. Please adjust the TikZ code to produce a more balanced diagram.\n\n"
                            f"Last TikZ source:\n{tikz_code}\n"
                        )
                        max_iter += 1
                        continue
            finally:
                os.unlink(temp_jpeg_path)

        # 4) Ask external Critic (with the final image)
        critic_prompt = (
            ("The final rendered diagram will be provided as a base64 JPEG (separate attachment) with its TikZ source.\n"
             if jpeg_b64 else
             "No JPEG is attached (rasterizer not available). Base your critique primarily on the TikZ source and compilation feasibility.\n")
            + "Provide a brief critique and concrete suggestions in plain text. If you approve the diagram with no further changes, include a line with exactly: APPROVED. Otherwise, do not include that word.\n\n"
            + "TikZ code:\n"
            + f"{tikz_code}\n"
            + "Original input code:\n"
            + f"{input_code}\n"
        )
        ai_msg = critic_agent.invoke(critic_prompt, image=jpeg_b64 if jpeg_b64 else None)
        print("[Critic]", ai_msg)
        if contains_approved(ai_msg):
            return tikz_code

        # If critic rejected, loop back with the critic's full feedback
        msg_to_generator = (
            "External critic feedback indicates issues remain. Please revise the diagram accordingly.\n\n"
            + ai_msg.strip() +
            "\n\nReturn ONLY a single fenced LaTeX block (```latex ... ```)."
        )
        max_iter += 1

    # If we exit the loop without approval, return the last TikZ (best effort)
    return tikz_code

def extract_tikz_code(ai_msg: str) -> str:
    """Extract LaTeX from a ```latex fenced block (or any fenced block as fallback)."""
    if not ai_msg:
        return ""
    m = re.search(r"```latex\s*([\s\S]*?)```", ai_msg)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"```\s*([\s\S]*?)```", ai_msg)
    if m2:
        return m2.group(1).strip()
    return ""

def contains_approved(text: str) -> bool:
    """Return True if text contains a standalone APPROVED line."""
    if not text:
        return False
    return bool(re.search(r"(^|\n)APPROVED(\s|$)", text))
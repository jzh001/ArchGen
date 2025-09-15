from llm.agent import Agent
from constants import RUBRICS_PROMPT_PATH, GENERATOR_PROMPT_PATH, CRITIC_PROMPT_PATH, MAX_ITER
from tikzconvert.compile import tikz_to_formats
import re, base64, shutil, tempfile, os
from llm.tools import search_tikz_database

# Global flag to terminate the workflow
terminate_workflow = False

def stop_workflow():
    """Set the global flag to terminate the workflow."""
    global terminate_workflow
    terminate_workflow = True

def reset_workflow_termination():
    """Reset the global flag after the workflow ends."""
    global terminate_workflow
    terminate_workflow = False

def run_stream(input_code: str, provider_choice: str):
    """Stream the generator-critic loop events for the frontend.

    Yields dict events:
    - {"type": "log", "text": str} at the end of each major step (generator/compile/critic)
    - Final yield: {"type": "final", "tikz": str}
    """
    print(f"[DEBUG] run_stream called with input_code length: {len(input_code) if input_code else 0}, provider_choice: {provider_choice}")
    
    # Reset the termination flag at the start of each workflow
    global terminate_workflow
    terminate_workflow = False
    
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
    print(f"[DEBUG] About to create generator_agent with provider: {provider_choice}")
    
    generator_agent = Agent(
        GENERATOR_PROMPT_PATH,
        rubrics=rubrics,
        provider_choice=provider_choice,
        tools=tools,
    )
    print(f"[DEBUG] Generator agent created successfully")

    critic_agent = Agent(
        CRITIC_PROMPT_PATH,
        rubrics=rubrics,
        provider_choice=provider_choice,
        tools=tools,
    )
    print(f"[DEBUG] Critic agent created successfully")

    # print("[Generator Prompt] ", generator_agent.messages[0])
    # print("[Critic Prompt] ", critic_agent.messages[0])

    # Detect whether a LaTeX toolchain / rasterizer is available in the runtime.
    # If not present (common when a Spaces runtime doesn't include TeX), we
    # short-circuit the compile->fix loop to avoid infinite retries: return
    # the generator's TikZ source after the first successful generation.
    def _latex_available() -> bool:
        paths = [shutil.which(x) for x in ("tectonic", "latexmk", "pdflatex")]
        print("[DEBUG] LaTeX toolchain paths:", paths)
        return any(paths)

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
    print(f"[DEBUG] compile_possible: {compile_possible}, raster_possible: {raster_possible}")
    
    if not compile_possible:
        yield {"type": "log", "text": "[workflow] No LaTeX engine detected in PATH. Skipping compile/critic loop; will return TikZ when produced."}

    print(f"[DEBUG] About to enter workflow loop. max_iter: {max_iter}, safety_ceiling: {safety_ceiling}")
    print(f"[DEBUG] terminate_workflow flag: {terminate_workflow}")
    
    # Add logging to confirm LLM invocation
    while iteration < max_iter and iteration < safety_ceiling:
        if terminate_workflow:
            yield {"type": "log", "text": "[workflow] Termination requested. Using the latest TikZ code."}
            break

        iteration += 1

        # Log the message being sent to the generator
        print(f"[DEBUG] Message to generator (iteration {iteration}):\n{msg_to_generator}")

        # 1) Ask generator to produce TikZ
        yield {"type": "log", "text": f"[Generator] Requesting TikZ (iteration {iteration})..."}
        try:
            ai_msg = generator_agent.invoke(msg_to_generator, image=jpeg_b64 if jpeg_b64 else None)
            print(f"[DEBUG] Response from generator (iteration {iteration}):\n{ai_msg}")
        except Exception as e:
            print(f"[ERROR] LLM invocation failed (iteration {iteration}): {e}")
            yield {"type": "log", "text": f"[ERROR] LLM invocation failed: {e}"}
            break

        yield {"type": "log", "text": f"[Generator]\n{ai_msg}"}
        tikz_code = extract_tikz_code(ai_msg)
        if tikz_code:
            # Stream the current TikZ from generator before compile
            yield {"type": "tikz", "tikz": tikz_code, "stage": "generated"}

        # If a stop was requested during or right after generation, exit early with latest TikZ
        if terminate_workflow:
            yield {"type": "log", "text": "[workflow] Stop requested after generation. Skipping compile and returning latest TikZ."}
            break

        # Build cautious transformation variants for compile attempts
        variants = _make_tikz_variants(tikz_code) if tikz_code else []

        compile_error_log = ""
        last_log = ""
        outputs = {}
        chosen_variant = None
        jpeg_bytes = b""
        # If no TikZ code detected, go to critic with error indication
        if not tikz_code:
            critic_prompt = (
                "Error: No LaTeX fenced block detected in generator response.\n\n"
                f"Original generator response:\n{ai_msg}\n\n"
                f"Original input to depict:\n{input_code}\n"
                "Please provide feedback and actionable suggestions for the generator to improve."
            )
            ai_msg_critic = critic_agent.invoke(critic_prompt)
            yield {"type": "log", "text": f"[Critic]\n{ai_msg_critic}"}
            if contains_approved(ai_msg_critic):
                # Approve returning raw message if critic surprisingly approved
                yield {"type": "final", "tikz": ai_msg}
                return
            # If not approved, loop back with critic feedback
            msg_to_generator = (
                "External critic feedback indicates issues remain. Please revise the diagram accordingly.\n\n"
                + ai_msg_critic.strip() +
                "\n\nReturn ONLY a single fenced LaTeX block (```latex ... ```)."
            )
            max_iter += 1
            continue

        # 2) Try compiling to JPEG (if possible in this runtime)
        if compile_possible:
            for tag, variant_code in variants:
                if terminate_workflow:
                    yield {"type": "log", "text": "[workflow] Stop requested before compile. Skipping compile."}
                    break
                try:
                    yield {"type": "log", "text": f"[Compile] Attempting variant '{tag}'..."}
                    outputs = tikz_to_formats(variant_code, formats=("jpeg", "pdf", "tikz"))
                except Exception as e:
                    last_log = str(e)
                    outputs = {"log": last_log.encode("utf-8", errors="ignore")}

                # Log the LaTeX error messages if compilation fails
                if "log" in outputs:
                    try:
                        last_log = outputs["log"].decode("utf-8", errors="replace")
                    except Exception:
                        last_log = str(outputs["log"]) if outputs.get("log") is not None else last_log
                    print(f"[DEBUG] LaTeX compilation log (variant '{tag}'):\n{last_log}")

                if "jpeg" in outputs and outputs.get("jpeg"):
                    chosen_variant = (tag, variant_code)
                    jpeg_bytes = outputs["jpeg"]
                    yield {"type": "log", "text": "[Compile] Success: JPEG produced."}
                    break
                # If no rasterizer is available, accept a successful PDF as success path
                if not raster_possible and ("pdf" in outputs and outputs.get("pdf")):
                    chosen_variant = (tag, variant_code)
                    yield {"type": "log", "text": "[Compile] Success: PDF produced (no rasterizer)."}
                    break

            if not chosen_variant:
                compile_error_log = last_log or "No detailed error log available."
                print(f"[DEBUG] Compilation failed for all variants. Last error log:\n{compile_error_log}")

        # If compilation failed or not possible, go to critic with error log
        if not chosen_variant:
            critic_prompt = (
                "TikZ code failed to compile.\n\n"
                f"TikZ source:\n{tikz_code}\n\n"
                f"--- TikZ Compile Error Log ---\n{compile_error_log or last_log}\n\n"
                f"Original input to depict:\n{input_code}\n"
                "Please provide feedback and actionable suggestions for the generator to improve."
            )
            ai_msg_critic = critic_agent.invoke(critic_prompt)
            yield {"type": "log", "text": f"[Critic]\n{ai_msg_critic}"}
            if contains_approved(ai_msg_critic):
                yield {"type": "final", "tikz": tikz_code}
                return
            # If not approved, loop back with critic feedback
            msg_to_generator = (
                "External critic feedback indicates issues remain. Please revise the diagram accordingly.\n\n"
                + ai_msg_critic.strip() +
                "\n\nReturn ONLY a single fenced LaTeX block (```latex ... ```)."
            )
            max_iter += 1
            continue

        # Update tikz_code to the successfully compiled variant
        tikz_code = chosen_variant[1]
        # Stream the compiled-accepted TikZ variant
        yield {"type": "tikz", "tikz": tikz_code, "stage": "compiled"}

        # 3) We have a JPEG or at least a PDF (if rasterizer missing)
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
                        yield {"type": "log", "text": f"[Quality] Extreme aspect ratio detected ({width}x{height}). Requesting generator to adjust."}
                        msg_to_generator = (
                            "The generated image has an extreme aspect ratio exceeding 5:1 or 1:5. Please adjust the TikZ code to produce a more balanced diagram.\n\n"
                            f"Last TikZ source:\n{tikz_code}\n"
                        )
                        max_iter += 1
                        # Defer file cleanup to finally; just loop again
                        continue
            finally:
                try:
                    if os.path.exists(temp_jpeg_path):
                        os.unlink(temp_jpeg_path)
                except Exception:
                    pass

        # If stop was requested after compile, return immediately with compiled TikZ
        if terminate_workflow:
            yield {"type": "log", "text": "[workflow] Stop requested after compile. Returning compiled TikZ without critique."}
            yield {"type": "final", "tikz": tikz_code}
            reset_workflow_termination()
            return

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
        # Respect stop before invoking critic
        if terminate_workflow:
            yield {"type": "log", "text": "[workflow] Stop requested before critic. Returning latest TikZ."}
            yield {"type": "final", "tikz": tikz_code}
            reset_workflow_termination()
            return

        ai_msg_critic = critic_agent.invoke(critic_prompt, image=jpeg_b64 if jpeg_b64 else None)
        yield {"type": "log", "text": f"[Critic]\n{ai_msg_critic}"}
        if contains_approved(ai_msg_critic):
            yield {"type": "final", "tikz": tikz_code}
            reset_workflow_termination()
            return

        # If critic rejected, loop back with the critic's full feedback
        msg_to_generator = (
            "External critic feedback indicates issues remain. Please revise the diagram accordingly.\n\n"
            + ai_msg_critic.strip() +
            "\n\nReturn ONLY a single fenced LaTeX block (```latex ... ```)."
        )
        max_iter += 1

    # If we exit the loop without approval, yield the last TikZ (best effort)
    yield {"type": "final", "tikz": tikz_code}
    
    # Reset the termination flag after the workflow ends
    reset_workflow_termination()
    return


def run(input_code: str, provider_choice: str) -> str:
    """Non-streaming wrapper that returns the final TikZ string.

    Internally consumes run_stream() and ignores intermediate logs.
    """
    final_tikz = ""
    for evt in run_stream(input_code=input_code, provider_choice=provider_choice):
        if isinstance(evt, dict) and evt.get("type") == "final":
            final_tikz = evt.get("tikz", "")
    return final_tikz

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
    """Return True if the critic indicates approval with uppercase keywords.

    Rules:
    - Case-sensitive: only match capitalized APPROVE or APPROVED as whole words.
    - Allow punctuation or whitespace boundaries (word boundaries cover this).
    - Avoid obvious uppercase negatives like NOT APPROVED / DISAPPROVED / DO NOT APPROVE.
    """
    if not text:
        return False

    t = text.strip()

    # Guard against explicit uppercase negatives
    negative_patterns_cs = [
        r"\bDISAPPROVED\b",
        r"\bNOT\s+APPROVED\b",
        r"\bDO\s+NOT\s+APPROVE(D)?\b",
        r"\bDON'T\s+APPROVE(D)?\b",
        r"\bCANNOT\s+APPROVE(D)?\b",
        r"\bWILL\s+NOT\s+APPROVE(D)?\b",
    ]
    for pat in negative_patterns_cs:
        if re.search(pat, t):
            return False

    # Positive: uppercase APPROVE or APPROVED, whole word, case-sensitive
    return bool(re.search(r"\bAPPROVE(D)?\b", t))
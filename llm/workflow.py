from llm.agent import Agent
from constants import RUBRICS_PROMPT_PATH, GENERATOR_PROMPT_PATH, CRITIC_PROMPT_PATH, MAX_ITER
from tikzconvert.compile import tikz_to_formats
import json, re, ast, base64, shutil

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
        f"Here is the code to depict:\n{input_code}\n\n"
        "Generate the TikZ code for the diagram. Output only the JSON as per the schema."
    )

    # Hard safety ceiling to avoid truly infinite loops in pathological cases
    safety_ceiling = MAX_ITER + 25
    generator_agent = Agent(
        GENERATOR_PROMPT_PATH,
        rubrics=rubrics,
        provider_choice=provider_choice,
    )

    critic_agent = Agent(
        CRITIC_PROMPT_PATH,
        rubrics=rubrics,
        provider_choice=provider_choice,
    )

    print("[Generator Prompt] ", generator_agent.messages[0])
    print("[Critic Prompt] ", critic_agent.messages[0])

    # Detect whether a LaTeX toolchain / rasterizer is available in the runtime.
    # If not present (common when a Spaces runtime doesn't include TeX), we
    # short-circuit the compile->fix loop to avoid infinite retries: return
    # the generator's TikZ source after the first successful generation.
    def _latex_available() -> bool:
        return any(shutil.which(x) for x in ("tectonic", "latexmk", "pdflatex"))

    def _rasterizer_available() -> bool:
        return any(shutil.which(x) for x in ("pdftoppm", "pdftocairo", "magick", "convert", "gs"))

    compile_possible = _latex_available()
    raster_possible = _rasterizer_available()
    if not compile_possible:
        print("[workflow] No LaTeX engine detected in PATH. Will skip compile/critic loop and return TikZ source when produced.")

    while iteration < max_iter and iteration < safety_ceiling:
        iteration += 1

        # 1) Ask generator to produce TikZ
        
        ai_msg = generator_agent.invoke(msg_to_generator, image=jpeg_b64 if jpeg_b64 else None)
        print("[Generator]", ai_msg)
        resp = extract_dict_from_json(ai_msg)
        tikz_code = resp.get("tikz_code", "")

        if not tikz_code:
            # No code produced—ask for a retry with explicit notice
            msg_to_generator = (
                f"The previous response did not include 'tikz_code'. Please return valid JSON with a 'tikz_code' field.\n\n"
                f"Original input to depict:\n{input_code}"
            )
            max_iter += 1
            continue

        # 2) Try compiling to JPEG (if possible in this runtime)
        if not compile_possible:
            # We cannot compile here (no TeX toolchain). Return the generated TikZ
            # as the best-effort result to avoid looping forever in Spaces.
            return tikz_code

        outputs = {}
        try:
            outputs = tikz_to_formats(tikz_code, formats=("jpeg", "tikz"))
        except Exception as e:
            print("TikZ compile raised an exception:", e)

        if "jpeg" not in outputs:
            # Compilation failed; ask generator to fix LaTeX/TikZ issues.
            msg_to_generator = (
                "The TikZ code failed to compile into a JPEG. Please correct any LaTeX/TikZ errors and return a new 'tikz_code'.\n"
                "Focus on syntactic correctness first (missing packages, unmatched braces, environments, math delimiters).\n\n"
                f"Here was your last 'tikz_code':\n{tikz_code}\n"
            )
            max_iter += 1
            continue

        # 3) We have a JPEG; convert to base64 for passing to LLMs
        jpeg_bytes = outputs.get("jpeg", b"")
        jpeg_b64 = base64.b64encode(jpeg_bytes).decode("ascii") if jpeg_bytes else ""
        if not jpeg_b64:
            # Unexpected; treat as compile failure
            msg_to_generator = (
                "Received no JPEG bytes after compilation. Please adjust the TikZ code for successful rendering and re-submit.\n\n"
                f"Last 'tikz_code':\n{tikz_code}\n"
            )
            max_iter += 1
            continue

        # 4) Ask external Critic (with the final image)
        critic_prompt = (
            "The final rendered diagram will be provided as a base64 JPEG (separate attachment) with its TikZ source.\n"
            "Provide critique and suggestions of the TikZ code. Approve only if it fully meets the rubrics.\n\n"
            "TikZ code:\n"
            f"{tikz_code}\n"
            "Original input code:\n"
            f"{input_code}\n"
        )
        ai_msg = critic_agent.invoke(critic_prompt, image=jpeg_b64)
        print("[Critic]", ai_msg)
        cr = extract_dict_from_json(ai_msg)
        final_approval = bool(cr.get("approval", False))
        if final_approval:
            return tikz_code

        # If critic rejected, loop back with critic feedback
        critique = cr.get("critique", "")
        suggestions = cr.get("suggestions", "")
        msg_to_generator = (
            f"External critic feedback indicates issues remain. You are provided with the image generated.\n"
            f"Critique: {critique}\n"
            f"Suggestions: {suggestions}\n\n"
            "Please revise and return a new 'tikz_code' (valid JSON only) that addresses all points."
        )
        max_iter += 1

    # If we exit the loop without approval, return the last TikZ (best effort)
    return tikz_code

def extract_dict_from_json(ai_msg: str) -> dict:
    """Try several strategies to extract a JSON object from the AI message.

    Strategies (in order):
    - direct json.loads
    - JSON inside a ```json ... ``` code fence
    - JSON inside any ``` ... ``` code fence
    - first '{' ... last '}' substring
    - ast.literal_eval on the substring (for Python-style dicts)
    - replacing single quotes with double quotes and json.loads

    Returns an empty dict on failure and prints a truncated diagnostic to help debugging.
    """
    if not ai_msg:
        return {}

    # Preprocess the input to normalize multiline strings, unescape quotes, and ensure valid JSON structure
    def normalize_json_input(input_str):
        # Remove newlines within JSON strings
        normalized = re.sub(r'(?<!\\)\n', ' ', input_str)
        # Replace escaped quotes with regular quotes
        normalized = normalized.replace('\\"', '"')
        # Remove extraneous whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

    ai_msg = normalize_json_input(ai_msg)

    # 1) direct parse
    try:
        return json.loads(ai_msg)
    except Exception:
        pass

    # 2) try to find a JSON block in a ```json code fence
    m = re.search(r"```json\s*(\{.*\})\s*```", ai_msg, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # 3) try a generic code fence
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", ai_msg, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # 4) try to extract first {...} substring
    start = ai_msg.find('{')
    end = ai_msg.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = ai_msg[start:end+1]
        try:
            return json.loads(candidate)
        except Exception:
            # 5) fallback to ast.literal_eval for non-strict JSON (single quotes, trailing commas, etc.)
            try:
                return ast.literal_eval(candidate)
            except Exception:
                pass

    # 6) try replacing single quotes with double quotes as a last-ditch effort
    candidate = ai_msg.strip().replace("'", '"')
    try:
        return json.loads(candidate)
    except Exception:
        pass

    # Give a helpful diagnostic for debugging
    preview = ai_msg[:1000].replace('\n', '\\n')
    print("Failed to parse JSON. Raw AI message (truncated):", preview)
    return {}
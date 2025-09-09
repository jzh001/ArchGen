from .agent import Agent
from .schema import TikZResponseFormatter, CritiqueResponseFormatter
from constants import RUBRICS_PROMPT_PATH, GENERATOR_PROMPT_PATH, CRITIC_PROMPT_PATH, MAX_ITER
import json, re, ast

def run(input_code: str, provider_choice: str) -> str:
    with open(RUBRICS_PROMPT_PATH, 'r') as f:
        rubrics = f.read()
    approval = False
    tikz_code = ""
    iteration = 0
    msg_to_generator = f"Here is the code: {input_code}\nGenerate the TikZ code for the diagram."
    while not approval and iteration < MAX_ITER:
        iteration += 1
        generator_agent = Agent(GENERATOR_PROMPT_PATH, schema=TikZResponseFormatter, rubrics=rubrics, provider_choice=provider_choice)
        ai_msg = generator_agent.invoke(msg_to_generator)
        print("[Generator]", ai_msg)
        tikz_code = extract_dict_from_json(ai_msg).get("tikz_code", "Error: No TikZ code found.")

        critic_agent = Agent(CRITIC_PROMPT_PATH, schema=CritiqueResponseFormatter, rubrics=rubrics, provider_choice=provider_choice)
        ai_msg = critic_agent.invoke(f"Here is the TikZ code: {tikz_code}\nProvide a critique of the code.")
        critique = extract_dict_from_json(ai_msg).get("critique", "Error: No critique found.")
        suggestions = extract_dict_from_json(ai_msg).get("suggestions", "Error: No suggestions found.")
        approval = extract_dict_from_json(ai_msg).get("approval", False)

        print("[Critic]", ai_msg)
        
        if not approval:
            msg_to_generator = f"{input_code}\nCritique: {critique}\nSuggestions: {suggestions}\nPlease improve the TikZ code based on the critique and suggestions."

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

    # 1) direct parse
    try:
        return json.loads(ai_msg)
    except Exception:
        pass

    # 2) try to find a JSON block in a ```json code fence
    m = re.search(r"```json\s*(\{.*?\})\s*```", ai_msg, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # 3) try a generic code fence
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", ai_msg, re.S)
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
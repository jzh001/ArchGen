from .agent import Agent
from .schema import TikZResponseFormatter
from constants import RUBRICS_PROMPT_PATH, GENERATOR_PROMPT_PATH
import json

def run(input_code: str, provider_choice: str) -> str:
    with open(RUBRICS_PROMPT_PATH, 'r') as f:
        rubrics = f.read()
    agent = Agent(GENERATOR_PROMPT_PATH, schema=TikZResponseFormatter, code=input_code, rubrics=rubrics, provider_choice=provider_choice)
    ai_msg = agent.invoke("Generate the TikZ code for the diagram.")
    tikz_code = extract_dict_from_json(ai_msg).get("tikz_code", "Error: No TikZ code found.")

    return tikz_code

def extract_dict_from_json(ai_msg: str) -> str:
    try:
        if isinstance(ai_msg, str):
            data = json.loads(ai_msg)
            return data
    except Exception as e:
        print("Failed to parse as JSON, extracting TikZ code from text.")
        return {}
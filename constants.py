RUBRICS_PROMPT_PATH = 'prompts/rubrics.txt'
GENERATOR_PROMPT_PATH = 'prompts/generator.txt'
CRITIC_PROMPT_PATH = 'prompts/critic.txt'
LLM_OPTIONS = [
    "ollama:gpt-oss:20b",
    # "ollama:qwen3:8b",
    "anthropic:claude-4-sonnet",
    "google-genai:gemini-2.5-flash",
    "google-genai:gemini-2.5-flash-lite",
]
MAX_ITER = 5
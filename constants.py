RUBRICS_PROMPT_PATH = 'prompts/rubrics.txt'
GENERATOR_PROMPT_PATH = 'prompts/generator.txt'
CRITIC_PROMPT_PATH = 'prompts/critic.txt'
LLM_OPTIONS = [
    # "ollama:gpt-oss:20b",
    # "ollama:qwen3:8b",
    # "ollama:qwen3:30b-a3b",
    "google-genai:gemini-2.5-flash",
    "google-genai:gemini-2.5-flash-lite",
    "google-genai:gemini-2.5-pro",
    # "anthropic:claude-4-sonnet",
    # "anthropic:claude-3-haiku",
]
MAX_ITER = 5
MAX_AGENT_ITER = 10
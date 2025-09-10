from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

def get_llm(llm_option: str):

    import os
    if llm_option == "anthropic:claude-4-sonnet":
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            max_tokens=5000,
            thinking={"type": "disabled"},
        )
    elif llm_option == "ollama:gpt-oss:20b":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(model="gpt-oss:20b", base_url=base_url)
    else:
        raise ValueError(f"Unknown llm_option: {llm_option}")

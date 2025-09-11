from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm(llm_option: str, tools: list = []):

    import os
    if llm_option == "anthropic:claude-4-sonnet":
        llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            max_tokens=5000,
            thinking={"type": "disabled"},
        )
    elif llm_option.startswith("ollama:"):
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model_name = llm_option[len("ollama:"):]
        llm = ChatOllama(
            model=model_name,
            base_url=base_url,
            max_tokens=5000,
            thinking={"type": "disabled"},
        )
    elif llm_option.startswith("google-genai:"):
        model_name = llm_option[len("google-genai:"):]
        llm = ChatGoogleGenerativeAI(
            model=model_name,
        )
    else:
        raise ValueError(f"Unknown llm_option: {llm_option}")

    # Bind tools only when provided and ensure we use the returned Runnable
    if tools:
        llm = llm.bind_tools(tools)
    return llm

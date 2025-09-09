from langchain.chat_models import init_chat_model
from langchain_ollama import ChatOllama

def get_llm(llm_option: str):

    import os
    if llm_option == "Anthropic":
        return init_chat_model("claude-3-5-haiku-latest", model_provider="anthropic")
    elif llm_option == "Ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(model="gpt-oss:20b", base_url=base_url)
    else:
        raise ValueError(f"Unknown llm_option: {llm_option}")

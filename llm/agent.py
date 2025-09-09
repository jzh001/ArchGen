from .select_llm import get_llm
from pydantic import BaseModel

class Agent:
    def __init__(self, instruction_prompt_path: str, schema: BaseModel, provider_choice: str, **kwargs):
        self.model = get_llm(provider_choice)
        self.schema = schema
        self.config = {"configurable": {"thread_id": "thread1"}}
        self.messages = []
        # Pass the actual schema definition (as a dict) to the prompt
        kwargs["schema"] = schema.schema()
        with open(instruction_prompt_path) as f:
            self.messages.append(f.read().format(**kwargs))

    def invoke(self, msg, image=None):
        # Build a single multimodal user message compatible with LangChain
        content_parts = [
            {"type": "text", "text": msg}
        ]
        if image:
            # Base64 image block (compatible with LangChain's multimodal schemas)
            content_parts.append(
                {
                    "type": "image",
                    "source_type": "base64",
                    "data": image,
                    "mime_type": "image/jpeg",
                }
            )
        input_message = {
            "role": "user",
            "content": content_parts,
        }
        # Do NOT persist the image to the long-term message history.
        # We'll send the image with this invocation only, and store only the text.
        text_only_message = {
            "role": "user",
            "content": [{"type": "text", "text": msg}],
        }

        try:
            # Send temporary message (with image if provided) without storing the image in history
            messages_for_model = self.messages + [input_message]
            ai_msg = self.model.invoke(messages_for_model, config=self.config).content
        except Exception as e:
            print("LLM invocation failed:", e)
            raise e

        # Persist only the text part of the user's message
        self.messages.append(text_only_message)
        self.messages.append({"role": "assistant", "content": ai_msg})

        return ai_msg
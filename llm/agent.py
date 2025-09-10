from llm.select_llm import get_llm
from pydantic import BaseModel
import json

class Agent:
    def __init__(self, instruction_prompt_path: str, schema: type[BaseModel], provider_choice: str, **kwargs):
        self.model = get_llm(provider_choice)
        self.schema = schema
        self.config = {"configurable": {"thread_id": "thread1"}}
        self.messages = []
        # Pass the actual schema definition (as a JSON string) to the prompt.
        # Prefer pydantic v2 API `model_json_schema()` and fall back to v1's `schema()` if needed.
        try:
            schema_dict = schema.model_json_schema()
        except Exception:
            # Fallback for pydantic v1 or unexpected errors when calling v2 API
            schema_dict = schema.schema()

        # Dump schema as JSON string for prompt readability
        schema_json = json.dumps(schema_dict, indent=2)

        # Read template and safely insert schema JSON without letting
        # str.format() interpret braces inside the JSON.
        with open(instruction_prompt_path) as f:
            template_text = f.read()

        # Use a unique placeholder token unlikely to appear in templates
        SCHEMA_TOKEN = "__SCHEMA_JSON_PLACEHOLDER__"

        if "{schema}" in template_text:
            # Remove schema from kwargs to avoid double-insertion
            kwargs_without_schema = {k: v for k, v in kwargs.items() if k != "schema"}
            # Temporarily replace the placeholder, format the rest, then inject raw JSON
            templ_with_token = template_text.replace("{schema}", SCHEMA_TOKEN)
            formatted = templ_with_token.format(**kwargs_without_schema)
            final_prompt = formatted.replace(SCHEMA_TOKEN, schema_json)
        else:
            # No {schema} placeholder; just format normally (if other placeholders exist)
            final_prompt = template_text.format(**kwargs)

        self.messages.append(final_prompt)

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
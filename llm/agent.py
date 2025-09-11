from llm.select_llm import get_llm
import re

class Agent:
    def __init__(self, instruction_prompt_path: str, provider_choice: str, **kwargs):
        self.model = get_llm(provider_choice, tools = [])
        self.config = {"configurable": {"thread_id": "thread1"}}
        self.messages = []

        with open(instruction_prompt_path) as f:
            template_text = f.read()

        def safe_format(template, **kwargs):
            # Convert double braces to single braces first
            template = template.replace("{{", "{").replace("}}", "}")
            # Replace single braces only
            pattern = re.compile(r'(?<!{){(\w+)}(?!})')
            def replacer(match):
                key = match.group(1)
                return str(kwargs.get(key, match.group(0)))
            
            return pattern.sub(replacer, template)

        self.instruction_prompt = safe_format(template_text, **kwargs)
        self.kwargs = kwargs

        self.messages.append(self.instruction_prompt)

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

        # Prepare text-only message for history
        text_only_message = {
            "role": "user",
            "content": [{"type": "text", "text": msg}],
        }

        # --- RAG integration ---
        # Import perform_rag here to avoid circular imports
        from vector_db.rag import perform_rag
        rag_query = msg
        rag_query += f"\n[Input Code]\n{self.kwargs.get('input_code', '')}\n" if self.kwargs.get('input_code') else ""
        rag_context = perform_rag(rag_query)
        # If RAG returns non-empty, append as context
        if rag_context and isinstance(rag_context, str) and rag_context.strip():
            content_parts.append({
                "type": "text",
                "text": f"[RAG TikZ Examples]\n------\n{rag_context}\n------"
            })

        input_message = {
            "role": "user",
            "content": content_parts,
        }

        try:
            # Send temporary message (with image and RAG context if provided) without storing the image or RAG in history
            messages_for_model = self.messages + [input_message]
            ai_msg = self.model.invoke(messages_for_model, config=self.config).content
        except Exception as e:
            print("LLM invocation failed:", e)
            raise e

        # Persist only the text part of the user's message
        self.messages.append(text_only_message)
        self.messages.append({"role": "assistant", "content": ai_msg})

        return ai_msg
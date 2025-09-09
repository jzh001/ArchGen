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

    def invoke(self, msg):
        self.messages.append(msg)
        input_message = {
            "role": "user",
            "content": msg,
        }
        self.messages.append(input_message)

        try:
            ai_msg = self.model.invoke(self.messages, config=self.config).content
        except Exception as e:
            print("LLM invocation failed:", e)
            raise e

        return ai_msg
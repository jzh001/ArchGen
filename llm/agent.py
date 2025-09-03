from langchain.chat_models import init_chat_model
from pydantic import BaseModel

class Agent:
    def __init__(self, instruction_prompt_path: str, schema: BaseModel, **kwargs):
        self.model = init_chat_model("anthropic:claude-3-5-haiku-latest")
        self.model = self.model.with_structured_output(schema)

        self.config = {"configurable": {"thread_id": "thread1"}}

        self.messages = []

        with open(instruction_prompt_path) as f:
            self.messages.append(f.read().format(**kwargs))

    def invoke(self, msg):
        self.messages.append(msg)
        input_message = {
            "role": "user",
            "content": msg,
        }
        self.messages.append(input_message)

        ai_msg = self.model.invoke(self.messages, config=self.config)

        return ai_msg.tikz_code
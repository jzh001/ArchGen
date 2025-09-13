from llm.select_llm import get_llm
import re
from llm.tools import search_tikz_database
from constants import MAX_AGENT_ITER
from typing import List
import json


class Agent:
    def __init__(self, instruction_prompt_path: str, provider_choice: str, tools: list = [], **kwargs):
        self.model = get_llm(provider_choice, tools=tools)
        self.config = {"configurable": {"thread_id": "thread1"}}

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

        # Keep messages as simple role/content dicts
        self.messages: List[dict] = [
            {"role": "system", "content": [{"type": "text", "text": self.instruction_prompt}]}
        ]

    @staticmethod
    def _extract_text(content):
        """Safely extract text from LangChain content (list or str)."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for p in content:
                if isinstance(p, dict) and p.get("type") == "text":
                    parts.append(p.get("text", ""))
                elif isinstance(p, str):
                    parts.append(p)
            return "".join(parts)
        if isinstance(content, dict):
            # Some tools return dict with 'content'
            return str(content.get("content", content))
        return str(content)

    def invoke(self, msg, image=None):
        # Build a single multimodal user message using LangChain message parts.
        content_parts = [{"type": "text", "text": msg}]
        if image:
            # Prefer OpenAI-style image_url with data URL, which LangChain adapters normalize
            data_url = f"data:image/jpeg;base64,{image}"
            content_parts.append({"type": "image_url", "image_url": {"url": data_url}})

        input_message = {"role": "user", "content": content_parts}

        try:
            # Copy the existing conversation state
            messages_for_model: List[dict] = list(self.messages) + [input_message]
            iterations = 0
            final_ai_message = None

            while iterations < MAX_AGENT_ITER:
                response = self.model.invoke(messages_for_model, config=self.config)
                tool_calls = getattr(response, "tool_calls", None) or []

                if not tool_calls:
                    # Model returned a regular assistant message
                    final_ai_message = response
                    break

                # Otherwise: model issued tool calls. First, preserve the assistant
                # message that initiated these calls, so the subsequent turn sees
                # the correct context (prevents repeated re-calling of tools).
                # Always coerce to a minimal assistant dict to avoid provider-specific objects
                coerced = {
                    "role": "assistant",
                    "content": getattr(response, "content", "") or "",
                }
                # If tool_calls exist, include them for providers that inspect history
                if tool_calls:
                    coerced["tool_calls"] = tool_calls
                messages_for_model.append(coerced)

                # Execute tools and append normalized tool messages
                for tool_call in tool_calls:
                    # tool_call is expected to be a dict with keys: name, args, id
                    tool_name = None
                    tool_args = {}
                    tool_id = None
                    if isinstance(tool_call, dict):
                        tool_name = str(tool_call.get("name", "")).lower()
                        tool_args = tool_call.get("args", {}) or {}
                        tool_id = tool_call.get("id")
                    else:
                        # Fallback for unexpected structures
                        try:
                            tool_name = str(getattr(tool_call, "name", "")).lower()
                            tool_args = getattr(tool_call, "args", {}) or {}
                            tool_id = getattr(tool_call, "id", None)
                        except Exception:
                            tool_name = None

                    tool_map = {"search_tikz_database": search_tikz_database}
                    selected_tool = tool_map.get(tool_name)

                    if selected_tool is None:
                        tool_result_text = f"Error: unknown tool '{tool_name}'"
                    else:
                        # Invoke the tool with its parsed arguments
                        try:
                            if isinstance(tool_args, str):
                                try:
                                    tool_args = json.loads(tool_args)
                                except Exception:
                                    tool_args = {"query": tool_args}
                            elif not isinstance(tool_args, dict):
                                tool_args = {"query": str(tool_args)}

                            # Minimal arg normalization for our known tool
                            if tool_name == "search_tikz_database":
                                if "query" not in tool_args and "input" in tool_args:
                                    tool_args["query"] = tool_args.pop("input")
                            raw_tool_output = selected_tool.invoke(tool_args)
                        except Exception as e:
                            raw_tool_output = f"Tool execution error: {e}"
                        tool_result_text = self._extract_text(raw_tool_output)

                    # Append a tool role message for the model
                    # Prefer OpenAI-style plain string content for tool messages
                    tool_msg = {"role": "tool", "content": tool_result_text}
                    if tool_id:
                        tool_msg["tool_call_id"] = tool_id
                    if tool_name:
                        tool_msg["name"] = tool_name
                    messages_for_model.append(tool_msg)

                iterations += 1

            if iterations >= MAX_AGENT_ITER:
                print(f"Reached MAX_AGENT_ITER={MAX_AGENT_ITER} without completing tool calls.")

            # Fallback if we didn’t get a proper assistant message
            if final_ai_message is None:
                for m in reversed(messages_for_model):
                    if isinstance(m, dict) and m.get("role") == "assistant":
                        final_ai_message = m
                        break

            # Extract assistant text safely
            if final_ai_message is None:
                ai_msg_content = ""
            else:
                raw_content = getattr(final_ai_message, "content", None)
                if raw_content is None and isinstance(final_ai_message, dict):
                    raw_content = final_ai_message.get("content")
                ai_msg_content = self._extract_text(raw_content)

        except Exception as e:
            print("LLM invocation failed:", e)
            raise e

        # Persist the user and assistant messages in history
        self.messages.append(input_message)
        self.messages.append({"role": "assistant", "content": [{"type": "text", "text": ai_msg_content}]})
        return ai_msg_content

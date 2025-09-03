from pydantic import BaseModel, Field
class TikZResponseFormatter(BaseModel):
    """Always use this tool to structure your response to the user."""
    tikz_code: str = Field(description="TikZ Code")
    # explanation: str = Field(description="explanation")
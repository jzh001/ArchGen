from pydantic import BaseModel, Field
class TikZResponseFormatter(BaseModel):
    """Output ONLY a valid JSON object matching this schema, with the TikZ code in the 'tikz_code' field."""
    tikz_code: str = Field(description="TikZ Code")
    # explanation: str = Field(description="explanation")
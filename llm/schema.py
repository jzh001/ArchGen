from pydantic import BaseModel, Field

class TikZResponseFormatter(BaseModel):
    """Output ONLY a valid JSON object matching this schema, with the TikZ code in the 'tikz_code' field."""
    tikz_code: str = Field(description="TikZ Code")
    # explanation: str = Field(description="explanation")

class CritiqueResponseFormatter(BaseModel):
    """Output ONLY a valid JSON object matching this schema, with the critique in the 'critique' field, suggestions in the 'suggestions' field, and approval in the 'approval' field."""
    critique: str = Field(description="Critique of the provided TikZ code")
    suggestions: str = Field(description="Suggestions for improvement")
    approval: bool = Field(description="Whether the TikZ code is approved or not")
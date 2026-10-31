from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    context: str | None = None


class ResearchSummary(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    summary: str = Field(min_length=1)

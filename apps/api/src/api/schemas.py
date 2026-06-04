from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class SourceOut(BaseModel):
    n: int
    title: str
    ref: str
    url: str
    source_type: str

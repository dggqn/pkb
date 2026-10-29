from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

class NoteCreate(BaseModel):
    content: str

class NoteCreated(BaseModel):
    id: str
    status: str


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    created_at: datetime


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank")
        return value


class QuerySource(BaseModel):
    note_id: str
    content: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[QuerySource]

from datetime import datetime

from pydantic import BaseModel, ConfigDict

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

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Note
from app.schemas import NoteCreate, NoteCreated, NoteRead


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Personal Knowledge Base API", lifespan=lifespan)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return a simple status check for the API."""
    return {"status": "ok"}
@app.post("/notes", response_model=NoteCreated)
def create_note(note: NoteCreate, db: Session = Depends(get_db)) -> NoteCreated:
    """Persist a note and return its identifier."""
    record = Note(content=note.content)
    db.add(record)
    db.commit()
    db.refresh(record)
    return NoteCreated(id=record.id, status="saved")


@app.get("/notes/{note_id}", response_model=NoteRead)
def get_note(note_id: str, db: Session = Depends(get_db)) -> NoteRead:
    record = db.get(Note, note_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return record


# if __name__ == "__main__":
#     main()

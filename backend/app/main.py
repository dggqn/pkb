from contextlib import asynccontextmanager
import re
from hashlib import sha256

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Note, NoteChunk
from app.schemas import (
    NoteCreate,
    NoteCreated,
    NoteRead,
    QueryRequest,
    QueryResponse,
    QuerySource,
)
from app.services.chunking import split_into_chunks

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Personal Knowledge Base API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return a simple status check for the API."""
    return {"status": "ok"}
@app.post("/notes", response_model=NoteCreated)
def create_note(note: NoteCreate, db: Session = Depends(get_db)) -> NoteCreated:
    """Save the original note and its text chunks in one transaction."""
    content = note.content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Note content must not be blank",
        )

    try:
        record = Note(content=content)
        db.add(record)

        # 先把原笔记写入当前事务，生成 record.id；这里还没有 commit。
        db.flush()

        chunks = split_into_chunks(content)
        db.add_all(
            [
                NoteChunk(
                    note_id=record.id,
                    chunk_index=index,
                    content=chunk,
                    content_hash=sha256(chunk.encode("utf-8")).hexdigest(),
                    index_status="pending",
                )
                for index, chunk in enumerate(chunks)
            ]
        )

        # 原笔记和所有片段一起提交。
        db.commit()
        db.refresh(record)

        return NoteCreated(id=record.id, status="saved")
    except Exception:
        db.rollback()
        raise

@app.get("/notes/{note_id}", response_model=NoteRead)
def get_note(note_id: str, db: Session = Depends(get_db)) -> NoteRead:
    record = db.get(Note, note_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return record


@app.post("/query", response_model=QueryResponse)
def query_knowledge(request: QueryRequest, db: Session = Depends(get_db)) -> QueryResponse:
    """Find notes with overlapping terms and return them as answer context."""
    terms = _query_terms(request.question)
    if not terms:
        return QueryResponse(answer="问题中没有可用于检索的关键词。", sources=[])

    notes = db.scalars(select(Note).order_by(Note.created_at.desc())).all()
    ranked: list[tuple[int, Note]] = []
    for note in notes:
        content = note.content.casefold()
        score = sum(content.count(term.casefold()) for term in terms)
        if score:
            ranked.append((score, note))
    ranked.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
    sources = [QuerySource(note_id=note.id, content=note.content) for _, note in ranked[:5]]

    if not sources:
        answer = "我暂时没有在你的笔记中找到与这个问题相关的内容。"
    else:
        excerpts = "\n".join(f"- {source.content}" for source in sources)
        answer = f"找到以下可能相关的笔记：\n{excerpts}"
    return QueryResponse(answer=answer, sources=sources)


def _query_terms(question: str) -> list[str]:
    """Extract basic Latin words and Chinese character bigrams for MVP search."""
    terms: list[str] = []
    for chunk in re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+", question.casefold()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", chunk):
            terms.extend(chunk[index : index + 2] for index in range(len(chunk) - 1))
            if len(chunk) == 1:
                terms.append(chunk)
        else:
            terms.append(chunk)
    return list(dict.fromkeys(terms))


# if __name__ == "__main__":
#     main()

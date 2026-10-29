from contextlib import asynccontextmanager
from hashlib import sha256
from threading import Lock, Thread
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)
# 启动恢复和新笔记索引共用这把锁，避免同时处理同一批 pending chunks。
_indexing_lock = Lock()

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, get_db

from app.models import Note, NoteChunk

from app.schemas import (
    NoteCreate,
    NoteCreated,
    NoteRead,
    QueryRequest,
    QueryResponse,
    QuerySource,
)
from app.services.hybrid_search import retrieve_hybrid_chunks
from app.services.llm import generate_answer
from app.services.chunking import split_into_chunks
from app.services.chunk_indexing import (
    index_pending_chunks,
    index_pending_chunks_to_elasticsearch,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    # 先确保数据库表已就绪，再启动积压索引恢复。
    Base.metadata.create_all(bind=engine)

    # 在线程中恢复，避免模型加载或索引请求拖住 API 启动。
    recovery_thread = Thread(
        target=index_pending_chunks_in_background,
        name="pending-index-recovery",
        daemon=True,
    )
    recovery_thread.start()

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
def index_pending_chunks_in_background() -> None:
    """用独立数据库会话分别处理两路 pending 索引。"""
    # 启动恢复任务可能正好遇到新笔记请求，使用锁让索引任务依次执行。
    with _indexing_lock:
        db = SessionLocal()
        try:
            # 分开捕获两路错误：Qdrant 整体不可用时，仍继续尝试 ES。
            try:
                qdrant_result = index_pending_chunks(db)
                logger.info("Qdrant 后台索引结果：%s", qdrant_result)
            except Exception:
                db.rollback()
                logger.exception("Qdrant 后台索引任务失败")

            try:
                es_result = index_pending_chunks_to_elasticsearch(db)
                logger.info("Elasticsearch 后台索引结果：%s", es_result)
            except Exception:
                db.rollback()
                logger.exception("Elasticsearch 后台索引任务失败")
        finally:
            db.close()
@app.post("/notes", response_model=NoteCreated)
def create_note(note: NoteCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> NoteCreated:
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
        # 先持久化笔记和 chunks，再安排后台索引，避免索引读取到未提交数据。
        background_tasks.add_task(index_pending_chunks_in_background)
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
def query_knowledge(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    """通过全文与向量混合检索笔记，并返回命中的片段作为来源。"""
    try:
        # 先多取一些候选，再在服务内融合 ES 与 Qdrant 的排名。
        chunks = retrieve_hybrid_chunks(
            db,
            request.question,
            candidate_limit=10,
            result_limit=5,
        )
    except Exception as exc:
        # 检索服务暂时不可用时返回明确的服务错误；
        # 原始异常仍会保留在服务端日志中，便于排查。
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="检索服务暂时不可用，请稍后重试。",
        ) from exc

    # 按 note_id 合并命中的片段，保证每篇笔记在来源列表中只出现一次。
    # 字典保留首次插入顺序，因此来源仍按混合检索排名排列。
    chunks_by_note: dict[str, list[str]] = {}
    for chunk in chunks:
        chunks_by_note.setdefault(chunk.note_id, []).append(chunk.content)

    sources = [
        QuerySource(
            note_id=note_id,
            content="\n…\n".join(contents),
        )
        for note_id, contents in chunks_by_note.items()
    ]

    if not sources:
        return QueryResponse(
            answer="我暂时没有在你的笔记中找到相关内容。",
            sources=[],
        )

    try:
        # 将融合检索得到的来源片段交给大模型组织答案。
        # 上下文顺序与前端来源列表一致，方便对应模型给出的资料编号。
        answer, cited_source_indexes = generate_answer(
            request.question,
            [source.content for source in sources],
        )
    except Exception as exc:
        # 模型服务异常时返回服务不可用，详细原因留在后端日志中。
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="答案生成服务暂时不可用，请稍后重试。",
        ) from exc

    # 只把答案明确引用的资料返回给前端，避免把召回到但没有用于回答的
    # 候选笔记展示成“参考来源”。generate_answer 已将答案中的资料序号
    # 重排为连续编号，因此这里按引用顺序选择对应来源即可。
    sources = [
        sources[index - 1]
        for index in cited_source_indexes
    ]

    return QueryResponse(answer=answer, sources=sources)

# if __name__ == "__main__":
#     main()

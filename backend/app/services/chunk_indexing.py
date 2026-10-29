from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NoteChunk
from qdrant_client import models as qdrant_models

from app.services.embedding import embed_document
from app.services.vector_store import (
    COLLECTION_NAME,
    ensure_collection,
    get_qdrant_client,
)
from app.services.search_store import (
    INDEX_NAME,
    get_elasticsearch_client,
)

def get_pending_chunks(
    db: Session,
    *,
    limit: int = 100,
) -> list[NoteChunk]:
    """按创建顺序读取一批待索引 chunk。"""
    if limit <= 0:
        raise ValueError("limit must be positive")

    statement = (
        select(NoteChunk)
        .where(NoteChunk.index_status == "pending")
        .order_by(
            NoteChunk.created_at,
            NoteChunk.note_id,
            NoteChunk.chunk_index,
        )
        .limit(limit)
    )
    return list(db.scalars(statement).all())
#
def index_pending_chunks(db: Session, *, limit: int = 100) -> dict:
    """将一批 pending chunks 写入 Qdrant，成功后更新 MySQL 状态。"""
    chunks = get_pending_chunks(db, limit=limit)
    chunk_ids = [chunk.id for chunk in chunks]
    # 队列为空时无需连接 Qdrant，也避免启动时产生无用网络请求。
    if not chunk_ids:
        return {"processed": 0, "indexed": 0, "failed": []}

    client = get_qdrant_client()
    ensure_collection(client)

    indexed = 0
    failed: list[dict[str, str]] = []

    for chunk_id in chunk_ids:
        chunk = db.get(NoteChunk, chunk_id)
        if chunk is None or chunk.index_status != "pending":
            continue

        try:
            vector = embed_document(chunk.content)
            if len(vector) != 1024:
                raise ValueError(
                    f"Expected 1024 vector dimensions, got {len(vector)}"
                )

            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    qdrant_models.PointStruct(
                        id=chunk.id,
                        vector=vector,
                        payload={
                            "note_id": chunk.note_id,
                            "chunk_index": chunk.chunk_index,
                            "content_hash": chunk.content_hash,
                        },
                    )
                ],
                wait=True,
            )

            # Qdrant 写入成功后，才提交 MySQL 状态。
            chunk.index_status = "indexed"
            db.commit()
            indexed += 1
        except Exception as exc:
            db.rollback()
            failed.append({"chunk_id": chunk_id, "error": str(exc)})

    return {
        "processed": len(chunk_ids),
        "indexed": indexed,
        "failed": failed,
    }

def get_pending_es_chunks(
    db: Session,
    *,
    limit: int = 100,
) -> list[NoteChunk]:
    """按创建顺序读取一批待写入 Elasticsearch 的 chunk。"""
    if limit <= 0:
        raise ValueError("limit must be positive")

    statement = (
        select(NoteChunk)
        .where(NoteChunk.es_status == "pending")
        .order_by(
            NoteChunk.created_at,
            NoteChunk.note_id,
            NoteChunk.chunk_index,
        )
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def index_pending_chunks_to_elasticsearch(
    db: Session,
    *,
    limit: int = 100,
) -> dict:
    """将 pending chunks 写入 Elasticsearch，成功后更新 ES 状态。"""
    chunks = get_pending_es_chunks(db, limit=limit)
    chunk_ids = [chunk.id for chunk in chunks]
    # 队列为空时无需连接 Qdrant，也避免启动时产生无用网络请求。
    if not chunk_ids:
        return {"processed": 0, "indexed": 0, "failed": []}
    client = get_elasticsearch_client()


    indexed = 0
    failed: list[dict[str, str]] = []

    for chunk_id in chunk_ids:
        chunk = db.get(NoteChunk, chunk_id)
        if chunk is None or chunk.es_status != "pending":
            continue

        try:
            client.index(
                index=INDEX_NAME,
                id=chunk.id,
                document={
                    "note_id": chunk.note_id,
                    "chunk_index": chunk.chunk_index,
                    "content_hash": chunk.content_hash,
                    "content": chunk.content,
                },
            )

            # ES 写入成功后才提交 ES 状态。
            chunk.es_status = "indexed"
            db.commit()
            indexed += 1
        except Exception as exc:
            db.rollback()
            failed.append({"chunk_id": chunk_id, "error": str(exc)})

    return {
        "processed": len(chunk_ids),
        "indexed": indexed,
        "failed": failed,
    }
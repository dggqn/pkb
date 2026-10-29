from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NoteChunk
from app.services.embedding import embed_query
from app.services.search_store import INDEX_NAME, get_elasticsearch_client
from app.services.vector_store import COLLECTION_NAME, get_qdrant_client


def retrieve_hybrid_chunks(
    db: Session,
    question: str,
    *,
    candidate_limit: int = 10,
    result_limit: int = 5,
) -> list[NoteChunk]:
    """从 ES 和 Qdrant 各自召回候选，融合排序后回 MySQL 读取 chunk 原文。"""
    if candidate_limit <= 0 or result_limit <= 0:
        raise ValueError("candidate_limit and result_limit must be positive")

    # 用 UUID 作为统一候选 ID，并记录两路检索各自的名次。
    # RRF 只比较排名，不直接混用 ES 和向量检索的原始分数。
    rankings: list[list[str]] = []

    # ES 负责全文匹配，使用已配置好的 IK search analyzer。
    es = get_elasticsearch_client()
    es_response = es.search(
        index=INDEX_NAME,
        query={"match": {"content": {"query": question}}},
        size=candidate_limit,
    )
    rankings.append(
        [hit["_id"] for hit in es_response["hits"]["hits"]]
    )

    # Qdrant 负责语义匹配；查询向量使用 BGE 的 query 指令前缀。
    query_vector = embed_query(question)
    qdrant = get_qdrant_client()
    vector_response = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=candidate_limit,
        with_payload=False,
    )
    rankings.append([str(point.id) for point in vector_response.points])

    # Reciprocal Rank Fusion：某个 chunk 在任一路排名越靠前，融合分越高。
    # 常数 60 是 RRF 的平滑项，避免只因名次相差一位就产生过大分差。
    rrf_k = 60
    fused_scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + (
                1.0 / (rrf_k + rank)
            )

    ranked_ids = [
        chunk_id
        for chunk_id, _ in sorted(
            fused_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:result_limit]
    ]
    if not ranked_ids:
        return []

    # 检索索引只负责找 ID；最终内容从 MySQL 读取，保持 MySQL 为事实来源。
    chunks = db.scalars(
        select(NoteChunk).where(NoteChunk.id.in_(ranked_ids))
    ).all()
    chunks_by_id = {chunk.id: chunk for chunk in chunks}

    # SQL 的 IN 查询不保证返回顺序，因此按融合排名重新排列。
    return [
        chunks_by_id[chunk_id]
        for chunk_id in ranked_ids
        if chunk_id in chunks_by_id
    ]
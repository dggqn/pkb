import os

from qdrant_client import QdrantClient, models


COLLECTION_NAME = "pkb_chunks"
VECTOR_SIZE = 1024


def get_qdrant_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    return QdrantClient(url=url)


def ensure_collection(client: QdrantClient) -> None:
    if client.collection_exists(COLLECTION_NAME):
        info = client.get_collection(COLLECTION_NAME)
        vector_config = info.config.params.vectors

        if not isinstance(vector_config, models.VectorParams):
            raise ValueError(
                f"Collection {COLLECTION_NAME!r} must use a single dense vector"
            )

        if vector_config.size != VECTOR_SIZE:
            raise ValueError(
                f"Collection {COLLECTION_NAME!r} has vector size "
                f"{vector_config.size}; expected {VECTOR_SIZE}"
            )

        if vector_config.distance != models.Distance.COSINE:
            raise ValueError(
                f"Collection {COLLECTION_NAME!r} must use Cosine distance"
            )

        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE,
        ),
    )
import os
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch


load_dotenv(Path(__file__).resolve().parents[2] / "docker" / ".env")

INDEX_NAME = "pkb_chunks"

# 链接es服务
def get_elasticsearch_client() -> Elasticsearch:
    """用来连接 Elasticsearch 并确认连接可用"""
    url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    client = Elasticsearch(url, request_timeout=10)

    if not client.ping():
        raise ConnectionError(f"Cannot connect to Elasticsearch at {url}")

    return client

#
def ensure_index(client: Elasticsearch) -> None:
    """确保全文检索索引已经准备好：如果 INDEX_NAME 指定的索引已存在，
    就直接返回；如果不存在，就创建它，并配置中文分词规则和字段类型。"""
    if client.indices.exists(index=INDEX_NAME):
        return

    client.indices.create(
        index=INDEX_NAME,
        settings={
            "analysis": {
                "analyzer": {
                    "pkb_index": {
                        "type": "custom",
                        "tokenizer": "ik_max_word",
                        "filter": ["lowercase"],
                    },
                    "pkb_search": {
                        "type": "custom",
                        "tokenizer": "ik_smart",
                        "filter": ["lowercase"],
                    },
                }
            }
        },
        mappings={
            "properties": {
                "note_id": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "content_hash": {"type": "keyword"},
                "content": {
                    "type": "text",
                    "analyzer": "pkb_index",
                    "search_analyzer": "pkb_search",
                },
            }
        },
    )
import sys

from app.database import SessionLocal
from app.services.chunk_indexing import (
    index_pending_chunks,
    index_pending_chunks_to_elasticsearch,
)


def main() -> int:
    """分别重试两路 pending 索引，并用退出码报告是否仍有失败项。"""
    db = SessionLocal()
    results: dict[str, dict] = {}

    try:
        # 两路索引分开捕获异常，避免一路不可用时跳过另一路。
        try:
            results["qdrant"] = index_pending_chunks(db)
        except Exception as exc:
            # 整体连接或 collection 初始化失败时，记录错误并继续 ES。
            db.rollback()
            results["qdrant"] = {"error": str(exc)}

        try:
            results["elasticsearch"] = (
                index_pending_chunks_to_elasticsearch(db)
            )
        except Exception as exc:
            db.rollback()
            results["elasticsearch"] = {"error": str(exc)}
    finally:
        db.close()

    # 用明确的英文标记，避免 PowerShell 终端中文编码影响阅读。
    has_failures = False
    for index_name, result in results.items():
        print(f"{index_name.upper()}_RESULT={result}")

        # 单条失败或整路异常都让命令以非零状态结束，便于后续监控。
        if result.get("error") or result.get("failed"):
            has_failures = True

    return 1 if has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
# Backend 开发运行手册

## 环境配置

1. 复制 `backend/docker/.env.example` 为 `backend/docker/.env`（若 `.env` 已存在，保留现有数据库密码，只补齐缺少的变量）。
2. 在 `.env` 中填写数据库密码和 OpenAI 兼容服务提供的 Base URL、API key、模型名称。
3. `.env` 已由仓库根目录 `.gitignore` 忽略，不要提交真实密钥。

环境变量包括：

- MySQL：`MYSQL_ROOT_PASSWORD`、`MYSQL_DATABASE`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_PORT`
- Elasticsearch：`ELASTICSEARCH_PORT`、`ELASTICSEARCH_URL`
- Qdrant：`QDRANT_PORT`、`QDRANT_URL`
- 大模型：`OPENAI_BASE_URL`、`OPENAI_API_KEY`、`OPENAI_MODEL`

## 启动依赖服务

在仓库根目录运行：

```powershell
docker compose -f backend/docker/compose.yml up -d
docker compose -f backend/docker/compose.yml ps
```

Compose 文件位于 `backend/docker/compose.yml`，从根目录运行时必须显式指定 `-f`。

## 启动后端

在 `backend` 目录运行：

```powershell
uv sync
uv run uvicorn app.main:app --reload --port 8001
```

服务启动时会在后台扫描 MySQL 中两路索引状态为 `pending` 的 chunks，并分别尝试恢复到 Qdrant 和 Elasticsearch。查看启动日志中的 `Qdrant 后台索引结果` 与 `Elasticsearch 后台索引结果`。

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

## 添加笔记与索引

通过 `POST /notes` 保存成功后，FastAPI 后台任务会分别索引 Qdrant 和 Elasticsearch。MySQL 中的 `index_status` 与 `es_status` 分别记录两路结果；只有对应写入成功后才会标记为 `indexed`。

如果服务暂时不可用，失败项留在 `pending`，日志会记录错误。服务恢复后可以重启后端触发启动恢复；也可以在 `backend` 目录手动运行：

```powershell
uv run python -m app.services.retry_pending_indexes
```

恢复命令分别尝试两路，即使一路整体失败也会继续尝试另一路。有失败时命令返回非零退出码。

## 查询流程

`POST /query` 使用 Elasticsearch IK 全文检索和 Qdrant 向量检索召回候选，以 RRF 融合排名，再从 MySQL 读取 chunk 内容。检索结果交给配置的 OpenAI 兼容 API 生成回答，API 响应保留 `answer` 与 `sources`。

## 关键位置

- `app/services/chunking.py`：笔记切块
- `app/services/embedding.py`：本地 BGE 向量生成
- `app/services/chunk_indexing.py`：两路 pending 索引任务
- `app/services/retry_pending_indexes.py`：手动恢复入口
- `app/services/hybrid_search.py`：混合检索与 RRF 排序
- `app/services/llm.py`：OpenAI 兼容 API 调用
- `app/services/vector_store.py`：Qdrant collection 管理
- `app/services/search_store.py`：Elasticsearch 索引与 IK mapping

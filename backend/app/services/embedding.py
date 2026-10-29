from functools import lru_cache
from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer


MODEL_DIR = (
    Path(__file__).resolve().parents[2]
    / "docker"
    / "embedding"
    / "bge-large-zh-v1.5"
)
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


@lru_cache(maxsize=1)
def _load_model():
    if not MODEL_DIR.exists():
        raise FileNotFoundError(f"Embedding model not found: {MODEL_DIR}")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    tokenizer = AutoTokenizer.from_pretrained(
        str(MODEL_DIR),
        local_files_only=True,
    )
    model = AutoModel.from_pretrained(
        str(MODEL_DIR),
        local_files_only=True,
    )
    model.to(device)
    model.eval()

    return tokenizer, model, device


def embed_text(text: str, *, is_query: bool = False) -> list[float]:
    tokenizer, model, device = _load_model()

    if is_query:
        text = QUERY_INSTRUCTION + text

    inputs = tokenizer(
        text,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )
    inputs = {name: tensor.to(device) for name, tensor in inputs.items()}

    with torch.inference_mode():
        outputs = model(**inputs)
        # BGE 使用最后一层的 [CLS] 向量作为句子向量
        vector = outputs.last_hidden_state[:, 0]
        vector = F.normalize(vector, p=2, dim=1)

    return vector[0].cpu().tolist()


def embed_document(text: str) -> list[float]:
    return embed_text(text)


def embed_query(text: str) -> list[float]:
    return embed_text(text, is_query=True)
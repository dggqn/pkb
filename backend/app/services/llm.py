import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# 复用项目本地环境文件；API 密钥不写入源码。
load_dotenv(Path(__file__).resolve().parents[2] / "docker" / ".env")

_SOURCE_CITATION_RE = re.compile(r"\[资料\s*(\d+)\s*\]")
_INSUFFICIENT_EVIDENCE = "我暂时没有在你的笔记中找到足够依据回答这个问题。"


def _get_client_and_model() -> tuple[OpenAI, str]:
    """读取 OpenAI 兼容服务配置，并检查必要变量是否齐全。"""
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model_name = os.getenv("OPENAI_MODEL", "").strip()

    missing = [
        name
        for name, value in (
            ("OPENAI_BASE_URL", base_url),
            ("OPENAI_API_KEY", api_key),
            ("OPENAI_MODEL", model_name),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing model configuration: " + ", ".join(missing)
        )

    # OpenAI SDK 使用标准 Chat Completions 接口连接兼容服务。
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=60,
    )
    return client, model_name


def generate_answer(
    question: str,
    contexts: list[str],
) -> tuple[str, list[int]]:
    """生成带资料引用的答案，并返回实际引用的资料序号。"""
    if not contexts:
        return _INSUFFICIENT_EVIDENCE, []

    client, model_name = _get_client_and_model()

    # 为资料编号，方便模型在答案中标出依据，也对应前端的来源顺序。
    numbered_contexts = "\n\n".join(
        f"资料 {index}：\n{content}"
        for index, content in enumerate(contexts, start=1)
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是个人知识库助手。回答必须严格受限于用户提供的笔记资料。"
                    "每个事实性结论都要紧跟能直接支持该结论的资料编号，例如 [资料 1]；"
                    "只能引用实际支持答案的资料，不要为了说明资料无关而引用它。"
                    "不要列举、复述或展示不支持答案的候选资料。"
                    "若问题有多个部分，只回答资料能支持的部分，并明确指出其余部分"
                    "无法从笔记确定。尤其是问题把无关话题拼在一起时，也要逐项拆开判断："
                    "只要有一个子问题能被资料支持，就回答该子问题并引用它的资料；"
                    "不能因为另一个子问题无关而把整题都拒答。"
                    "资料只给出结论、没有解释原因时，不要自行补全原因。"
                    "若没有任何资料能支持问题的答案，明确说笔记中没有足够依据，"
                    "且不要引用任何资料。不要给资料中没有的建议、背景或推论。"
                    "引用必须使用单个有效编号，格式为 [资料 1]，不要使用编号范围。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"问题：\n{question}\n\n"
                    f"可参考的笔记资料：\n{numbered_contexts}"
                ),
            },
        ],
    )

    # 兼容服务可能返回空内容；显式报错，避免把空答案当作成功。
    answer = response.choices[0].message.content
    if not answer or not answer.strip():
        raise RuntimeError("The model returned an empty answer")

    answer = answer.strip()

    # 只把模型明确引用的资料交给前端。过滤前先检查编号，避免模型引用不存在的资料。
    citation_matches = list(_SOURCE_CITATION_RE.finditer(answer))
    cited_indexes = [int(match.group(1)) for match in citation_matches]
    if not cited_indexes:
        # 没有可验证的资料引用时，不能把未引用的自由回答当作有依据的答案返回。
        return _INSUFFICIENT_EVIDENCE, []

    if any(index < 1 or index > len(contexts) for index in cited_indexes):
        # 遇到越界引用时保守拒答，避免把错误编号映射到别的来源。
        return _INSUFFICIENT_EVIDENCE, []

    # 按回答中首次引用的顺序去重，并把答案中的编号改为连续编号。
    # 这样前端来源列表顺序可以和答案里的 [资料 N] 一一对应。
    ordered_indexes = list(dict.fromkeys(cited_indexes))
    renumbered = {
        original_index: new_index
        for new_index, original_index in enumerate(ordered_indexes, start=1)
    }

    def renumber_citation(match: re.Match[str]) -> str:
        original_index = int(match.group(1))
        return f"[资料 {renumbered[original_index]}]"

    answer = _SOURCE_CITATION_RE.sub(renumber_citation, answer)
    return answer, ordered_indexes

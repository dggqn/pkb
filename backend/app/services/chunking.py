import re


DEFAULT_CHUNK_SIZE = 350
DEFAULT_OVERLAP = 50


def split_into_chunks(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Split text at paragraph and sentence boundaries where possible."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and less than chunk_size")

    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", text)
    ]

    chunks: list[str] = []
    current = ""

    def emit_current() -> None:
        nonlocal current
        value = current.strip()
        if value:
            chunks.append(value)
        current = ""

    for paragraph in filter(None, paragraphs):
        sentences = re.split(r"(?<=[。！？.!?；;])", paragraph)
        for sentence in filter(None, (part.strip() for part in sentences)):
            # A single unusually long sentence needs character-based splitting.
            if len(sentence) > chunk_size:
                emit_current()
                start = 0
                while start < len(sentence):
                    end = start + chunk_size
                    piece = sentence[start:end].strip()
                    if piece:
                        chunks.append(piece)
                    if end >= len(sentence):
                        break
                    start = end - overlap
                continue

            candidate = f"{current}{sentence}" if not current else f"{current}{sentence}"
            if current and len(candidate) > chunk_size:
                previous = current.strip()
                emit_current()
                current = previous[-overlap:] if overlap else ""
                current += sentence
            else:
                current = candidate

        emit_current()

    return chunks
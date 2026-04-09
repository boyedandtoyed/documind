from dataclasses import dataclass
from typing import Generator
import re

@dataclass
class Chunk:
    text: str
    page: int | None
    index: int

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()

def sliding_window_chunks(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
    page: int | None = None,
) -> Generator[Chunk, None, None]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    if not words:
        return
    step = max(1, chunk_size - overlap)
    for i, start in enumerate(range(0, len(words), step)):
        chunk_words = words[start : start + chunk_size]
        if not chunk_words:
            break
        yield Chunk(text=" ".join(chunk_words), page=page, index=i)

def chunk_pdf(path: str, chunk_size: int = 512, overlap: int = 64) -> list[Chunk]:
    from pypdf import PdfReader
    reader = PdfReader(path)
    chunks: list[Chunk] = []
    for page_num, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        cleaned = clean_text(raw)
        if not cleaned:
            continue
        for chunk in sliding_window_chunks(cleaned, chunk_size, overlap, page=page_num):
            chunks.append(chunk)
    return chunks

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[Chunk]:
    cleaned = clean_text(text)
    return list(sliding_window_chunks(cleaned, chunk_size, overlap))

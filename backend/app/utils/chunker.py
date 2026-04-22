from __future__ import annotations

import re
from typing import List, Optional

from app.models.document import Chunk, ChunkMetadata


class SemanticChunker:
    """Semantic chunking with sliding window fallback."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._sentence_endings = re.compile(r"(?<=[.!?])\s+")

    def chunk_text(
        self,
        text: str,
        document_id: str,
        document_name: str,
        page_number: Optional[int] = None,
        start_char_offset: int = 0,
    ) -> List[Chunk]:
        """Split text into semantic chunks with overlap."""
        if not text.strip():
            return []

        sentences = self._split_into_sentences(text)
        chunks: List[Chunk] = []
        current_sentences: List[str] = []
        current_length = 0
        chunk_index = 0
        char_pos = start_char_offset

        for sentence in sentences:
            sentence_len = len(sentence)

            if current_length + sentence_len > self.chunk_size and current_sentences:
                chunk_text = " ".join(current_sentences)
                chunks.append(
                    self._make_chunk(
                        text=chunk_text,
                        document_id=document_id,
                        document_name=document_name,
                        chunk_index=chunk_index,
                        page_number=page_number,
                        start_char=char_pos,
                        end_char=char_pos + len(chunk_text),
                    )
                )
                chunk_index += 1
                char_pos += len(chunk_text) + 1

                # Sliding window overlap: keep last N chars worth of sentences
                overlap_sentences = self._get_overlap_sentences(current_sentences)
                current_sentences = overlap_sentences
                current_length = sum(len(s) for s in overlap_sentences)

            current_sentences.append(sentence)
            current_length += sentence_len

        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append(
                self._make_chunk(
                    text=chunk_text,
                    document_id=document_id,
                    document_name=document_name,
                    chunk_index=chunk_index,
                    page_number=page_number,
                    start_char=char_pos,
                    end_char=char_pos + len(chunk_text),
                )
            )

        return chunks

    def chunk_pages(
        self,
        pages: List[tuple[int, str]],
        document_id: str,
        document_name: str,
    ) -> List[Chunk]:
        """Chunk a multi-page document, tracking page numbers."""
        all_chunks: List[Chunk] = []
        offset = 0
        for page_num, page_text in pages:
            page_chunks = self.chunk_text(
                text=page_text,
                document_id=document_id,
                document_name=document_name,
                page_number=page_num,
                start_char_offset=offset,
            )
            all_chunks.extend(page_chunks)
            offset += len(page_text) + 1
        return all_chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        raw = self._sentence_endings.split(text)
        sentences: List[str] = []
        for s in raw:
            s = s.strip()
            if not s:
                continue
            # If sentence is still too long, split by newline then by token length
            if len(s) > self.chunk_size * 1.5:
                sentences.extend(self._hard_split(s))
            else:
                sentences.append(s)
        return sentences

    def _hard_split(self, text: str) -> List[str]:
        parts: List[str] = []
        words = text.split()
        current: List[str] = []
        current_len = 0
        for word in words:
            if current_len + len(word) > self.chunk_size:
                if current:
                    parts.append(" ".join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len += len(word) + 1
        if current:
            parts.append(" ".join(current))
        return parts

    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        overlap: List[str] = []
        total = 0
        for sentence in reversed(sentences):
            if total + len(sentence) > self.chunk_overlap:
                break
            overlap.insert(0, sentence)
            total += len(sentence) + 1
        return overlap

    @staticmethod
    def _make_chunk(
        text: str,
        document_id: str,
        document_name: str,
        chunk_index: int,
        page_number: Optional[int],
        start_char: int,
        end_char: int,
    ) -> Chunk:
        return Chunk(
            text=text,
            metadata=ChunkMetadata(
                document_id=document_id,
                document_name=document_name,
                chunk_index=chunk_index,
                page_number=page_number,
                start_char=start_char,
                end_char=end_char,
            ),
        )

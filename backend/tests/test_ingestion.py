"""Tests for document ingestion and chunking."""
from __future__ import annotations

import pytest

from app.utils.chunker import SemanticChunker


class TestSemanticChunker:
    def setup_method(self) -> None:
        self.chunker = SemanticChunker(chunk_size=200, chunk_overlap=30)

    def test_empty_text_returns_no_chunks(self) -> None:
        chunks = self.chunker.chunk_text("", document_id="doc1", document_name="test.txt")
        assert chunks == []

    def test_whitespace_only_returns_no_chunks(self) -> None:
        chunks = self.chunker.chunk_text("   \n\t  ", document_id="doc1", document_name="test.txt")
        assert chunks == []

    def test_short_text_produces_single_chunk(self) -> None:
        text = "This is a short document."
        chunks = self.chunker.chunk_text(text, document_id="doc1", document_name="test.txt")
        assert len(chunks) == 1
        assert chunks[0].text == text

    def test_long_text_produces_multiple_chunks(self) -> None:
        text = " ".join(["This is sentence number {}.".format(i) for i in range(50)])
        chunks = self.chunker.chunk_text(text, document_id="doc1", document_name="test.txt")
        assert len(chunks) > 1

    def test_chunks_preserve_document_metadata(self) -> None:
        text = "Hello world. This is a test document with multiple sentences."
        chunks = self.chunker.chunk_text(
            text, document_id="doc-123", document_name="myfile.pdf"
        )
        for chunk in chunks:
            assert chunk.metadata.document_id == "doc-123"
            assert chunk.metadata.document_name == "myfile.pdf"

    def test_page_number_preserved(self) -> None:
        pages = [(3, "Content on page three. More content here.")]
        chunks = self.chunker.chunk_pages(pages, document_id="doc1", document_name="doc.pdf")
        for chunk in chunks:
            assert chunk.metadata.page_number == 3

    def test_chunk_index_sequential(self) -> None:
        text = " ".join(["Sentence {}.".format(i) for i in range(30)])
        chunks = self.chunker.chunk_text(text, document_id="doc1", document_name="test.txt")
        indices = [c.metadata.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_text_is_stripped(self) -> None:
        text = "  Leading and trailing spaces.  More text here to make it longer.  "
        chunks = self.chunker.chunk_text(text, document_id="doc1", document_name="test.txt")
        for chunk in chunks:
            assert chunk.text == chunk.text.strip()

    def test_multi_page_document(self) -> None:
        pages = [
            (1, "Page one content. " * 20),
            (2, "Page two content. " * 20),
            (3, "Page three content. " * 20),
        ]
        chunks = self.chunker.chunk_pages(pages, document_id="doc1", document_name="doc.pdf")
        page_numbers = {c.metadata.page_number for c in chunks}
        assert page_numbers == {1, 2, 3}

    def test_hard_split_very_long_sentence(self) -> None:
        long_sentence = "word " * 300
        chunks = self.chunker.chunk_text(
            long_sentence, document_id="doc1", document_name="test.txt"
        )
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.text) <= self.chunker.chunk_size * 2

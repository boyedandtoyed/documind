from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

from app.models.document import Chunk, Document, DocumentStatus, DocumentType
from app.utils.chunker import SemanticChunker

logger = logging.getLogger(__name__)


class IngestionService:
    """Parse PDF/DOCX/TXT/MD files and produce chunks ready for embedding."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self.chunker = SemanticChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    async def process_file(
        self,
        file_path: str,
        document: Document,
    ) -> List[Chunk]:
        """Parse file and return chunks. Updates document.page_count in place."""
        ext = Path(file_path).suffix.lower().lstrip(".")
        file_type = DocumentType(ext) if ext in DocumentType._value2member_map_ else DocumentType.TXT

        try:
            if file_type == DocumentType.PDF:
                pages = await self._parse_pdf(file_path)
            elif file_type == DocumentType.DOCX:
                pages = await self._parse_docx(file_path)
            else:
                pages = await self._parse_text(file_path)

            document.page_count = len(pages)
            chunks = self.chunker.chunk_pages(
                pages=pages,
                document_id=document.id,
                document_name=document.name,
            )
            document.chunk_count = len(chunks)
            return chunks

        except Exception as e:
            logger.error("Failed to process file %s: %s", file_path, e)
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            raise

    async def _parse_pdf(self, file_path: str) -> List[Tuple[int, str]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._parse_pdf_sync, file_path)

    @staticmethod
    def _parse_pdf_sync(file_path: str) -> List[Tuple[int, str]]:
        try:
            import pdfplumber  # type: ignore
            pages: List[Tuple[int, str]] = []
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append((i, text))
            return pages
        except ImportError:
            # Fallback to pypdf
            try:
                from pypdf import PdfReader  # type: ignore
                reader = PdfReader(file_path)
                pages = []
                for i, page in enumerate(reader.pages, start=1):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append((i, text))
                return pages
            except ImportError:
                raise RuntimeError("Install pdfplumber or pypdf to parse PDFs.")

    async def _parse_docx(self, file_path: str) -> List[Tuple[int, str]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._parse_docx_sync, file_path)

    @staticmethod
    def _parse_docx_sync(file_path: str) -> List[Tuple[int, str]]:
        try:
            from docx import Document as DocxDocument  # type: ignore
            doc = DocxDocument(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            # Group into pseudo-pages of ~3000 chars
            pages: List[Tuple[int, str]] = []
            page_num = 1
            current: List[str] = []
            current_len = 0
            for para in paragraphs:
                current.append(para)
                current_len += len(para)
                if current_len >= 3000:
                    pages.append((page_num, "\n\n".join(current)))
                    page_num += 1
                    current = []
                    current_len = 0
            if current:
                pages.append((page_num, "\n\n".join(current)))
            return pages
        except ImportError:
            raise RuntimeError("Install python-docx to parse DOCX files.")

    @staticmethod
    async def _parse_text(file_path: str) -> List[Tuple[int, str]]:
        async with asyncio.timeout(10):
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None, lambda: Path(file_path).read_text(encoding="utf-8", errors="replace")
            )
        # Split into pseudo-pages of 3000 chars
        page_size = 3000
        pages: List[Tuple[int, str]] = []
        for i in range(0, max(len(content), 1), page_size):
            chunk = content[i : i + page_size]
            if chunk.strip():
                pages.append((i // page_size + 1, chunk))
        return pages or [(1, content)]

"""Document chunking engine — splits parsed documents into embedding-ready chunks."""
from __future__ import annotations

import re
from typing import Any

from .config import get_config
from .parsers.base import ParsedDocument, ParsedSection


class Chunker:
    def __init__(self) -> None:
        config = get_config()
        self.chunk_size = config.chunk_size
        self.chunk_overlap = config.chunk_overlap

    def chunk_document(self, doc: ParsedDocument) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        for section in doc.sections:
            for sc in self._chunk_text(section.content):
                chunks.append({"content": sc, "source": section.source, "section": section.section, "page": section.page, "language": section.language})
        merged: list[dict[str, Any]] = []
        for chunk in chunks:
            if merged and len(chunk["content"]) < 50 and merged[-1].get("section") == chunk.get("section"):
                merged[-1]["content"] += "\n" + chunk["content"]
            else:
                merged.append(chunk)
        return merged

    def _chunk_text(self, text: str) -> list[str]:
        text = text.strip()
        if not text: return []
        target_words = int(self.chunk_size / 1.3); overlap_words = int(self.chunk_overlap / 1.3)
        sentences = self._split_sentences(text)
        if len(sentences) <= 1: return [text] if text else []
        chunks: list[str] = []; current_words: list[str] = []; current_count = 0
        for sentence in sentences:
            sent_words = sentence.split()
            if current_count + len(sent_words) > target_words and current_words:
                chunks.append(" ".join(current_words))
                overlap = current_words[-overlap_words:] if overlap_words > 0 else []
                current_words = list(overlap); current_count = len(overlap)
            current_words.extend(sent_words); current_count += len(sent_words)
        if current_words: chunks.append(" ".join(current_words))
        return chunks

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        parts = re.split(r'(?<=[.!?。！？])\s+', text)
        return [p.strip() for p in parts if p.strip()]

"""Plain text parser."""
from __future__ import annotations

from pathlib import Path

from .base import BaseParser, ParsedDocument, ParsedSection


class TextParser(BaseParser):
    supported_extensions = [".txt", ".text", ".log", ".csv", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"]

    def parse(self) -> ParsedDocument:
        text = self.file_path.read_text(encoding="utf-8", errors="ignore")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        sections = [ParsedSection(content=para, source=str(self.file_path), section="") for para in paragraphs]
        return ParsedDocument(source=str(self.file_path), file_type=self.file_path.suffix.lstrip(".") or "txt", sections=sections)

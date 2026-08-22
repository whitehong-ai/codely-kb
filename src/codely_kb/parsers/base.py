"""Base document parser interface and data structures."""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ParsedSection:
    content: str
    source: str
    section: str = ""
    page: Optional[int] = None
    language: str = ""


@dataclass
class ParsedDocument:
    source: str
    file_type: str
    sections: list[ParsedSection] = field(default_factory=list)

    @property
    def total_text(self) -> str:
        return "\n\n".join(s.content for s in self.sections)


class BaseParser(ABC):
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    supported_extensions: list[str] = []

    @abstractmethod
    def parse(self) -> ParsedDocument:
        ...

    @staticmethod
    def compute_hash(file_path: str | Path) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

"""Document parsers for multiple file formats."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .base import BaseParser, ParsedDocument, ParsedSection
from .markdown import MarkdownParser
from .code import CodeParser
from .pdf import PDFParser
from .html import HTMLParser
from .epub import EPUBParser
from .text import TextParser

_PARSER_REGISTRY: dict[str, type[BaseParser]] = {}


def _register(parser_cls: type[BaseParser]) -> None:
    for ext in parser_cls.supported_extensions:
        _PARSER_REGISTRY[ext.lower()] = parser_cls


_register(MarkdownParser)
_register(CodeParser)
_register(PDFParser)
_register(HTMLParser)
_register(EPUBParser)
_register(TextParser)


def get_parser(file_path: str | Path) -> Optional[BaseParser]:
    ext = Path(file_path).suffix.lower()
    parser_cls = _PARSER_REGISTRY.get(ext)
    if parser_cls is None: return None
    return parser_cls(file_path)


def get_parser_for_url(url: str) -> BaseParser:
    return HTMLParser(url)


def is_supported(file_path: str | Path) -> bool:
    return Path(file_path).suffix.lower() in _PARSER_REGISTRY


__all__ = [
    "BaseParser", "ParsedDocument", "ParsedSection",
    "MarkdownParser", "CodeParser", "PDFParser",
    "HTMLParser", "EPUBParser", "TextParser",
    "get_parser", "get_parser_for_url", "is_supported",
]

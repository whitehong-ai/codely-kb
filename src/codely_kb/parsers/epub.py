"""EPUB parser using ebooklib."""
from __future__ import annotations

from pathlib import Path

from .base import BaseParser, ParsedDocument, ParsedSection


class EPUBParser(BaseParser):
    supported_extensions = [".epub"]

    def parse(self) -> ParsedDocument:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
        book = epub.read_epub(str(self.file_path), options={"ignore_ncx": True})
        sections: list[ParsedSection] = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            html_content = item.get_content().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html_content, "html.parser")
            chapter_title = ""
            h_tag = soup.find(["h1", "h2"])
            if h_tag: chapter_title = h_tag.get_text(strip=True)
            paragraphs = [p.get_text(strip=True) for p in soup.find_all(["p", "li"]) if p.get_text(strip=True)]
            if paragraphs:
                content = "\n".join(paragraphs)
                if len(content) > 2000:
                    for i in range(0, len(paragraphs), 10):
                        chunk = "\n".join(paragraphs[i:i + 10])
                        if chunk.strip(): sections.append(ParsedSection(content=chunk, source=str(self.file_path), section=f"{chapter_title} (part {i // 10 + 1})" if chapter_title else ""))
                else:
                    sections.append(ParsedSection(content=content, source=str(self.file_path), section=chapter_title))
        return ParsedDocument(source=str(self.file_path), file_type="epub", sections=sections)

"""PDF parser using PyMuPDF (fitz)."""
from __future__ import annotations

from pathlib import Path

from .base import BaseParser, ParsedDocument, ParsedSection


class PDFParser(BaseParser):
    supported_extensions = [".pdf"]

    def parse(self) -> ParsedDocument:
        import fitz
        doc = fitz.open(str(self.file_path))
        sections: list[ParsedSection] = []
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            if not text.strip(): continue
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            if len(paragraphs) <= 1 or len(text) <= 2000:
                sections.append(ParsedSection(content=text.strip(), source=str(self.file_path), section=f"Page {page_num + 1}", page=page_num + 1))
            else:
                for para in paragraphs:
                    if para: sections.append(ParsedSection(content=para, source=str(self.file_path), section=f"Page {page_num + 1}", page=page_num + 1))
        doc.close()
        return ParsedDocument(source=str(self.file_path), file_type="pdf", sections=sections)

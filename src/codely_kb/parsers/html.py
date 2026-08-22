"""HTML/URL parser using BeautifulSoup."""
from __future__ import annotations

from pathlib import Path

from .base import BaseParser, ParsedDocument, ParsedSection


class HTMLParser(BaseParser):
    supported_extensions = [".html", ".htm"]

    def __init__(self, file_path: str | Path):
        if isinstance(file_path, str) and file_path.startswith("http"):
            self._url = file_path; self._is_url = True; self.file_path = Path(file_path)
        else:
            self._url = None; self._is_url = False; self.file_path = Path(file_path)

    def parse(self) -> ParsedDocument:
        from bs4 import BeautifulSoup
        if self._is_url:
            import requests
            resp = requests.get(self._url, timeout=30); resp.raise_for_status(); html = resp.text; source = self._url
        else:
            html = self.file_path.read_text(encoding="utf-8", errors="ignore"); source = str(self.file_path)
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]): tag.decompose()
        sections: list[ParsedSection] = []
        title = soup.find("title"); current_heading = title.get_text(strip=True) if title else ""
        current_content: list[str] = []
        for element in soup.find_all(["h1", "h2", "h3", "p", "li", "pre", "blockquote"]):
            text = element.get_text(strip=True)
            if not text: continue
            if element.name in ("h1", "h2", "h3"):
                if current_content:
                    sections.append(ParsedSection(content="\n".join(current_content), source=source, section=current_heading)); current_content = []
                current_heading = text
            else:
                current_content.append(text)
        if current_content: sections.append(ParsedSection(content="\n".join(current_content), source=source, section=current_heading))
        return ParsedDocument(source=source, file_type="html", sections=sections)

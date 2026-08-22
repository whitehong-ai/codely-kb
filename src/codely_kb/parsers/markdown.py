"""Markdown parser using markdown-it-py."""
from __future__ import annotations

from pathlib import Path

from .base import BaseParser, ParsedDocument, ParsedSection


class MarkdownParser(BaseParser):
    supported_extensions = [".md", ".markdown"]

    def parse(self) -> ParsedDocument:
        from markdown_it import MarkdownIt

        text = self.file_path.read_text(encoding="utf-8")
        md = MarkdownIt()
        tokens = md.parse(text)

        sections: list[ParsedSection] = []
        current_heading = ""
        current_content: list[str] = []

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.type == "heading_open":
                if current_content:
                    sections.append(ParsedSection(content="\n".join(current_content).strip(), source=str(self.file_path), section=current_heading))
                    current_content = []
                level = token.tag
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    current_heading = f"{level} {tokens[i + 1].content}"
                    current_content.append(f"{('#' * int(level[1:]))} {tokens[i + 1].content}")
                i += 3
                continue
            elif token.type == "inline":
                current_content.append(token.content)
            elif token.type == "fence":
                lang = token.info.strip() if token.info else ""
                current_content.append(f"```{lang}\n{token.content}\n```")
            elif token.type == "code_block":
                current_content.append(token.content)
            i += 1

        if current_content:
            sections.append(ParsedSection(content="\n".join(current_content).strip(), source=str(self.file_path), section=current_heading))

        return ParsedDocument(source=str(self.file_path), file_type="md", sections=sections)

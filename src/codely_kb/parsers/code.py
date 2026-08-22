"""Code file parser using tree-sitter."""
from __future__ import annotations

from pathlib import Path

from .base import BaseParser, ParsedDocument, ParsedSection

_LANG_MAP = {
    ".py": "python", ".ts": "typescript", ".tsx": "tsx", ".js": "javascript",
    ".jsx": "jsx", ".java": "java", ".go": "go", ".rs": "rust", ".c": "c",
    ".cpp": "cpp", ".h": "c", ".hpp": "cpp", ".rb": "ruby", ".lua": "lua",
    ".swift": "swift", ".kt": "kotlin", ".cs": "c_sharp", ".php": "php",
    ".scala": "scala", ".sh": "bash",
}

_DEFINITION_TYPES = {
    "function_definition", "class_definition", "method_definition",
    "function_declaration", "class_declaration", "method_declaration",
    "function_item", "struct_item", "impl_item", "enum_item",
    "interface_declaration", "type_declaration", "export_statement",
}


class CodeParser(BaseParser):
    supported_extensions = list(_LANG_MAP.keys())

    def parse(self) -> ParsedDocument:
        text = self.file_path.read_text(encoding="utf-8")
        ext = self.file_path.suffix.lower()
        lang_name = _LANG_MAP.get(ext, "")
        if not lang_name: return self._fallback_parse(text, ext)
        try:
            from tree_sitter_languages import get_parser as ts_get_parser
            parser = ts_get_parser(lang_name)
            tree = parser.parse(text.encode("utf-8"))
            sections = self._extract_definitions(tree.root_node, text, lang_name)
            if sections: return ParsedDocument(source=str(self.file_path), file_type=ext.lstrip("."), sections=sections)
        except Exception: pass
        return self._fallback_parse(text, ext)

    def _extract_definitions(self, root_node, text: str, lang_name: str) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        def visit(node):
            if node.type in _DEFINITION_TYPES:
                start_line = node.start_point[0]; end_line = node.end_point[0]
                content = "\n".join(text.splitlines()[start_line:end_line + 1])
                first_line = text.splitlines()[start_line].strip() if start_line < len(text.splitlines()) else ""
                sections.append(ParsedSection(content=content, source=str(self.file_path), section=first_line[:80], language=lang_name))
                return
            for child in node.children: visit(child)
        visit(root_node)
        if not sections and text.strip():
            sections.append(ParsedSection(content=text, source=str(self.file_path), section="(entire file)", language=lang_name))
        return sections

    def _fallback_parse(self, text: str, ext: str) -> ParsedDocument:
        lines = text.splitlines(); chunk_size = 50; sections: list[ParsedSection] = []
        for i in range(0, len(lines), chunk_size):
            chunk = "\n".join(lines[i:i + chunk_size])
            if chunk.strip():
                sections.append(ParsedSection(content=chunk, source=str(self.file_path), section=f"lines {i+1}-{min(i+chunk_size, len(lines))}", language=ext.lstrip(".")))
        if not sections and text.strip():
            sections.append(ParsedSection(content=text, source=str(self.file_path), section="(entire file)", language=ext.lstrip(".")))
        return ParsedDocument(source=str(self.file_path), file_type=ext.lstrip("."), sections=sections)

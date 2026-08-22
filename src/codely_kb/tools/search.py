"""Semantic search and RAG query tools."""
from __future__ import annotations

from typing import Any

from ..config import get_config
from ..vectorstore import get_vectorstore


def search_kb(kb_id: str, query: str, top_k: int = 0, min_score: float = 0.0) -> dict[str, Any]:
    config = get_config()
    if top_k <= 0: top_k = config.default_top_k
    if min_score <= 0: min_score = config.default_min_score
    results = get_vectorstore().search(kb_id, query, top_k=top_k, min_score=min_score)
    return {"query": query, "kb_id": kb_id, "results": results, "total": len(results)}


def rag_query(kb_id: str, query: str, top_k: int = 0) -> dict[str, Any]:
    config = get_config()
    if top_k <= 0: top_k = config.default_top_k
    results = get_vectorstore().search(kb_id, query, top_k=top_k, min_score=0.2)
    context_parts: list[str] = []; sources: list[str] = []
    for r in results:
        source_label = r["source"]
        if r.get("section"): source_label += f" — {r['section']}"
        if r.get("page") is not None: source_label += f" (page {r['page']})"
        context_parts.append(f"[{source_label}]\n{r['content']}")
        if r["source"] not in sources: sources.append(r["source"])
    context_text = "\n\n---\n\n".join(context_parts) if context_parts else ""
    suggested_prompt = f"Based on the following document excerpts, answer the question: {query}\n\nContext:\n{context_text}\n\nPlease cite sources when referencing specific information." if context_text else f"No relevant documents found for: {query}"
    return {"chunks": [{"content": r["content"], "source": r["source"], "section": r.get("section", ""), "page": r.get("page"), "score": r["score"]} for r in results], "context_text": context_text, "sources": sources, "suggested_prompt": suggested_prompt, "kb_id": kb_id, "query": query}

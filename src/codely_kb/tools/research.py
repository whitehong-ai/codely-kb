"""Deep research and problem-solving support tools."""
from __future__ import annotations

import re
from typing import Any

from ..vectorstore import get_vectorstore


def research_search(query: str, kb_id: str | None = None, depth: str = "standard") -> dict[str, Any]:
    kb_results: list[dict[str, Any]] = []
    if kb_id:
        kb_results = get_vectorstore().search(kb_id, query, top_k=10, min_score=0.15)
        sub_queries = _derive_sub_queries(query, depth)
        seen_sources = {r["source"] for r in kb_results}
        for sq in sub_queries:
            for r in get_vectorstore().search(kb_id, sq, top_k=5, min_score=0.2):
                if r["source"] not in seen_sources: kb_results.append(r); seen_sources.add(r["source"])
    search_terms = _generate_search_terms(query, depth)
    outline = _suggest_outline(query, kb_results, depth)
    context_parts = [f"[{r['source']}{' — ' + r['section'] if r.get('section') else ''}]\n{r['content']}" for r in kb_results]
    context_text = "\n\n---\n\n".join(context_parts) if context_parts else ""
    return {"kb_results": [{"content": r["content"], "source": r["source"], "section": r.get("section", ""), "score": r["score"]} for r in kb_results], "search_terms": search_terms, "suggested_outline": outline, "context_text": context_text, "note": "Use search_terms with Codely's web_search tool for external information."}


def solve_search(query: str, kb_id: str | None = None, phase: str = "diagnose") -> dict[str, Any]:
    kb_chunks: list[dict[str, Any]] = []; related_concepts: list[str] = []
    if kb_id:
        kb_chunks = get_vectorstore().search(kb_id, query, top_k=5, min_score=0.2)
        for c in kb_chunks:
            if c.get("section"): related_concepts.append(c["section"])
        related_concepts = list(dict.fromkeys(related_concepts))[:10]
    phase_data = {
        "diagnose": {"prompt": f"Analyze this problem and identify:\n1. Problem type\n2. Key concepts\n3. Potential approaches\n4. Edge cases\n\nProblem: {query}\n", "instruction": "Identify the problem type and list key concepts before attempting to solve."},
        "solve": {"prompt": f"Solve this problem step by step:\n{query}\n\nProvide:\n1. Approach explanation\n2. Step-by-step solution\n3. Code or pseudocode if applicable\n", "instruction": "Generate a solution with clear reasoning at each step."},
        "verify": {"prompt": f"Verify this solution for: {query}\n\nCheck:\n1. Logical consistency\n2. Edge case handling\n3. Time/space complexity\n4. Alternative approaches\n", "instruction": "Independently verify the solution. If verification fails, suggest corrections."},
    }
    data = phase_data.get(phase, phase_data["diagnose"])
    return {"phase": phase, "kb_chunks": [{"content": c["content"], "source": c["source"], "score": c["score"]} for c in kb_chunks], "related_concepts": related_concepts, "diagnostic_prompt": data["prompt"], "instruction": data["instruction"], "note": "Three-phase orchestration is handled by Codely Skill."}


def _derive_sub_queries(query: str, depth: str) -> list[str]:
    parts = re.split(r'\s+(?:and|vs?\.?|versus|compared to|or)\s+', query, flags=re.IGNORECASE)
    sub = [p.strip() for p in parts if p.strip() and len(p.strip()) > 3]
    if depth == "deep": sub.extend([f"{query} history", f"{query} comparison", f"{query} future"])
    return sub[:5]


def _generate_search_terms(query: str, depth: str) -> list[str]:
    terms = [query]; angles = ["overview", "tutorial", "comparison", "best practices", "recent advances"]
    n = 3 if depth == "quick" else (5 if depth == "standard" else 8)
    return terms + [f"{query} {a}" for a in angles[:n]]


def _suggest_outline(query: str, kb_results: list[dict], depth: str) -> list[str]:
    n = 3 if depth == "quick" else (5 if depth == "standard" else 8)
    outline = [f"1. Introduction: What is {query}?", f"2. Key concepts and terminology"]
    if n >= 4: outline.append("3. Current state and approaches")
    if n >= 5: outline.append("4. Comparison of alternatives")
    if n >= 6: outline.append("5. Use cases and applications")
    if n >= 7: outline.append("6. Challenges and limitations")
    if n >= 8: outline.append("7. Future directions")
    outline.append(f"{len(outline) + 1}. Conclusion and references")
    return outline

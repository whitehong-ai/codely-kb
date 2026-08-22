"""Learning plan management tools."""
from __future__ import annotations

import json
import uuid
from typing import Any

from ..state import get_store
from ..vectorstore import get_vectorstore


def create_learning_plan(kb_id: str, topic: str, depth: str = "standard") -> dict[str, Any]:
    results = get_vectorstore().search(kb_id, topic, top_k=20, min_score=0.15)
    if not results: return {"error": f"[ERROR] create_learning_plan: no content found for topic '{topic}' in KB '{kb_id}'."}
    sources: dict[str, list[dict]] = {}
    for r in results: sources.setdefault(r["source"], []).append(r)
    context_parts = [f"[{src}]\n" + "\n\n".join(c["content"] for c in chunks) for src, chunks in sources.items()]
    context_text = "\n\n---\n\n".join(context_parts)
    step_range = {"quick": "3-5", "standard": "5-10", "thorough": "10-20"}.get(depth, "5-10")
    suggested_prompt = f"Create a {depth} learning plan ({step_range} steps) for the topic: '{topic}'.\n\nSource material from knowledge base:\n{context_text}\n\nFor each step, provide:\n- title: short step title\n- description: what to learn\n- concepts: list of key concepts\n- kb_chunks: list of source references\n\nOrder steps from foundational to advanced.\nReturn as a JSON array."
    return {"kb_id": kb_id, "topic": topic, "depth": depth, "context_text": context_text, "suggested_prompt": suggested_prompt, "sources_found": list(sources.keys()), "note": "Codely LLM should use suggested_prompt to generate steps, then call save_learning_plan to persist."}


def save_learning_plan(kb_id: str, topic: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    store = get_store(); enriched_steps = []
    for i, step in enumerate(steps):
        enriched_steps.append({"step_id": step.get("step_id", f"s_{uuid.uuid4().hex[:10]}"), "title": step.get("title", f"Step {i+1}"), "description": step.get("description", ""), "kb_chunks": step.get("kb_chunks", []), "concepts": step.get("concepts", [])})
    plan = store.create_learning_plan(kb_id, topic, enriched_steps)
    return {"plan_id": plan["plan_id"], "topic": topic, "total_steps": plan["total_steps"], "steps": enriched_steps, "created_at": plan["created_at"]}


def get_learning_plan(plan_id: str) -> dict[str, Any]:
    plan = get_store().get_learning_plan(plan_id)
    if not plan: return {"error": f"[ERROR] get_learning_plan: plan '{plan_id}' not found"}
    return {"plan_id": plan["plan_id"], "kb_id": plan["kb_id"], "topic": plan["topic"], "total_steps": plan["total_steps"], "completed_steps": plan["completed_steps"], "status": plan["status"], "steps": [{"step_id": s["step_id"], "title": s["title"], "description": s["description"], "kb_chunks": s["kb_chunks"], "concepts": s["concepts"], "status": s["status"], "score": s["score"], "order": s["order_idx"]} for s in plan["steps"]], "created_at": plan["created_at"], "updated_at": plan["updated_at"]}


def update_step_progress(plan_id: str, step_id: str, status: str, score: int | None = None) -> dict[str, Any]:
    store = get_store()
    result = store.update_step_progress(plan_id, step_id, status, score)
    if not result: return {"error": f"[ERROR] update_step_progress: step '{step_id}' not found in plan '{plan_id}'"}
    updated_step = result.get("updated_step", {}); next_step = result.get("next_step"); completed = result.get("completed_steps", 0)
    plan = store.get_learning_plan(plan_id); total = plan["total_steps"] if plan else 0
    weak_concepts: list[str] = []
    if status == "struggling" or (score is not None and score < 80):
        step_concepts = json.loads(updated_step.get("concepts", "[]")) if updated_step else []
        for concept in step_concepts: store.add_weak_concept(plan_id, concept); weak_concepts.append(concept)
    return {"updated_step": {"step_id": updated_step.get("step_id", step_id), "status": status, "score": score}, "next_step": {"step_id": next_step["step_id"], "title": next_step["title"]} if next_step else None, "weak_concepts": weak_concepts, "overall_progress": f"{completed}/{total} steps completed ({round(completed / total * 100) if total else 0}%)"}


def get_weak_concepts(plan_id: str) -> dict[str, Any]:
    store = get_store(); plan = store.get_learning_plan(plan_id)
    if not plan: return {"error": f"[ERROR] get_weak_concepts: plan '{plan_id}' not found"}
    weak = store.get_weak_concepts(plan_id)
    recommended_review: list[str] = []
    for wc in weak:
        for step in plan["steps"]:
            if wc["concept"] in step.get("concepts", []): recommended_review.extend(step.get("kb_chunks", []))
    recommended_review = list(dict.fromkeys(recommended_review))[:5]
    return {"plan_id": plan_id, "weak_concepts": [{"concept": wc["concept"], "missed_count": wc["missed_count"], "last_seen": wc["last_seen"]} for wc in weak], "recommended_review": recommended_review}

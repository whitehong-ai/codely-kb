"""Quiz generation and grading tools."""
from __future__ import annotations

import uuid
from typing import Any

from ..state import get_store
from ..vectorstore import get_vectorstore


def generate_quiz(kb_id: str, topic: str, num_questions: int = 5, question_type: str = "mixed", difficulty: str = "medium") -> dict[str, Any]:
    results = get_vectorstore().search(kb_id, topic, top_k=10, min_score=0.2)
    if not results: return {"error": f"[ERROR] generate_quiz: no content found for topic '{topic}' in KB '{kb_id}'. Consider importing more documents."}
    concepts: list[str] = []
    for r in results:
        if r.get("section"): concepts.append(r["section"])
    concepts = list(dict.fromkeys(concepts))[:10]
    context_parts = [f"[{r['source']}## {r.get('section', '')}]\n{r['content']}" for r in results]
    context_text = "\n\n".join(context_parts)
    type_instruction = {"choice": "multiple choice questions with 4 options (A/B/C/D) and one correct answer", "short_answer": "short answer questions", "fill_blank": "fill-in-the-blank questions", "mixed": "a mix of multiple choice, short answer, and fill-in-the-blank questions"}.get(question_type, "a mix of multiple choice, short answer, and fill-in-the-blank questions")
    difficulty_instruction = {"easy": "basic recall and definition questions", "medium": "questions requiring understanding and application", "hard": "questions requiring analysis and synthesis"}.get(difficulty, "questions requiring understanding and application")
    suggested_prompt = f"Generate {num_questions} {difficulty_instruction} about '{topic}'.\nFormat: {type_instruction}.\n\nSource material:\n{context_text}\n\nFor each question, provide:\n- question: the question text\n- type: \"choice\", \"short_answer\", or \"fill_blank\"\n- options: list of options (for choice type)\n- answer: the correct answer\n- explanation: brief explanation\n- concepts: list of key concepts tested\n\nReturn as a JSON array."
    return {"kb_id": kb_id, "topic": topic, "num_questions": num_questions, "question_type": question_type, "difficulty": difficulty, "concepts_found": concepts, "context_text": context_text, "suggested_prompt": suggested_prompt, "note": "Codely LLM should use suggested_prompt to generate quiz questions."}


def grade_answer(kb_id: str, question_id: str, question_type: str, question_text: str = "", user_answer: str = "", correct_answer: str = "", score: int = 0, concepts_missed: list[str] | None = None) -> dict[str, Any]:
    store = get_store(); correct = score >= 60
    result = store.add_quiz_result(kb_id=kb_id, question_id=question_id, question_type=question_type, question_text=question_text, user_answer=user_answer, correct=correct, score=score, concepts_missed=concepts_missed)
    return {"result_id": result["result_id"], "question_id": question_id, "correct": correct, "score": score, "concepts_missed": concepts_missed or [], "feedback": f"Correct! Score: {score}/100." if correct else f"Not quite. Score: {score}/100. Review: {', '.join(concepts_missed or [])}"}


def list_quiz_history(kb_id: str, limit: int = 50) -> dict[str, Any]:
    history = get_store().list_quiz_history(kb_id, limit=limit)
    total = len(history); correct_count = sum(1 for h in history if h.get("correct"))
    avg_score = sum(h.get("score", 0) for h in history) / total if total > 0 else 0
    return {"kb_id": kb_id, "history": history, "total": total, "correct_count": correct_count, "average_score": round(avg_score, 1)}

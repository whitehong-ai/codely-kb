"""SQLite state management for knowledge bases, documents, quizzes, and learning plans."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_config


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


class StateStore:
    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            db_path = get_config().state_db_path
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _init_db(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS kbs (
                kb_id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '', doc_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY, kb_id TEXT NOT NULL, file_path TEXT NOT NULL,
                file_type TEXT NOT NULL, file_hash TEXT, chunk_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                FOREIGN KEY (kb_id) REFERENCES kbs(kb_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS quiz_results (
                result_id TEXT PRIMARY KEY, kb_id TEXT NOT NULL, question_id TEXT NOT NULL,
                question_type TEXT NOT NULL, question_text TEXT, user_answer TEXT,
                correct BOOLEAN, score INTEGER, concepts_missed TEXT, created_at TEXT NOT NULL,
                FOREIGN KEY (kb_id) REFERENCES kbs(kb_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS learning_plans (
                plan_id TEXT PRIMARY KEY, kb_id TEXT NOT NULL, topic TEXT NOT NULL,
                total_steps INTEGER NOT NULL, completed_steps INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                FOREIGN KEY (kb_id) REFERENCES kbs(kb_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS plan_steps (
                step_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, title TEXT NOT NULL,
                description TEXT, kb_chunks TEXT, concepts TEXT, status TEXT DEFAULT 'pending',
                score INTEGER, order_idx INTEGER NOT NULL, completed_at TEXT,
                FOREIGN KEY (plan_id) REFERENCES learning_plans(plan_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS weak_concepts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id TEXT NOT NULL,
                concept TEXT NOT NULL, missed_count INTEGER DEFAULT 1, last_seen TEXT NOT NULL,
                FOREIGN KEY (plan_id) REFERENCES learning_plans(plan_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_documents_kb ON documents(kb_id);
            CREATE INDEX IF NOT EXISTS idx_quiz_kb ON quiz_results(kb_id);
            CREATE INDEX IF NOT EXISTS idx_steps_plan ON plan_steps(plan_id);
            CREATE INDEX IF NOT EXISTS idx_weak_plan ON weak_concepts(plan_id);
        """)
        self.conn.commit()

    def create_kb(self, name: str, description: str = "") -> dict[str, Any]:
        kb_id = _uuid("kb_"); now = _now_iso()
        self.conn.execute("INSERT INTO kbs (kb_id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (kb_id, name, description, now, now))
        self.conn.commit()
        return {"kb_id": kb_id, "name": name, "description": description, "doc_count": 0, "chunk_count": 0, "created_at": now}

    def delete_kb(self, kb_id: str) -> bool:
        cur = self.conn.execute("DELETE FROM kbs WHERE kb_id = ?", (kb_id,)); self.conn.commit()
        return cur.rowcount > 0

    def get_kb(self, kb_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM kbs WHERE kb_id = ?", (kb_id,)).fetchone()
        return dict(row) if row else None

    def get_kb_by_name(self, name: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM kbs WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

    def list_kbs(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM kbs ORDER BY created_at DESC").fetchall()]

    def update_kb_stats(self, kb_id: str, doc_count: int, chunk_count: int) -> None:
        self.conn.execute("UPDATE kbs SET doc_count = ?, chunk_count = ?, updated_at = ? WHERE kb_id = ?", (doc_count, chunk_count, _now_iso(), kb_id)); self.conn.commit()

    def add_document(self, kb_id: str, file_path: str, file_type: str, file_hash: str | None, chunk_count: int = 0) -> dict[str, Any]:
        doc_id = _uuid("doc_"); now = _now_iso()
        self.conn.execute("INSERT INTO documents (doc_id, kb_id, file_path, file_type, file_hash, chunk_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (doc_id, kb_id, file_path, file_type, file_hash, chunk_count, now, now))
        self.conn.commit()
        return {"doc_id": doc_id, "kb_id": kb_id, "file_path": file_path, "file_type": file_type, "file_hash": file_hash, "chunk_count": chunk_count, "created_at": now}

    def get_document_by_path(self, kb_id: str, file_path: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM documents WHERE kb_id = ? AND file_path = ?", (kb_id, file_path)).fetchone()
        return dict(row) if row else None

    def update_document(self, doc_id: str, file_hash: str | None, chunk_count: int) -> None:
        self.conn.execute("UPDATE documents SET file_hash = ?, chunk_count = ?, updated_at = ? WHERE doc_id = ?", (file_hash, chunk_count, _now_iso(), doc_id)); self.conn.commit()

    def remove_document(self, doc_id: str) -> bool:
        cur = self.conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,)); self.conn.commit()
        return cur.rowcount > 0

    def remove_document_by_path(self, kb_id: str, file_path: str) -> bool:
        cur = self.conn.execute("DELETE FROM documents WHERE kb_id = ? AND file_path = ?", (kb_id, file_path)); self.conn.commit()
        return cur.rowcount > 0

    def list_documents(self, kb_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM documents WHERE kb_id = ? ORDER BY created_at", (kb_id,)).fetchall()]

    def get_document_count(self, kb_id: str) -> int:
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM documents WHERE kb_id = ?", (kb_id,)).fetchone()
        return row["cnt"] if row else 0

    def add_quiz_result(self, kb_id, question_id, question_type, question_text="", user_answer="", correct=None, score=None, concepts_missed=None) -> dict[str, Any]:
        result_id = _uuid("qr_"); now = _now_iso()
        self.conn.execute("INSERT INTO quiz_results (result_id, kb_id, question_id, question_type, question_text, user_answer, correct, score, concepts_missed, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (result_id, kb_id, question_id, question_type, question_text, user_answer, correct, score, json.dumps(concepts_missed or []), now))
        self.conn.commit()
        return {"result_id": result_id, "kb_id": kb_id, "question_id": question_id, "question_type": question_type, "question_text": question_text, "user_answer": user_answer, "correct": correct, "score": score, "concepts_missed": concepts_missed or [], "created_at": now}

    def list_quiz_history(self, kb_id: str, limit: int = 50) -> list[dict[str, Any]]:
        results = []
        for r in self.conn.execute("SELECT * FROM quiz_results WHERE kb_id = ? ORDER BY created_at DESC LIMIT ?", (kb_id, limit)).fetchall():
            d = dict(r); d["concepts_missed"] = json.loads(d.get("concepts_missed") or "[]"); results.append(d)
        return results

    def create_learning_plan(self, kb_id: str, topic: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
        plan_id = _uuid("plan_"); now = _now_iso()
        self.conn.execute("INSERT INTO learning_plans (plan_id, kb_id, topic, total_steps, completed_steps, status, created_at, updated_at) VALUES (?, ?, ?, ?, 0, 'active', ?, ?)", (plan_id, kb_id, topic, len(steps), now, now))
        for i, step in enumerate(steps):
            step_id = step.get("step_id") or _uuid("s_")
            self.conn.execute("INSERT INTO plan_steps (step_id, plan_id, title, description, kb_chunks, concepts, status, score, order_idx, completed_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, ?, NULL)", (step_id, plan_id, step["title"], step.get("description", ""), json.dumps(step.get("kb_chunks", [])), json.dumps(step.get("concepts", [])), i + 1))
        self.conn.commit()
        return {"plan_id": plan_id, "kb_id": kb_id, "topic": topic, "total_steps": len(steps), "completed_steps": 0, "status": "active", "created_at": now}

    def get_learning_plan(self, plan_id: str) -> dict[str, Any] | None:
        plan = self.conn.execute("SELECT * FROM learning_plans WHERE plan_id = ?", (plan_id,)).fetchone()
        if not plan: return None
        plan = dict(plan); steps = self.conn.execute("SELECT * FROM plan_steps WHERE plan_id = ? ORDER BY order_idx", (plan_id,)).fetchall()
        plan["steps"] = []
        for s in steps:
            sd = dict(s); sd["kb_chunks"] = json.loads(sd.get("kb_chunks") or "[]"); sd["concepts"] = json.loads(sd.get("concepts") or "[]"); plan["steps"].append(sd)
        return plan

    def update_step_progress(self, plan_id: str, step_id: str, status: str, score: int | None = None) -> dict[str, Any] | None:
        now = _now_iso() if status in ("completed", "skipped") else None
        self.conn.execute("UPDATE plan_steps SET status = ?, score = ?, completed_at = ? WHERE step_id = ? AND plan_id = ?", (status, score, now, step_id, plan_id))
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM plan_steps WHERE plan_id = ? AND status = 'completed'", (plan_id,)).fetchone()
        completed = row["cnt"] if row else 0
        self.conn.execute("UPDATE learning_plans SET completed_steps = ?, updated_at = ?, status = ? WHERE plan_id = ?", (completed, _now_iso(), "completed" if completed >= self._get_total_steps(plan_id) else "active", plan_id))
        self.conn.commit()
        updated = self.conn.execute("SELECT * FROM plan_steps WHERE step_id = ?", (step_id,)).fetchone()
        next_step = self.conn.execute("SELECT * FROM plan_steps WHERE plan_id = ? AND order_idx > (SELECT order_idx FROM plan_steps WHERE step_id = ?) ORDER BY order_idx LIMIT 1", (plan_id, step_id)).fetchone()
        return {"updated_step": dict(updated) if updated else None, "next_step": dict(next_step) if next_step else None, "completed_steps": completed}

    def _get_total_steps(self, plan_id: str) -> int:
        row = self.conn.execute("SELECT total_steps FROM learning_plans WHERE plan_id = ?", (plan_id,)).fetchone()
        return row["total_steps"] if row else 0

    def add_weak_concept(self, plan_id: str, concept: str) -> None:
        existing = self.conn.execute("SELECT id, missed_count FROM weak_concepts WHERE plan_id = ? AND concept = ?", (plan_id, concept)).fetchone()
        if existing:
            self.conn.execute("UPDATE weak_concepts SET missed_count = ?, last_seen = ? WHERE id = ?", (existing["missed_count"] + 1, _now_iso(), existing["id"]))
        else:
            self.conn.execute("INSERT INTO weak_concepts (plan_id, concept, missed_count, last_seen) VALUES (?, ?, 1, ?)", (plan_id, concept, _now_iso()))
        self.conn.commit()

    def get_weak_concepts(self, plan_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM weak_concepts WHERE plan_id = ? ORDER BY missed_count DESC, last_seen DESC", (plan_id,)).fetchall()]

    def close(self) -> None:
        if self._conn: self._conn.close(); self._conn = None


_store: StateStore | None = None

def get_store() -> StateStore:
    global _store
    if _store is None: _store = StateStore()
    return _store

"""ChromaDB-backed vector store for semantic search."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from .config import get_config

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self) -> None:
        self._client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            import chromadb
            config = get_config()
            self._client = chromadb.PersistentClient(path=config.chroma_path_str)
            logger.info("ChromaDB initialized at %s", config.chroma_path_str)
        return self._client

    def _get_collection(self, kb_id: str) -> Any:
        return self.client.get_or_create_collection(name=get_config().kb_collection_name(kb_id), metadata={"hnsw:space": "cosine"})

    def add_chunks(self, kb_id: str, chunks: list[dict[str, Any]]) -> list[str]:
        if not chunks: return []
        collection = self._get_collection(kb_id)
        ids = [f"chunk_{uuid.uuid4().hex[:16]}" for _ in chunks]
        metadatas = [{"source": c.get("source", ""), "section": c.get("section", ""), "language": c.get("language", ""), **({"page": str(c["page"])} if c.get("page") is not None else {})} for c in chunks]
        collection.add(ids=ids, documents=[c["content"] for c in chunks], metadatas=metadatas)
        logger.info("Added %d chunks to KB %s", len(ids), kb_id)
        return ids

    def search(self, kb_id: str, query: str, top_k: int = 5, min_score: float = 0.3) -> list[dict[str, Any]]:
        collection = self._get_collection(kb_id)
        results = collection.query(query_texts=[query], n_results=min(top_k * 2, 100))
        if not results["ids"] or not results["ids"][0]: return []
        chunks = []
        for i, chunk_id in enumerate(results["ids"][0]):
            score = 1.0 - results["distances"][0][i]
            if score < min_score: continue
            meta = results["metadatas"][0][i]; page = None
            if "page" in meta:
                try: page = int(meta["page"])
                except (ValueError, TypeError): pass
            chunks.append({"content": results["documents"][0][i], "source": meta.get("source", ""), "section": meta.get("section", ""), "page": page, "language": meta.get("language", ""), "score": round(score, 4), "chunk_id": chunk_id})
        return chunks[:top_k]

    def delete_chunks_by_source(self, kb_id: str, source: str) -> int:
        collection = self._get_collection(kb_id)
        results = collection.get(where={"source": source})
        if results["ids"]: collection.delete(ids=results["ids"]); return len(results["ids"])
        return 0

    def delete_all_chunks(self, kb_id: str) -> None:
        collection = self._get_collection(kb_id)
        all_data = collection.get()
        if all_data["ids"]: collection.delete(ids=all_data["ids"])

    def drop_collection(self, kb_id: str) -> None:
        try: self.client.delete_collection(name=get_config().kb_collection_name(kb_id))
        except Exception: pass

    def count(self, kb_id: str) -> int:
        return self._get_collection(kb_id).count()


_store: VectorStore | None = None

def get_vectorstore() -> VectorStore:
    global _store
    if _store is None: _store = VectorStore()
    return _store

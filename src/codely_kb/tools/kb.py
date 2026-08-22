"""Knowledge base management tools."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..chunker import Chunker
from ..config import get_config
from ..parsers import get_parser, get_parser_for_url, is_supported
from ..state import get_store
from ..vectorstore import get_vectorstore

logger = logging.getLogger(__name__)


def create_kb(name: str, description: str = "") -> dict[str, Any]:
    store = get_store()
    existing = store.get_kb_by_name(name)
    if existing: return {"error": f"[ERROR] create_kb: knowledge base '{name}' already exists", "kb_id": existing["kb_id"]}
    kb = store.create_kb(name, description)
    logger.info("Created KB: %s (%s)", name, kb["kb_id"])
    return kb


def delete_kb(kb_id: str) -> dict[str, Any]:
    store = get_store(); vs = get_vectorstore()
    kb = store.get_kb(kb_id)
    if not kb: return {"error": f"[ERROR] delete_kb: knowledge base '{kb_id}' not found"}
    vs.drop_collection(kb_id); store.delete_kb(kb_id)
    return {"success": True, "kb_id": kb_id, "name": kb["name"]}


def list_kbs() -> dict[str, Any]:
    kbs = get_store().list_kbs()
    return {"knowledge_bases": [{"kb_id": kb["kb_id"], "name": kb["name"], "description": kb["description"], "doc_count": kb["doc_count"], "chunk_count": kb["chunk_count"]} for kb in kbs], "total": len(kbs)}


def get_kb_info(kb_id: str) -> dict[str, Any]:
    store = get_store()
    kb = store.get_kb(kb_id)
    if not kb: return {"error": f"[ERROR] get_kb_info: knowledge base '{kb_id}' not found"}
    docs = store.list_documents(kb_id)
    return {"kb_id": kb["kb_id"], "name": kb["name"], "description": kb["description"], "doc_count": kb["doc_count"], "chunk_count": kb["chunk_count"], "created_at": kb["created_at"], "updated_at": kb["updated_at"], "documents": [{"doc_id": d["doc_id"], "file_path": d["file_path"], "file_type": d["file_type"], "chunk_count": d["chunk_count"]} for d in docs]}


def add_documents(kb_id: str, files: list[str]) -> dict[str, Any]:
    store = get_store(); vs = get_vectorstore(); chunker = Chunker()
    kb = store.get_kb(kb_id)
    if not kb: return {"error": f"[ERROR] add_documents: knowledge base '{kb_id}' not found"}
    added = 0; total_chunks = 0; errors: list[dict[str, str]] = []; skipped = 0
    for file_path in files:
        path = Path(file_path).expanduser()
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and is_supported(child):
                    result = _import_single_file(kb_id, str(child), store, vs, chunker)
                    if result.get("error"): errors.append(result["error"])
                    elif result.get("skipped"): skipped += 1
                    else: added += 1; total_chunks += result["chunks"]
            continue
        if not path.exists(): errors.append({"file": str(path), "error": "file not found"}); continue
        if not is_supported(path): errors.append({"file": str(path), "error": f"unsupported format: {path.suffix}"}); continue
        result = _import_single_file(kb_id, str(path), store, vs, chunker)
        if result.get("error"): errors.append(result["error"])
        elif result.get("skipped"): skipped += 1
        else: added += 1; total_chunks += result["chunks"]
    doc_count = store.get_document_count(kb_id); vs_count = vs.count(kb_id)
    store.update_kb_stats(kb_id, doc_count, vs_count)
    return {"added": added, "chunks": total_chunks, "skipped": skipped, "errors": errors, "kb_id": kb_id}


def _import_single_file(kb_id, file_path, store, vs, chunker: Chunker) -> dict[str, Any]:
    parser = get_parser(file_path)
    if parser is None: return {"error": {"file": file_path, "error": "no parser available"}}
    file_hash = parser.compute_hash(file_path)
    existing = store.get_document_by_path(kb_id, file_path)
    if existing and existing.get("file_hash") == file_hash: return {"skipped": True}
    if existing: vs.delete_chunks_by_source(kb_id, file_path); store.remove_document(existing["doc_id"])
    try: doc = parser.parse()
    except Exception as e: return {"error": {"file": file_path, "error": str(e)}}
    chunks = chunker.chunk_document(doc)
    if not chunks: return {"error": {"file": file_path, "error": "no content extracted"}}
    chunk_ids = vs.add_chunks(kb_id, chunks)
    store.add_document(kb_id=kb_id, file_path=file_path, file_type=doc.file_type, file_hash=file_hash, chunk_count=len(chunks))
    return {"chunks": len(chunks), "chunk_ids": chunk_ids}


def add_url(kb_id: str, url: str) -> dict[str, Any]:
    store = get_store(); vs = get_vectorstore(); chunker = Chunker()
    kb = store.get_kb(kb_id)
    if not kb: return {"error": f"[ERROR] add_url: knowledge base '{kb_id}' not found"}
    parser = get_parser_for_url(url)
    try: doc = parser.parse()
    except Exception as e: return {"error": f"[ERROR] add_url: failed to fetch {url}: {e}"}
    chunks = chunker.chunk_document(doc)
    if not chunks: return {"error": f"[ERROR] add_url: no content extracted from {url}"}
    vs.add_chunks(kb_id, chunks)
    store.add_document(kb_id=kb_id, file_path=url, file_type="html", file_hash=None, chunk_count=len(chunks))
    doc_count = store.get_document_count(kb_id); vs_count = vs.count(kb_id)
    store.update_kb_stats(kb_id, doc_count, vs_count)
    return {"added": 1, "chunks": len(chunks), "url": url, "kb_id": kb_id}


def list_documents(kb_id: str) -> dict[str, Any]:
    store = get_store()
    kb = store.get_kb(kb_id)
    if not kb: return {"error": f"[ERROR] list_documents: knowledge base '{kb_id}' not found"}
    docs = store.list_documents(kb_id)
    return {"kb_id": kb_id, "documents": [{"doc_id": d["doc_id"], "file_path": d["file_path"], "file_type": d["file_type"], "chunk_count": d["chunk_count"], "created_at": d["created_at"], "updated_at": d["updated_at"]} for d in docs], "total": len(docs)}


def remove_document(kb_id: str, file_path: str) -> dict[str, Any]:
    store = get_store(); vs = get_vectorstore()
    kb = store.get_kb(kb_id)
    if not kb: return {"error": f"[ERROR] remove_document: knowledge base '{kb_id}' not found"}
    vs.delete_chunks_by_source(kb_id, file_path)
    removed = store.remove_document_by_path(kb_id, file_path)
    if not removed: return {"error": f"[ERROR] remove_document: document '{file_path}' not found in KB"}
    doc_count = store.get_document_count(kb_id); vs_count = vs.count(kb_id)
    store.update_kb_stats(kb_id, doc_count, vs_count)
    return {"success": True, "file_path": file_path, "kb_id": kb_id}

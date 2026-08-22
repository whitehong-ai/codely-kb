"""Embedding engine using sentence-transformers with TF-IDF fallback."""
from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np

from .config import get_config

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    def __init__(self) -> None:
        self._model: Any = None
        self._backend: str = ""
        self._tfidf: _TFIDFBackend | None = None

    def _ensure_model(self) -> None:
        if self._model is not None or self._tfidf is not None: return
        config = get_config()
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(config.embedding_model)
            self._backend = "sentence-transformers"
            logger.info("Loaded embedding model: %s", config.embedding_model)
        except Exception as e:
            logger.warning("Failed to load sentence-transformers (%s), falling back to TF-IDF", e)
            self._tfidf = _TFIDFBackend(); self._backend = "tfidf"

    def embed(self, texts: list[str]) -> np.ndarray:
        self._ensure_model()
        if self._backend == "sentence-transformers":
            return np.array(self._model.encode(texts, show_progress_bar=False), dtype=np.float32)
        assert self._tfidf is not None; return self._tfidf.embed(texts)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    @property
    def backend(self) -> str:
        self._ensure_model(); return self._backend

    @property
    def dimension(self) -> int:
        self._ensure_model()
        if self._backend == "sentence-transformers": return self._model.get_sentence_embedding_dimension()
        assert self._tfidf is not None; return self._tfidf.dimension


class _TFIDFBackend:
    def __init__(self) -> None:
        self._vectorizer: Any = None; self._fitted = False; self._vocab: dict[str, int] = {}; self.dimension = 384
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(max_features=384, stop_words="english", ngram_range=(1, 2))
        except ImportError:
            logger.warning("scikit-learn not available, using hash-based TF-IDF")

    def _fit(self, texts: list[str]) -> None:
        if self._vectorizer is not None: self._vectorizer.fit(texts); self._fitted = True
        else:
            import re
            words: set[str] = set()
            for text in texts: words.update(re.findall(r"\w+", text.lower()))
            for i, w in enumerate(sorted(words)[:384]): self._vocab[w] = i
            self._fitted = True

    def embed(self, texts: list[str]) -> np.ndarray:
        if not self._fitted: self._fit(texts)
        if self._vectorizer is not None:
            arr = np.array(self._vectorizer.transform(texts).toarray(), dtype=np.float32)
            if arr.shape[1] < 384: arr = np.pad(arr, ((0, 0), (0, 384 - arr.shape[1])))
            elif arr.shape[1] > 384: arr = arr[:, :384]
            return arr
        return self._hash_embed(texts)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    def _hash_embed(self, texts: list[str]) -> np.ndarray:
        import hashlib, re
        arr = np.zeros((len(texts), 384), dtype=np.float32)
        for i, text in enumerate(texts):
            for word in re.findall(r"\w+", text.lower()):
                h = int(hashlib.md5(word.encode()).hexdigest(), 16) % 384; arr[i, h] += 1.0
            norm = np.linalg.norm(arr[i])
            if norm > 0: arr[i] /= norm
        return arr


_engine: EmbeddingEngine | None = None

def get_engine() -> EmbeddingEngine:
    global _engine
    if _engine is None: _engine = EmbeddingEngine()
    return _engine

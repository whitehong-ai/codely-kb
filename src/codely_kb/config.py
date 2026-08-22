"""Configuration management for codely-kb."""
from __future__ import annotations

import os
from pathlib import Path


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(path)))


class Config:
    def __init__(self) -> None:
        home_env = os.environ.get("CODELY_KB_HOME", "~/.codely-kb")
        self.kb_home: Path = _expand(home_env)
        self.kb_home.mkdir(parents=True, exist_ok=True)

        self.chroma_dir: Path = self.kb_home / "chroma"
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        self.state_db_path: Path = self.kb_home / "state.db"

        self.embedding_model: str = os.environ.get(
            "CODELY_KB_EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
        self.embedding_dim: int = 384

        self.chunk_size: int = 512
        self.chunk_overlap: int = 64

        self.default_top_k: int = 5
        self.default_min_score: float = 0.3

    @property
    def chroma_path_str(self) -> str:
        return str(self.chroma_dir)

    def kb_collection_name(self, kb_id: str) -> str:
        return f"kb_{kb_id}"


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config

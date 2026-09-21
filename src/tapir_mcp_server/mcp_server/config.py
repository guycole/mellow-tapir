"""Configuration helpers for the Tapir MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_ROOT.parent
REPO_ROOT = PROJECT_ROOT.parent.parent.parent

DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "tapir.sqlite"
DEFAULT_SEED_PATH = REPO_ROOT / "src" / "tapir_schema" / "seed.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "src" / "tapir_schema" / "schema.sql"


@dataclass(frozen=True)
class ServerConfig:
    """Runtime settings for database and optional Ollama integration."""

    db_path: Path
    seed_path: Path
    schema_path: Path
    ollama_base_url: str
    reference_model: str


def load_config() -> ServerConfig:
    """Load config from environment variables with sensible defaults."""
    db_path = Path(os.getenv("TAPIR_DB_PATH", str(DEFAULT_DB_PATH))).resolve()
    seed_path = Path(os.getenv("TAPIR_SEED_PATH", str(DEFAULT_SEED_PATH))).resolve()
    schema_path = Path(os.getenv("TAPIR_SCHEMA_PATH", str(DEFAULT_SCHEMA_PATH))).resolve()
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    reference_model = os.getenv("REFERENCE_LLM_MODEL", "gpt-oss:20b")
    return ServerConfig(
        db_path=db_path,
        seed_path=seed_path,
        schema_path=schema_path,
        ollama_base_url=ollama_base_url,
        reference_model=reference_model,
    )

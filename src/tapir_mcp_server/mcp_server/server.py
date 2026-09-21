"""MCP server definition for Tapir classification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from .config import ServerConfig
from .database import TapirRepository
from .reference_llm import OllamaConfig, ask_reference_llm


def create_server(config: ServerConfig) -> MCPServer:
    """Create and configure the MCP server instance."""
    repository = TapirRepository(
        db_path=config.db_path,
        seed_path=config.seed_path,
        schema_path=config.schema_path,
    )

    server = MCPServer(
        name="tapir_mcp_server",
        title="Tapir Classifier MCP",
        description=(
            "Classify RF frequencies using a read-only SQLite catalog built "
            "from tapir_classifier seed data."
        ),
        instructions=(
            "Use classify_frequency for a direct lookup. Use query_channels "
            "for nearby channel context and search_services for broad service "
            "discovery."
        ),
    )

    @server.tool(description="Classify one frequency into probable services.")
    def classify_frequency(frequency: str | int | float) -> dict[str, Any]:
        return repository.classify_frequency(frequency)

    @server.tool(description="List known channels between two frequencies.")
    def query_channels(
        lower_hz: int,
        upper_hz: int,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        return repository.query_channels(lower_hz, upper_hz, limit)

    @server.tool(description="Search services by service or use-name text.")
    def search_services(service_query: str, limit: int = 50) -> list[dict[str, Any]]:
        return repository.search_services(service_query, limit)

    @server.tool(description="Execute a read-only SELECT/CTE query.")
    def execute_readonly_sql(sql: str, limit: int = 200) -> dict[str, Any]:
        return repository.execute_select_sql(sql, limit)

    @server.tool(
        description=(
            "Ask the reference LLM through Ollama. Default model is "
            "gpt-oss:20b."
        )
    )
    def ask_reference_model(
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        return ask_reference_llm(
            config=OllamaConfig(
                base_url=config.ollama_base_url,
                model=config.reference_model,
            ),
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )

    @server.resource(
        "tapir://metadata",
        name="Tapir Dataset Metadata",
        mime_type="application/json",
    )
    def metadata_resource() -> str:
        metadata = {
            "database_path": str(config.db_path),
            "read_only": True,
            "seed_source": str(config.seed_path),
            "schema_source": str(config.schema_path),
            "reference_llm": {
                "provider": "ollama",
                "model": config.reference_model,
                "endpoint": config.ollama_base_url,
            },
        }
        return json.dumps(metadata, indent=2)

    @server.resource(
        "tapir://sources/seed-json",
        name="Seed JSON Source",
        mime_type="application/json",
    )
    def seed_resource() -> str:
        return repository.source_documents()["seed_json"]

    @server.resource(
        "tapir://sources/schema-sql",
        name="Schema SQL Source",
        mime_type="text/plain",
    )
    def schema_resource() -> str:
        return repository.source_documents()["schema_sql"]

    return server


def ensure_database_exists(db_path: Path) -> None:
    """Raise a clear error if the SQLite file is missing."""
    if not db_path.exists():
        raise FileNotFoundError(
            f"SQLite database was not found at {db_path}. "
            "Run the DB build step first."
        )

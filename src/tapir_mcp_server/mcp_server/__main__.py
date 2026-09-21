"""CLI entrypoint for the Tapir MCP server."""

from __future__ import annotations

import argparse
from pathlib import Path

from .build_db import build_sqlite_database
from .config import load_config
from .server import create_server, ensure_database_exists


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Tapir MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="MCP transport type.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--path", default="/mcp")
    parser.add_argument(
        "--rebuild-db",
        action="store_true",
        help="Rebuild SQLite database from tapir_classifier sources.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()

    if args.rebuild_db or not Path(config.db_path).exists():
        build_sqlite_database(
            db_path=config.db_path,
            seed_path=config.seed_path,
            schema_path=config.schema_path,
        )

    ensure_database_exists(config.db_path)
    server = create_server(config)

    if args.transport == "stdio":
        server.run(transport="stdio")
        return

    server.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
    )


if __name__ == "__main__":
    main()

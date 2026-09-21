"""Build the SQLite Tapir catalog from seed JSON and schema metadata."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_seed(seed_path: Path) -> dict[str, Any]:
    with seed_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS band (
            band_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lower_hz INTEGER NOT NULL CHECK (lower_hz >= 0),
            upper_hz INTEGER NOT NULL CHECK (upper_hz > lower_hz),
            service_name TEXT NOT NULL,
            use_name TEXT NOT NULL,
            channel_spacing_hz INTEGER,
            channel_offset_hz INTEGER,
            priority INTEGER NOT NULL DEFAULT 50 CHECK (priority BETWEEN 0 AND 100),
            notes TEXT,
            UNIQUE (lower_hz, upper_hz, service_name, use_name)
        );

        CREATE INDEX IF NOT EXISTS band_frequency_idx
            ON band (lower_hz, upper_hz);
        CREATE INDEX IF NOT EXISTS band_service_idx
            ON band (service_name);

        CREATE TABLE IF NOT EXISTS band_emission (
            band_id INTEGER NOT NULL,
            emission_designator TEXT NOT NULL,
            modulation_label TEXT NOT NULL,
            occupied_bandwidth_hz INTEGER,
            is_typical INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            PRIMARY KEY (band_id, emission_designator),
            FOREIGN KEY (band_id) REFERENCES band (band_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS channel (
            channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
            center_hz INTEGER NOT NULL CHECK (center_hz >= 0),
            label TEXT NOT NULL,
            service_name TEXT NOT NULL,
            emission_designator TEXT,
            channel_spacing_hz INTEGER,
            notes TEXT,
            UNIQUE (center_hz, label)
        );

        CREATE INDEX IF NOT EXISTS channel_frequency_idx
            ON channel (center_hz);

        CREATE TABLE IF NOT EXISTS dataset_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def _insert_data(conn: sqlite3.Connection, catalog: dict[str, Any]) -> None:
    conn.execute("DELETE FROM channel")
    conn.execute("DELETE FROM band_emission")
    conn.execute("DELETE FROM band")
    conn.execute("DELETE FROM dataset_metadata")

    for band in catalog.get("bands", []):
        cursor = conn.execute(
            """
            INSERT INTO band (
                lower_hz,
                upper_hz,
                service_name,
                use_name,
                channel_spacing_hz,
                channel_offset_hz,
                priority,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                band["lower_hz"],
                band["upper_hz"],
                band["service_name"],
                band["use_name"],
                band.get("channel_spacing_hz"),
                band.get("channel_offset_hz"),
                band["priority"],
                band.get("notes"),
            ),
        )
        band_id = cursor.lastrowid
        for emission in band.get("emissions", []):
            conn.execute(
                """
                INSERT INTO band_emission (
                    band_id,
                    emission_designator,
                    modulation_label,
                    occupied_bandwidth_hz,
                    is_typical,
                    notes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    band_id,
                    emission["designator"],
                    emission["modulation"],
                    emission.get("occupied_bandwidth_hz"),
                    1 if emission.get("typical", True) else 0,
                    emission.get("notes"),
                ),
            )

    for channel in catalog.get("channels", []):
        conn.execute(
            """
            INSERT INTO channel (
                center_hz,
                label,
                service_name,
                emission_designator,
                channel_spacing_hz,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                channel["center_hz"],
                channel["label"],
                channel["service_name"],
                channel.get("emission_designator"),
                channel.get("channel_spacing_hz"),
                channel.get("notes"),
            ),
        )


def _insert_metadata(
    conn: sqlite3.Connection,
    seed_path: Path,
    schema_path: Path,
    catalog: dict[str, Any],
) -> None:
    limits = catalog.get("catalog_limits_hz", [108000000, 1000000000])
    metadata = {
        "source_seed_json": str(seed_path.resolve()),
        "source_schema_sql": str(schema_path.resolve()),
        "catalog_limit_lower_hz": str(limits[0]),
        "catalog_limit_upper_hz": str(limits[1]),
        "schema_sql_text": _read_text(schema_path),
    }
    conn.executemany(
        "INSERT INTO dataset_metadata (key, value) VALUES (?, ?)",
        metadata.items(),
    )


def build_sqlite_database(db_path: Path, seed_path: Path, schema_path: Path) -> None:
    """Build a fresh SQLite catalog file from the source JSON and SQL files."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    catalog = _load_seed(seed_path)
    with sqlite3.connect(db_path) as conn:
        _create_schema(conn)
        _insert_data(conn, catalog)
        _insert_metadata(conn, seed_path, schema_path, catalog)
        conn.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SQLite DB from seed files")
    parser.add_argument("--db-path", required=True, type=Path)
    parser.add_argument("--seed-path", required=True, type=Path)
    parser.add_argument("--schema-path", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_sqlite_database(
        db_path=args.db_path,
        seed_path=args.seed_path,
        schema_path=args.schema_path,
    )


if __name__ == "__main__":
    main()

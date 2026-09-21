"""Read-only SQLite access layer for Tapir classification data."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


_ALLOWED_SQL_PATTERN = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)


class TapirRepository:
    """Query helper for the immutable Tapir catalog."""

    def __init__(self, db_path: Path, seed_path: Path, schema_path: Path) -> None:
        self._db_path = db_path
        self._seed_path = seed_path
        self._schema_path = schema_path

    def _connect(self) -> sqlite3.Connection:
        uri = f"file:{self._db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn

    @staticmethod
    def _parse_frequency(frequency: str | int | float) -> int:
        if isinstance(frequency, int):
            return frequency
        if isinstance(frequency, float):
            if frequency < 10_000:
                return int(round(frequency * 1_000_000))
            return int(round(frequency))

        value = str(frequency).strip().lower().replace(",", "")
        if value.endswith("mhz"):
            return int(round(float(value[:-3]) * 1_000_000))
        if value.endswith("khz"):
            return int(round(float(value[:-3]) * 1_000))
        if value.endswith("hz"):
            return int(round(float(value[:-2])))

        number = float(value)
        if number < 10_000:
            return int(round(number * 1_000_000))
        return int(round(number))

    def classify_frequency(self, frequency: str | int | float) -> dict[str, Any]:
        query_hz = self._parse_frequency(frequency)
        with self._connect() as conn:
            channels = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT
                        channel_id,
                        center_hz,
                        label,
                        service_name,
                        emission_designator,
                        channel_spacing_hz,
                        notes
                    FROM channel
                    WHERE center_hz = ?
                    ORDER BY service_name, label
                    """,
                    (query_hz,),
                )
            ]

            band_rows = list(
                conn.execute(
                    """
                    SELECT
                        band_id,
                        lower_hz,
                        upper_hz,
                        service_name,
                        use_name,
                        channel_spacing_hz,
                        channel_offset_hz,
                        priority,
                        notes
                    FROM band
                    WHERE ? >= lower_hz AND ? < upper_hz
                    ORDER BY
                        priority DESC,
                        (upper_hz - lower_hz) ASC,
                        service_name ASC,
                        use_name ASC
                    """,
                    (query_hz, query_hz),
                )
            )

            bands: list[dict[str, Any]] = []
            for row in band_rows:
                band_record = dict(row)
                emissions = [
                    dict(item)
                    for item in conn.execute(
                        """
                        SELECT
                            emission_designator AS designator,
                            modulation_label AS modulation,
                            occupied_bandwidth_hz,
                            is_typical AS typical,
                            notes
                        FROM band_emission
                        WHERE band_id = ?
                        ORDER BY is_typical DESC, emission_designator ASC
                        """,
                        (row["band_id"],),
                    )
                ]
                for emission in emissions:
                    emission["typical"] = bool(emission["typical"])
                band_record["emissions"] = emissions
                bands.append(band_record)

        return {
            "frequency_hz": query_hz,
            "frequency_mhz": query_hz / 1_000_000,
            "channels": channels,
            "bands": bands,
        }

    def query_channels(
        self,
        lower_hz: int,
        upper_hz: int,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 1000))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    channel_id,
                    center_hz,
                    label,
                    service_name,
                    emission_designator,
                    channel_spacing_hz,
                    notes
                FROM channel
                WHERE center_hz BETWEEN ? AND ?
                ORDER BY center_hz ASC
                LIMIT ?
                """,
                (lower_hz, upper_hz, safe_limit),
            )
            return [dict(row) for row in rows]

    def search_services(self, service_query: str, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 500))
        query_like = f"%{service_query.strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT
                    service_name,
                    use_name,
                    MIN(lower_hz) AS min_lower_hz,
                    MAX(upper_hz) AS max_upper_hz,
                    MAX(priority) AS max_priority
                FROM band
                WHERE service_name LIKE ? OR use_name LIKE ?
                GROUP BY service_name, use_name
                ORDER BY max_priority DESC, service_name ASC, use_name ASC
                LIMIT ?
                """,
                (query_like, query_like, safe_limit),
            )
            return [dict(row) for row in rows]

    def execute_select_sql(self, sql: str, limit: int = 200) -> dict[str, Any]:
        if not _ALLOWED_SQL_PATTERN.match(sql):
            raise ValueError("Only SELECT/CTE queries are allowed.")

        normalized = sql.strip().rstrip(";")
        limited = (
            f"SELECT * FROM ({normalized}) AS q LIMIT {max(1, min(limit, 1000))}"
        )
        with self._connect() as conn:
            cursor = conn.execute(limited)
            columns = [description[0] for description in cursor.description or []]
            rows = [dict(row) for row in cursor.fetchall()]

        return {"columns": columns, "rows": rows, "row_count": len(rows)}

    def source_documents(self) -> dict[str, str]:
        return {
            "seed_json": self._seed_path.read_text(encoding="utf-8"),
            "schema_sql": self._schema_path.read_text(encoding="utf-8"),
        }

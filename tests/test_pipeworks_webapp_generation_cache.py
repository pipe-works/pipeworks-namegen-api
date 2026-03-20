"""Unit tests for generation package option caching."""

from __future__ import annotations

from pathlib import Path

from pipeworks_namegen_api.webapp.db import connect_database, initialize_schema
from pipeworks_namegen_api.webapp.generation import (
    clear_generation_package_options_cache,
    get_cached_generation_package_options,
)


def _insert_package_with_table(
    conn,
    *,
    name: str,
    metadata_path: str,
    zip_path: str,
    source_txt: str,
    table_name: str,
    row_count: int,
) -> int:
    inserted = conn.execute(
        """
        INSERT INTO imported_packages (
            package_name,
            imported_at,
            metadata_json_path,
            package_zip_path
        ) VALUES (?, ?, ?, ?)
        """,
        (name, "2026-02-08T00:00:00+00:00", metadata_path, zip_path),
    )
    if inserted.lastrowid is None:
        raise AssertionError("Expected sqlite row id for imported package insert.")
    package_id = int(inserted.lastrowid)
    conn.execute(
        """
        INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
        VALUES (?, ?, ?, ?)
        """,
        (package_id, source_txt, table_name, row_count),
    )
    conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY, value TEXT)")
    conn.commit()
    return package_id


def test_generation_package_options_cache_invalidation(tmp_path: Path) -> None:
    """Cache should hold until explicit invalidation per db path."""
    db_path = tmp_path / "cache.sqlite3"
    with connect_database(db_path) as conn:
        initialize_schema(conn)
        _insert_package_with_table(
            conn,
            name="Package A",
            metadata_path="a.json",
            zip_path="a.zip",
            source_txt="nltk_first_name_2syl.txt",
            table_name="pkg_a",
            row_count=2,
        )

        first_payload = get_cached_generation_package_options(conn, db_path=db_path)
        first_total = sum(len(entry["packages"]) for entry in first_payload)

        _insert_package_with_table(
            conn,
            name="Package B",
            metadata_path="b.json",
            zip_path="b.zip",
            source_txt="nltk_first_name_2syl.txt",
            table_name="pkg_b",
            row_count=2,
        )

        cached_payload = get_cached_generation_package_options(conn, db_path=db_path)
        cached_total = sum(len(entry["packages"]) for entry in cached_payload)
        assert cached_total == first_total

        clear_generation_package_options_cache(db_path)
        refreshed_payload = get_cached_generation_package_options(conn, db_path=db_path)
        refreshed_total = sum(len(entry["packages"]) for entry in refreshed_payload)
        assert refreshed_total == first_total + 1

        clear_generation_package_options_cache()

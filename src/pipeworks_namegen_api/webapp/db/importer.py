"""Importer workflow for metadata JSON + ZIP package pairs."""

from __future__ import annotations

import json
import sqlite3
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeworks_namegen_api.webapp.db.repositories import build_package_table_name
from pipeworks_namegen_api.webapp.db.table_store import create_text_table, insert_text_rows


def load_metadata_json(metadata_path: Path) -> dict[str, Any]:
    """Load metadata JSON and enforce object-root structure.

    Args:
        metadata_path: Path to metadata JSON file.

    Returns:
        Parsed JSON object.

    Raises:
        ValueError: If the root JSON value is not an object.
    """
    with open(metadata_path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Metadata JSON root must be an object.")
    return payload


def read_txt_rows(archive: zipfile.ZipFile, entry_name: str) -> list[tuple[int, str]]:
    """Read one txt entry and return ``(line_number, value)`` tuples.

    Empty and whitespace-only lines are skipped during import so DB tables only
    store meaningful values.
    """
    try:
        payload = archive.read(entry_name)
    except KeyError as exc:
        raise ValueError(f"TXT entry missing from zip: {entry_name}") from exc

    try:
        decoded = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"TXT entry is not valid UTF-8: {entry_name}") from exc

    rows: list[tuple[int, str]] = []
    for line_number, line in enumerate(decoded.splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        rows.append((line_number, text))
    return rows


def import_package_pair(
    conn: sqlite3.Connection, *, metadata_path: Path, zip_path: Path
) -> dict[str, Any]:
    """Import one metadata+zip pair and create one SQLite table per ``*.txt``.

    The importer ignores JSON files inside the archive. It uses metadata
    ``files_included`` (when provided) to limit which ``*.txt`` entries are
    imported.

    Args:
        conn: Open SQLite connection.
        metadata_path: Path to ``*_metadata.json`` file.
        zip_path: Path to package zip file.

    Returns:
        API-style summary payload describing imported package and created tables.

    Raises:
        FileNotFoundError: If metadata or zip path does not exist.
        ValueError: For invalid metadata, duplicate imports, or zip format/data
            issues.
    """
    metadata_resolved = metadata_path.resolve()
    zip_resolved = zip_path.resolve()

    if not metadata_resolved.exists():
        raise FileNotFoundError(f"Metadata JSON does not exist: {metadata_resolved}")
    if not zip_resolved.exists():
        raise FileNotFoundError(f"Package ZIP does not exist: {zip_resolved}")

    payload = load_metadata_json(metadata_resolved)

    # FIX: Support both old-format "common_name" and new-format "package_name"
    # metadata fields. Old packages use "common_name", newer patch-based
    # packages use "package_name". Fall back to the ZIP stem if neither exists.
    package_name = (
        str(payload.get("common_name", "")).strip()
        or str(payload.get("package_name", "")).strip()
        or zip_resolved.stem
    )

    raw_files_included = payload.get("files_included")
    if raw_files_included is None:
        files_included: list[Any] = []
    elif isinstance(raw_files_included, list):
        files_included = raw_files_included
    else:
        raise ValueError("Metadata key 'files_included' must be a list when provided.")

    # FIX: Build TWO allowed-name sets to handle both metadata formats.
    #
    # Old format uses basenames in files_included:
    #   ["pyphen_first_name_2syl.txt", "pyphen_last_name_2syl.txt"]
    #
    # New format uses directory-qualified relative paths:
    #   ["patch_a/selections.txt", "patch_b/selections.txt"]
    #
    # We collect both the full relative paths AND the basenames so the
    # filter below matches entries regardless of which convention the
    # metadata author used.
    allowed_txt_full_paths: set[str] = set()
    allowed_txt_basenames: set[str] = set()
    for name in files_included:
        cleaned = str(name).strip()
        if not cleaned.lower().endswith(".txt"):
            continue
        allowed_txt_full_paths.add(cleaned)
        allowed_txt_basenames.add(Path(cleaned).name)

    try:
        with zipfile.ZipFile(zip_resolved, "r") as archive:
            entries = sorted(
                name
                for name in archive.namelist()
                if not name.endswith("/") and name.lower().endswith(".txt")
            )

            # FIX: Match ZIP entries against both full relative paths and
            # basenames. The full-path check handles the new patch-based
            # format ("patch_a/selections.txt"), while the basename check
            # preserves backward compatibility with old flat-layout packages
            # ("pyphen_first_name_2syl.txt").
            if allowed_txt_full_paths:
                entries = [
                    entry
                    for entry in entries
                    if entry in allowed_txt_full_paths or Path(entry).name in allowed_txt_basenames
                ]

            cursor = conn.execute(
                """
                INSERT INTO imported_packages (
                    package_name,
                    imported_at,
                    metadata_json_path,
                    package_zip_path
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    package_name,
                    datetime.now(timezone.utc).isoformat(),
                    str(metadata_resolved),
                    str(zip_resolved),
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not return a row id for imported package insert.")
            package_id = int(cursor.lastrowid)

            # FIX: Detect basename collisions among the filtered entries.
            # When two ZIP entries in different directories share the same
            # basename (e.g. "patch_a/selections.txt" and
            # "patch_b/selections.txt"), we must use a directory-qualified
            # source_txt_name to avoid UNIQUE constraint violations.
            #
            # Old-format packages (e.g. "selections/nltk_first_name_2syl.txt")
            # have unique basenames, so they continue to store just the
            # basename for backward compatibility with existing DB records
            # and the generation class mapper.
            basename_counts = Counter(Path(entry).name for entry in entries)
            colliding_basenames = {name for name, count in basename_counts.items() if count > 1}

            created_tables: list[dict[str, Any]] = []
            for index, entry_name in enumerate(entries, start=1):
                txt_rows = read_txt_rows(archive, entry_name)
                table_name = build_package_table_name(
                    package_name, Path(entry_name).stem, package_id, index
                )
                create_text_table(conn, table_name)
                insert_text_rows(conn, table_name, txt_rows)

                entry_path = Path(entry_name)
                if entry_path.name in colliding_basenames:
                    # FIX: Directory-qualify to avoid UNIQUE collision.
                    # "patch_a/selections.txt" -> "patch_a_selections.txt"
                    source_txt_name = str(entry_path).replace("/", "_")
                else:
                    # No collision: use bare basename for backward compat.
                    source_txt_name = entry_path.name

                conn.execute(
                    """
                    INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
                    VALUES (?, ?, ?, ?)
                    """,
                    (package_id, source_txt_name, table_name, len(txt_rows)),
                )
                created_tables.append(
                    {
                        "source_txt_name": source_txt_name,
                        "table_name": table_name,
                        "row_count": len(txt_rows),
                    }
                )

            conn.commit()
            return {
                "message": (
                    f"Imported package '{package_name}' with "
                    f"{len(created_tables)} txt table(s)."
                ),
                "package_id": package_id,
                "package_name": package_name,
                "tables": created_tables,
            }
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError("This metadata/zip pair has already been imported.") from exc
    except zipfile.BadZipFile as exc:
        conn.rollback()
        raise ValueError(f"Invalid ZIP file: {zip_resolved}") from exc
    except Exception:
        conn.rollback()
        raise


def import_from_run_directory(
    conn: sqlite3.Connection,
    *,
    run_dir: Path,
    package_name: str | None = None,
) -> dict[str, Any]:
    """Import name data directly from a namegen-lexicon output run directory.

    Reads all IPC selection files (``ipc/*.v1.json``) from the run directory,
    extracts ``name_class`` from each file's ``payload.params`` block, and
    groups names by class.  One SQLite table is created per class using the
    ``nltk_{name_class}.txt`` source filename convention so the generation
    mapper resolves:

    - ``class_key``    → ``name_class``  (e.g. ``"first_name"``)
    - ``syllable_key`` → ``"all"``       (no syllable-count suffix in the filename)

    This satisfies the mud-server ``syllable_key="all"`` requirement without
    needing to produce a ZIP package first.

    The ``UNIQUE(metadata_json_path, package_zip_path)`` constraint on
    ``imported_packages`` naturally prevents duplicate imports: the resolved
    run directory path is stored as ``metadata_json_path`` and the literal
    string ``"(ipc-run-import)"`` as ``package_zip_path``.

    Args:
        conn: Open SQLite connection.
        run_dir: Path to the namegen-lexicon output run directory (e.g.
            ``/srv/work/pipeworks/runtime/namegen-lexicon/output/20260412_104618_nltk``).
        package_name: Human-readable label for the imported package.  Defaults
            to the run directory stem (e.g. ``"20260412_104618_nltk"``).

    Returns:
        API-style summary payload with keys ``message``, ``package_id``,
        ``package_name``, and ``tables`` (list of created table summaries).

    Raises:
        FileNotFoundError: If ``run_dir`` or its ``ipc/`` subdirectory does not
            exist, or if no ``*.v1.json`` IPC files are found.
        ValueError: If an IPC file is malformed, missing required fields, no
            name entries are found, or this run directory has already been
            imported.
    """
    run_dir_resolved = run_dir.resolve()
    if not run_dir_resolved.is_dir():
        raise FileNotFoundError(f"Run directory does not exist: {run_dir_resolved}")

    ipc_dir = run_dir_resolved / "ipc"
    if not ipc_dir.is_dir():
        raise FileNotFoundError(f"IPC directory not found: {ipc_dir}")

    # Only selection files carry payload.params.name_class and
    # payload.selected_names.  Other IPC artifacts (candidates, walks, package,
    # walker_run_state, etc.) use different schemas and must be skipped.
    ipc_files = sorted(ipc_dir.glob("*_selections.v1.json"))
    if not ipc_files:
        raise FileNotFoundError(f"No *_selections.v1.json IPC files found in: {ipc_dir}")

    resolved_package_name = (package_name or "").strip() or run_dir_resolved.name

    # Group names by name_class across all IPC files.  Multiple IPC files may
    # share the same name_class; their names are merged into a single table so
    # the generation mapper sees exactly one source_txt_name per class.
    names_by_class: dict[str, list[str]] = {}
    for ipc_path in ipc_files:
        with open(ipc_path, encoding="utf-8") as handle:
            ipc_data = json.load(handle)

        if not isinstance(ipc_data, dict):
            raise ValueError(f"IPC file root must be an object: {ipc_path.name}")

        payload = ipc_data.get("payload")
        if not isinstance(payload, dict):
            raise ValueError(f"IPC file missing 'payload' object: {ipc_path.name}")

        params = payload.get("params")
        if not isinstance(params, dict):
            raise ValueError(f"IPC file missing 'payload.params' object: {ipc_path.name}")

        name_class = str(params.get("name_class", "")).strip()
        if not name_class:
            raise ValueError(f"IPC file missing 'payload.params.name_class': {ipc_path.name}")

        selected_names = payload.get("selected_names")
        if not isinstance(selected_names, list):
            raise ValueError(f"IPC file missing 'payload.selected_names' list: {ipc_path.name}")

        for entry in selected_names:
            if not isinstance(entry, dict):
                continue
            name_value = str(entry.get("name", "")).strip()
            if not name_value:
                continue
            names_by_class.setdefault(name_class, []).append(name_value)

    if not names_by_class:
        raise ValueError("No name entries found across all IPC files in the run.")

    # Use the resolved run_dir path as the metadata_json_path sentinel and a
    # fixed literal as package_zip_path.  Together they form a unique key that
    # prevents re-importing the same run directory.
    run_dir_str = str(run_dir_resolved)
    ipc_sentinel = "(ipc-run-import)"

    try:
        cursor = conn.execute(
            """
            INSERT INTO imported_packages (
                package_name,
                imported_at,
                metadata_json_path,
                package_zip_path
            ) VALUES (?, ?, ?, ?)
            """,
            (
                resolved_package_name,
                datetime.now(timezone.utc).isoformat(),
                run_dir_str,
                ipc_sentinel,
            ),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return a row id for imported package insert.")
        package_id = int(cursor.lastrowid)

        created_tables: list[dict[str, Any]] = []
        # Sort by name_class for deterministic table index assignment.
        for index, (name_class, names) in enumerate(sorted(names_by_class.items()), start=1):
            # source_txt_name uses the nltk_{name_class}.txt convention:
            #   _map_source_txt_name_to_generation_class  → class_key = name_class
            #   _extract_syllable_option_from_source_txt_name → None → treated as "all"
            source_txt_name = f"nltk_{name_class}.txt"

            table_name = build_package_table_name(
                resolved_package_name, f"nltk_{name_class}", package_id, index
            )
            create_text_table(conn, table_name)

            rows = [(i + 1, name) for i, name in enumerate(names)]
            insert_text_rows(conn, table_name, rows)

            conn.execute(
                """
                INSERT INTO package_tables (
                    package_id, source_txt_name, table_name, row_count
                ) VALUES (?, ?, ?, ?)
                """,
                (package_id, source_txt_name, table_name, len(rows)),
            )
            created_tables.append(
                {
                    "source_txt_name": source_txt_name,
                    "table_name": table_name,
                    "row_count": len(rows),
                }
            )

        conn.commit()
        return {
            "message": (
                f"Imported run '{resolved_package_name}' with "
                f"{len(created_tables)} class table(s)."
            ),
            "package_id": package_id,
            "package_name": resolved_package_name,
            "tables": created_tables,
        }

    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError(f"Run directory '{run_dir_str}' has already been imported.") from exc
    except Exception:
        conn.rollback()
        raise


__all__ = [
    "load_metadata_json",
    "read_txt_rows",
    "import_package_pair",
    "import_from_run_directory",
]

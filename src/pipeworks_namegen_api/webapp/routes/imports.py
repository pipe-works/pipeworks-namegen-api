"""Import route handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol


class _ImportHandler(Protocol):
    """Structural protocol for import endpoint handler behavior."""

    db_path: Path

    def _read_json_body(self) -> dict[str, Any]: ...

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None: ...


def post_import(
    handler: _ImportHandler,
    *,
    connect_database: Callable[..., Any],
    initialize_schema: Callable[..., None],
    import_package_pair: Callable[..., dict[str, Any]],
    on_import_success: Callable[[], None] | None = None,
) -> None:
    """Import one metadata+zip pair and create tables for included txt data."""
    try:
        payload = handler._read_json_body()
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return

    metadata_raw = str(payload.get("metadata_json_path", "")).strip()
    zip_raw = str(payload.get("package_zip_path", "")).strip()
    if not metadata_raw or not zip_raw:
        handler._send_json(
            {"error": "Both 'metadata_json_path' and 'package_zip_path' are required."},
            status=400,
        )
        return

    metadata_path = Path(metadata_raw).expanduser()
    zip_path = Path(zip_raw).expanduser()

    try:
        with connect_database(handler.db_path) as conn:
            initialize_schema(conn)
            result = import_package_pair(conn, metadata_path=metadata_path, zip_path=zip_path)
        if on_import_success is not None:
            on_import_success()
        handler._send_json(result)
    except (FileNotFoundError, ValueError) as exc:
        handler._send_json({"error": str(exc)}, status=400)
    except Exception as exc:  # nosec B110 - converted into controlled API response
        handler._send_json({"error": f"Import failed: {exc}"}, status=500)


def post_import_from_run(
    handler: _ImportHandler,
    *,
    connect_database: Callable[..., Any],
    initialize_schema: Callable[..., None],
    import_from_run_directory: Callable[..., dict[str, Any]],
    on_import_success: Callable[[], None] | None = None,
) -> None:
    """Import name data from a namegen-lexicon output run directory.

    Expected JSON body fields:
        - ``run_dir`` (str, required): Absolute path to the run directory.
        - ``package_name`` (str, optional): Human-readable package label.
          Defaults to the run directory stem when omitted.
    """
    try:
        payload = handler._read_json_body()
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return

    run_dir_raw = str(payload.get("run_dir", "")).strip()
    if not run_dir_raw:
        handler._send_json({"error": "'run_dir' is required."}, status=400)
        return

    package_name_raw: str | None = str(payload.get("package_name", "")).strip() or None

    run_dir = Path(run_dir_raw).expanduser()

    try:
        with connect_database(handler.db_path) as conn:
            initialize_schema(conn)
            result = import_from_run_directory(
                conn,
                run_dir=run_dir,
                package_name=package_name_raw,
            )
        if on_import_success is not None:
            on_import_success()
        handler._send_json(result)
    except (FileNotFoundError, ValueError) as exc:
        handler._send_json({"error": str(exc)}, status=400)
    except Exception as exc:  # nosec B110 - converted into controlled API response
        handler._send_json({"error": f"Import failed: {exc}"}, status=500)


__all__ = ["post_import", "post_import_from_run"]

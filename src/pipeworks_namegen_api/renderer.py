"""Deterministic name rendering helpers for API compatibility.

This module mirrors the runtime-safe renderer behavior from legacy
``pipeworks_name_generation`` so the API extraction can proceed without waiting
for a published core package artifact that exposes renderer symbols.

TODO(phase3): switch imports to ``pipeworks_namegen_core.renderer`` once
``pipeworks-namegen-core`` publishes a release containing the extracted
renderer surface.
"""

from __future__ import annotations

from typing import Sequence

RENDER_STYLES: set[str] = {"raw", "lower", "upper", "title", "sentence"}


def normalize_render_style(raw_style: str | None) -> str:
    """Normalize and validate a render style value."""
    if raw_style is None:
        return "raw"

    normalized = str(raw_style).strip().lower()
    if not normalized:
        return "raw"

    if normalized not in RENDER_STYLES:
        allowed = ", ".join(sorted(RENDER_STYLES))
        raise ValueError(f"Unknown render style: {raw_style!r}. Allowed: {allowed}.")

    return normalized


def render_name(name: str, style: str | None = None) -> str:
    """Render one name using a supported style."""
    normalized = normalize_render_style(style)

    if normalized == "raw":
        return name
    if normalized == "lower":
        return name.lower()
    if normalized == "upper":
        return name.upper()
    if normalized == "sentence":
        if not name:
            return name
        return name[:1].upper() + name[1:].lower()

    return name.title()


def render_names(names: Sequence[str], style: str | None = None) -> list[str]:
    """Render a sequence of names with the same style."""
    normalized = normalize_render_style(style)
    if normalized == "raw":
        return list(names)

    return [render_name(name, normalized) for name in names]

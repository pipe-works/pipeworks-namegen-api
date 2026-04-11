[![CI](https://github.com/pipe-works/pipeworks-namegen-api/actions/workflows/ci.yml/badge.svg)](https://github.com/pipe-works/pipeworks-namegen-api/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/pipe-works/pipeworks-namegen-api/branch/main/graph/badge.svg)](https://codecov.io/gh/pipe-works/pipeworks-namegen-api) [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0) [![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# pipeworks-namegen-api

`pipeworks-namegen-api` is the canonical HTTP runtime for PipeWorks name
generation. It owns the `/api/generate` service contract, the packaged webapp
runtime, and the service-side persistence for imported name packages and user
favorites.

## PipeWorks Workspace

These repositories are designed to live inside a shared PipeWorks workspace
rooted at `/srv/work/pipeworks`.

- `repos/` contains source checkouts only.
- `venvs/` contains per-project virtual environments such as `pw-mud-server`.
- `runtime/` contains mutable runtime state such as databases, exports, session
  files, and caches.
- `logs/` contains service-owned log output when a project writes logs outside
  the process manager.
- `config/` contains workspace-level configuration files that should not be
  treated as source.
- `bin/` contains optional workspace helper scripts.
- `home/` is reserved for workspace-local user data when a project needs it.

Across the PipeWorks ecosphere, the rule is simple: keep source in `repos/`,
keep mutable state outside the repo checkout, and use explicit paths between
repos when one project depends on another.

## What This Repo Owns

This repository is the source of truth for:

- the runtime HTTP contract used by downstream consumers such as
  `pipeworks_mud_server`
- the packaged webapp server under `pipeworks_namegen_api.webapp`
- service-owned SQLite persistence for imported packages and favorites
- deployment templates under `deploy/`

This repository does not own:

- the pure deterministic generator boundary
- corpus extraction, syllable analysis, or package authoring workflows
- shared workspace tooling outside the API runtime boundary

## Repository Layout

- `src/pipeworks_namegen_api/renderer.py` library-side rendering support
- `src/pipeworks_namegen_api/webapp/` runtime server, config, routes, adapters,
  persistence, and frontend assets
- `tests/` pytest coverage for the API contract, runtime, config, and deploy
  templates
- `deploy/` example INI, systemd, and nginx files
- `docs/` Sphinx documentation

## Relationship To The Other Namegen Repos

- `pipeworks-namegen-core`
  deterministic generation/rendering primitives
- `pipeworks-namegen-api`
  canonical runtime HTTP contract and persistence layer
- `pipeworks-namegen-lexicon`
  creator tooling, package authoring, and consumer-facing web surfaces

The split matters. Runtime generation and persistence belong here; package
creation and corpus exploration do not.

## Quick Start

### Requirements

- Python `>=3.12`
- a PipeWorks workspace rooted at `/srv/work/pipeworks`
- access to `pipeworks-namegen-core`, which is installed from GitHub by
  `pyproject.toml`

### Install

```bash
python3 -m venv /srv/work/pipeworks/venvs/pw-namegen-api
/srv/work/pipeworks/venvs/pw-namegen-api/bin/pip install -e ".[dev]"
```

### Prepare Workspace Config

The packaged webapp expects an INI file. A host-neutral workspace layout is:

```bash
mkdir -p /srv/work/pipeworks/config/pipeworks-namegen-api
cp deploy/server.ini.example /srv/work/pipeworks/config/pipeworks-namegen-api/server.ini
```

The shipped example uses service-owned writable paths. For a workspace-backed
setup, update the INI to point at directories under `/srv/work/pipeworks/runtime/`
such as:

- `/srv/work/pipeworks/runtime/namegen-api/name_packages.sqlite3`
- `/srv/work/pipeworks/runtime/namegen-api/user_favorites.sqlite3`
- `/srv/work/pipeworks/runtime/namegen-api/exports`
- `/srv/work/pipeworks/runtime/namegen-api/backups`

### Run The Full Webapp

```bash
/srv/work/pipeworks/venvs/pw-namegen-api/bin/python \
  -m pipeworks_namegen_api.webapp.server \
  --config /srv/work/pipeworks/config/pipeworks-namegen-api/server.ini
```

### Run API-Only

```bash
/srv/work/pipeworks/venvs/pw-namegen-api/bin/python \
  -m pipeworks_namegen_api.webapp.api \
  --config /srv/work/pipeworks/config/pipeworks-namegen-api/server.ini
```

## Configuration

The packaged CLI accepts:

- `--config` for the INI file path
- `--host` and `--port` to override bind settings
- `--favorites-db` to override the favorites SQLite path
- `--api-only` to disable UI/static serving
- `--quiet` to suppress verbose runtime logging

The shipped example config lives at `deploy/server.ini.example`. The webapp
expects a `[webapp]` section covering host, port, API-only mode, and writable
paths for the package store, favorites DB, exports, and backups.

## Validation And Development

Run the main checks from the repo root:

```bash
/srv/work/pipeworks/venvs/pw-namegen-api/bin/pytest
/srv/work/pipeworks/venvs/pw-namegen-api/bin/ruff check src tests
/srv/work/pipeworks/venvs/pw-namegen-api/bin/black --check src tests
/srv/work/pipeworks/venvs/pw-namegen-api/bin/mypy src
```

Typical smoke endpoints after startup are:

- `GET /health`
- `GET /api/health`
- `GET /api/version`
- `POST /api/generate`

A successful generation request still depends on imported package data being
present in the configured SQLite store.

## Deployment Templates

Host-neutral deployment examples are shipped in:

- `deploy/server.ini.example`
- `deploy/systemd/pipeworks-namegen-api.service.example`
- `deploy/nginx/name.api.example.org.conf.example`
- `deploy/README.md`

These templates are examples, not the runtime authority themselves.

## Documentation

Additional documentation lives in `docs/`.

## License

[GPL-3.0-or-later](LICENSE)

# pipeworks-namegen-api

`pipeworks-namegen-api` is the hosted HTTP runtime for PipeWorks name
generation. It owns the `/api/generate` service contract used by downstream
consumers such as `pipeworks_mud_server`.

This repo is not the right place to re-collapse the older
`pipeworks_name_generation` all-in-one model. Keep the service boundary narrow:

1. `pipeworks-namegen-api` owns HTTP runtime behavior and deployment guidance.
2. `pipeworks-namegen-core` owns deterministic generation primitives.
3. `pipeworks-namegen-lexicon` owns lexicon and pipeline tooling.

## Ownership

This repository is the source of truth for:

1. Runtime HTTP behavior for `/api/generate` and related endpoints.
2. API-process deployment guidance (`systemd`, nginx, runtime config, service
   data paths).
3. Versioned deployment templates under [`deploy/`](deploy/).

This repository does not own:

1. Lexicon or corpus-pipeline tooling.
2. A shared launcher spanning API and build-tool services.
3. Service-owned mutable runtime data inside the repo working tree.

## Current Host Model

The current Luminal deployment model is intentionally host-managed:

1. Repo checkout lives under `/srv/work/pipeworks/repos/pipeworks-namegen-api`.
2. The service venv lives outside the repo under
   `/srv/work/pipeworks/venvs/pw-namegen-api`.
3. Host-owned config lives outside the repo at
   `/etc/pipeworks/namegen-api/server.ini`.
4. Service-owned writable data lives outside the repo under
   `/var/lib/pipeworks-namegen-api`.
5. The backend binds to `127.0.0.1:8360`.
6. nginx is the canonical entry point at `https://namegen-api.luminal.local`.
7. The production process target is
   `python -m pipeworks_namegen_api.webapp.api`.

This split is deliberate. The repo provides source code and deployment
templates; the host owns runtime shape, trust, unit wiring, and writable state.

## Workspace Layout

For the current Luminal rollout, think in terms of five separate surfaces:

1. Repo source:
   [`/srv/work/pipeworks/repos/pipeworks-namegen-api`](.)
2. Venv:
   `/srv/work/pipeworks/venvs/pw-namegen-api`
3. Host config:
   `/etc/pipeworks/namegen-api/server.ini`
4. Service runtime data:
   `/var/lib/pipeworks-namegen-api`
5. Reverse proxy and TLS:
   nginx + `namegen-api.luminal.local`

Do not move runtime SQLite files, export targets, or backup targets back into
the repo tree for convenience.

## Local Development

Editable install:

```bash
PYENV_VERSION=png pip install -e ".[dev]"
```

Run the full web app locally:

```bash
PYENV_VERSION=png python -m pipeworks_namegen_api.webapp.server --config server.ini
```

Run the API-only process:

```bash
PYENV_VERSION=png python -m pipeworks_namegen_api.webapp.api --config server.ini
```

For local development, a repo-local `server.ini` is fine. For host-managed
deployment, prefer an explicit config path outside the repo.

## Deployment Baseline

Canonical deployment guidance and templates live in:

1. [`docs/source/deployment.rst`](docs/source/deployment.rst)
2. [`deploy/systemd/pipeworks-namegen-api.service.example`](deploy/systemd/pipeworks-namegen-api.service.example)
3. [`deploy/nginx/name.api.example.org.conf.example`](deploy/nginx/name.api.example.org.conf.example)
4. [`deploy/server.ini.example`](deploy/server.ini.example)

The deployment templates intentionally avoid user-home paths and pyenv-coupled
interpreter paths.

## Runtime Paths

The deployed API expects service-owned writable paths outside the repo:

1. `db_path = /var/lib/pipeworks-namegen-api/name_packages.sqlite3`
2. `favorites_db_path = /var/lib/pipeworks-namegen-api/user_favorites.sqlite3`
3. `db_export_path = /var/lib/pipeworks-namegen-api/exports`
4. `db_backup_path = /var/lib/pipeworks-namegen-api/backups`

Configured export and backup targets may be either explicit file paths or
directory paths. When a directory path is used, the runtime writes timestamped
output files inside that directory.

## Verification Notes

The first Luminal rollout has been verified through:

1. `GET /health`
2. `GET /api/health`
3. `GET /api/version`
4. Real `POST /api/generate` requests on both:
   `http://127.0.0.1:8360`
   `https://namegen-api.luminal.local`

One practical detail matters for real generation verification: a successful
`POST /api/generate` requires imported package data to exist in the configured
SQLite database first.

Another practical detail comes from the `systemd` sandboxing in the deployment
template:

1. `PrivateTmp=true` means the service does not share the host's normal `/tmp`.
2. `ProtectHome=true` means the service should not rely on reading import inputs
   from user home directories.
3. Import source files therefore need to live in a service-readable location
   such as `/var/lib/pipeworks-namegen-api`.

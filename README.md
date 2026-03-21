# pipeworks-namegen-api

`pipeworks-namegen-api` is the canonical production runtime for Pipeworks name generation.
It owns the `/api/generate` service contract used by downstream consumers, including
`pipeworks_mud_server`.

## Runtime Ownership

This repository is the only source of truth for:

1. Production HTTP runtime behavior (`/api/generate` and related API endpoints).
2. Service deployment guidance (systemd, nginx, runtime config paths).
3. Production operational templates under [`deploy/`](deploy/).

Out of scope:

1. Lexicon/corpus pipeline tooling (`pipeworks-namegen-lexicon`).
2. Deterministic generation primitives library ownership (`pipeworks-namegen-core`).

## Running Locally

```bash
PYENV_VERSION=png pip install -e ".[dev]"
PYENV_VERSION=png python -m pipeworks_namegen_api.webapp.server --config server.ini
```

API-only mode:

```bash
PYENV_VERSION=png python -m pipeworks_namegen_api.webapp.api --config server.ini
```

## Deployment

Production deployment guidance and templates live in:

1. [`docs/source/deployment.rst`](docs/source/deployment.rst)
2. [`deploy/systemd/pipeworks-namegen-api.service.example`](deploy/systemd/pipeworks-namegen-api.service.example)
3. [`deploy/nginx/name.api.example.org.conf.example`](deploy/nginx/name.api.example.org.conf.example)
4. [`deploy/server.ini.example`](deploy/server.ini.example)

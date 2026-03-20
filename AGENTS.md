# AGENTS.md

## Foundation

This repository follows Pipe-Works org standards and reusable workflow conventions.

## Scope

- Production API service for name generation.
- Existing namegen web UI and API-only mode runtime ownership.
- Contract compatibility for `/api/generate` consumers.

## Non-Negotiables

- Preserve API contract stability for `pipeworks_mud_server`.
- Keep runtime/config/deployment boundaries explicit.
- Depend on `pipeworks-namegen-core` for deterministic generation behavior.

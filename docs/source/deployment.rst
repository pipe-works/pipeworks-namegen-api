Deployment (systemd + nginx)
============================

This document defines the canonical production deployment baseline for
``pipeworks-namegen-api``.

Ownership and Scope
-------------------

This repository is the authoritative runtime/deployment source for production
name generation service ownership.

Production consumers, including ``pipeworks_mud_server``, should integrate
through the HTTP API boundary exposed by this service.

Keep the service boundary narrow:

1. ``pipeworks-namegen-api`` owns hosted HTTP runtime and deployment.
2. ``pipeworks-namegen-core`` owns deterministic generation primitives.
3. ``pipeworks-namegen-lexicon`` owns lexicon and pipeline tooling.

Do not reintroduce a shared runtime shape that mixes API hosting, deterministic
library ownership, and offline build-tool workflows into one deployed service.

Host Model
----------

The current intended deployment model is host-managed rather than repo-managed:

1. Repo checkout lives outside host config and service data paths.
2. The service venv lives outside the repo.
3. Host-owned config lives under ``/etc/pipeworks/namegen-api/``.
4. Service-owned writable data lives under
   ``/var/lib/pipeworks-namegen-api/``.
5. The backend binds to localhost and is exposed publicly through nginx.

For the current Luminal rollout, that split is:

1. Repo: ``/srv/work/pipeworks/repos/pipeworks-namegen-api``
2. Venv: ``/srv/work/pipeworks/venvs/pw-namegen-api``
3. Config: ``/etc/pipeworks/namegen-api/server.ini``
4. Service data: ``/var/lib/pipeworks-namegen-api``
5. Hostname: ``https://namegen-api.luminal.local``

Deployment Artifacts
--------------------

Reference templates are versioned in this repository:

1. ``deploy/systemd/pipeworks-namegen-api.service.example``
2. ``deploy/nginx/name.api.example.org.conf.example``
3. ``deploy/server.ini.example``

These templates intentionally avoid user-home and pyenv-coupled paths so they
remain portable across hosts and environments.

Server Runtime
--------------

Run the API-only process for production traffic:

.. code-block:: bash

   python -m pipeworks_namegen_api.webapp.api --config /etc/pipeworks/namegen-api/server.ini

The ``server.ini`` template defaults to API-only routing.

Configured database export and backup targets may be either explicit file paths
or directory paths. When a directory path is used, the runtime writes a
timestamped SQLite file inside that directory.

Recommended steady-state host values:

.. code-block:: ini

   [webapp]
   host = 127.0.0.1
   port = 8360
   api_only = true
   serve_ui = false
   db_path = /var/lib/pipeworks-namegen-api/name_packages.sqlite3
   favorites_db_path = /var/lib/pipeworks-namegen-api/user_favorites.sqlite3
   db_export_path = /var/lib/pipeworks-namegen-api/exports
   db_backup_path = /var/lib/pipeworks-namegen-api/backups

Avoid repo-local runtime databases and mutable service state in the source
tree for host-managed deployment.

systemd Baseline
----------------

Install and adapt:

1. Copy ``deploy/systemd/pipeworks-namegen-api.service.example`` to
   ``/etc/systemd/system/pipeworks-namegen-api.service``.
2. Update the service user/group and filesystem paths.
3. Ensure read/write paths exist and are writable by the service account.
4. Keep the hardening flags unless observed runtime behavior proves a specific
   need to relax them.
5. Reload and start:

.. code-block:: bash

   sudo systemctl daemon-reload
   sudo systemctl start pipeworks-namegen-api.service

Luminal example:

.. code-block:: ini

   [Service]
   User=pipeworks
   Group=pipeworks
   WorkingDirectory=/srv/work/pipeworks/repos/pipeworks-namegen-api
   ExecStart=/srv/work/pipeworks/venvs/pw-namegen-api/bin/python -m pipeworks_namegen_api.webapp.api --config /etc/pipeworks/namegen-api/server.ini

Important sandboxing implications from the template:

1. ``PrivateTmp=true`` means the running service does not share the host's
   normal ``/tmp`` namespace.
2. ``ProtectHome=true`` means the service should not rely on reading import
   inputs from user home directories.
3. Import source files therefore need to live in a service-readable location
   such as ``/var/lib/pipeworks-namegen-api``.

Enable at boot only after explicit operational review:

.. code-block:: bash

   sudo systemctl enable pipeworks-namegen-api.service

nginx Baseline
--------------

Install and adapt:

1. Copy ``deploy/nginx/name.api.example.org.conf.example`` into your nginx
   site config location.
2. Update ``server_name`` and TLS certificate paths.
3. Proxy ``/api/`` to the localhost backend.
4. Decide explicitly whether ``/health`` should also be exposed in addition to
   ``/api/health``.
5. Validate and reload:

.. code-block:: bash

   sudo nginx -t
   sudo systemctl reload nginx

Luminal example:

1. Canonical hostname is ``namegen-api.luminal.local``.
2. HTTP port 80 redirects to HTTPS.
3. TLS is terminated at nginx.
4. nginx proxies to ``http://127.0.0.1:8360``.

Operational Notes
-----------------

1. Keep ``pipeworks-namegen-api`` as the only runtime service owner for
   production name generation.
2. Avoid host-specific interpreter paths in unit files; prefer managed venv
   paths under service-owned directories.
3. Keep ingress (TLS, rate limiting, request body limits) at the reverse proxy.
4. The service exposes both ``/api/health`` and ``/health`` for lightweight
   liveness checks.
5. A real ``POST /api/generate`` verification requires imported package data to
   exist in the configured SQLite database first; health and version checks
   alone do not prove generation behavior.

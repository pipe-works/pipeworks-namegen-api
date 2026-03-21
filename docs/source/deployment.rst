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

systemd Baseline
----------------

Install and adapt:

1. Copy ``deploy/systemd/pipeworks-namegen-api.service.example`` to
   ``/etc/systemd/system/pipeworks-namegen-api.service``.
2. Update the service user/group and filesystem paths.
3. Ensure read/write paths exist and are writable by the service account.
4. Enable and start:

.. code-block:: bash

   sudo systemctl daemon-reload
   sudo systemctl enable pipeworks-namegen-api.service
   sudo systemctl start pipeworks-namegen-api.service

nginx Baseline
--------------

Install and adapt:

1. Copy ``deploy/nginx/name.api.example.org.conf.example`` into your nginx
   site config location.
2. Update ``server_name`` and TLS certificate paths.
3. Validate and reload:

.. code-block:: bash

   sudo nginx -t
   sudo systemctl reload nginx

Operational Notes
-----------------

1. Keep ``pipeworks-namegen-api`` as the only runtime service owner for
   production name generation.
2. Avoid host-specific interpreter paths in unit files; prefer managed venv
   paths under service-owned directories.
3. Keep ingress (TLS, rate limiting, request body limits) at the reverse proxy.

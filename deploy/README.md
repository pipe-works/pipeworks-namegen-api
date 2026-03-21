# Deployment Templates

This directory contains canonical production deployment templates for
`pipeworks-namegen-api`.

1. `systemd/pipeworks-namegen-api.service.example`
2. `nginx/name.api.example.org.conf.example`
3. `server.ini.example`

All templates are intentionally host-portable:

1. No user-home absolute paths (for example, `/Users/<name>` or `/home/<name>`).
2. No pyenv-coupled interpreter paths.
3. Service module target set to `pipeworks_namegen_api.webapp.api`.

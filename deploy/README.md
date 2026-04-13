# Deployment Templates

This directory contains deployment templates for `pipeworks-namegen-api`.

## Production templates

1. `systemd/pipeworks-namegen-api.service.example`
2. `nginx/name.api.example.org.conf.example`
3. `server.ini.example`

All production templates are intentionally host-portable:

1. No user-home absolute paths (for example, `/Users/<name>` or `/home/<name>`).
2. No pyenv-coupled interpreter paths.
3. Service module target set to `pipeworks_namegen_api.webapp.api`.

## Luminal development host templates

4. `nginx/namegen-api.luminal.local`

The luminal template reflects the live nginx vhost deployed at
`/etc/nginx/sites-available/namegen-api.luminal.local` on `luminal.local`.
It includes CORS headers for `https://pipeworks-org.luminal.local`, which
calls `/api/generate` directly from the browser on the explore page.

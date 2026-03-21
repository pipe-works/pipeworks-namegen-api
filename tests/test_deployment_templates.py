"""Deployment-template regression tests.

These checks keep Phase 6 guarantees stable by ensuring deployment artifacts
remain portable and consistently target the API runtime owned by this repo.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = ROOT / "deploy"
SYSTEMD_TEMPLATE = DEPLOY_DIR / "systemd" / "pipeworks-namegen-api.service.example"
NGINX_TEMPLATE = DEPLOY_DIR / "nginx" / "name.api.example.org.conf.example"
SERVER_INI_TEMPLATE = DEPLOY_DIR / "server.ini.example"


def _read_text(path: Path) -> str:
    """Read UTF-8 text from a deployment template."""
    return path.read_text(encoding="utf-8")


def test_deployment_templates_exist() -> None:
    """All canonical deployment templates should be present in-repo."""
    assert DEPLOY_DIR.exists()
    assert SYSTEMD_TEMPLATE.exists()
    assert NGINX_TEMPLATE.exists()
    assert SERVER_INI_TEMPLATE.exists()


def test_systemd_template_targets_api_module() -> None:
    """systemd template should launch the API-only entrypoint module."""
    content = _read_text(SYSTEMD_TEMPLATE)
    assert "pipeworks_namegen_api.webapp.api" in content
    assert "--config /etc/pipeworks/namegen-api/server.ini" in content


def test_server_ini_template_defaults_to_api_only() -> None:
    """Runtime INI template should enforce API-only mode for production usage."""
    content = _read_text(SERVER_INI_TEMPLATE)
    assert "api_only = true" in content
    assert "serve_ui = false" in content


def test_deployment_templates_avoid_user_home_or_pyenv_coupling() -> None:
    """Templates should not hardcode user-home or pyenv-specific filesystem paths."""
    for template in (SYSTEMD_TEMPLATE, NGINX_TEMPLATE, SERVER_INI_TEMPLATE):
        content = _read_text(template)
        assert "/Users/" not in content
        assert "/home/" not in content
        assert ".pyenv" not in content

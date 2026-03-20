from pipeworks_namegen_api import healthcheck


def test_healthcheck_returns_ok() -> None:
    assert healthcheck() == "ok"

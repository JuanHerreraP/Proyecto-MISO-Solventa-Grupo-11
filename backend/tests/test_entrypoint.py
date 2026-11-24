"""Verifica que la configuración de ECS no exponga secretos en argumentos."""

import runpy
from pathlib import Path

import pytest


def test_entrypoint_materializa_secretos_y_codifica_password(monkeypatch, tmp_path):
    import os
    import tempfile

    class Arranque(Exception):
        pass

    monkeypatch.setattr(tempfile, "mkdtemp", lambda **_: str(tmp_path))
    for variable in ("DATABASE_URL", "JWT_PRIVATE_KEY_PATH", "JWT_PUBLIC_KEY_PATH"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("DB_HOST", "database.internal")
    monkeypatch.setenv("DB_PASSWORD", "p@ss:/word")
    monkeypatch.setenv("JWT_PRIVATE_KEY_PEM", "private pem\n")
    monkeypatch.setenv("JWT_PUBLIC_KEY_PEM", "public pem\n")

    def ejecutar(programa, argumentos):
        assert programa == "uvicorn"
        assert "p@ss" not in str(argumentos)
        assert os.environ["DATABASE_URL"] == (
            "postgresql+psycopg://solventa:p%40ss%3A%2Fword@"
            "database.internal:5432/solventa?sslmode=require"
        )
        for tipo in ("PRIVATE", "PUBLIC"):
            assert f"JWT_{tipo}_KEY_PEM" not in os.environ
            archivo = Path(os.environ[f"JWT_{tipo}_KEY_PATH"])
            assert archivo.read_text() == f"{tipo.lower()} pem\n"
            assert archivo.stat().st_mode & 0o777 == 0o600
        assert "DB_PASSWORD" not in os.environ
        raise Arranque

    monkeypatch.setattr(os, "execvp", ejecutar)
    with pytest.raises(Arranque):
        runpy.run_path(str(Path(__file__).parents[1] / "entrypoint.py"), run_name="__main__")


def test_el_rol_worker_pagos_arranca_el_consumidor_de_pagos_y_no_la_api(monkeypatch):
    import os

    llamadas = []
    for variable in ("DB_HOST", "JWT_PRIVATE_KEY_PEM", "JWT_PUBLIC_KEY_PEM"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("SOLVENTA_ROL", "worker-pagos")
    monkeypatch.setattr("app.desembolsos.worker.ejecutar", lambda: llamadas.append("pagos"))
    monkeypatch.setattr(os, "execvp", lambda *_: pytest.fail("No debe arrancar la API."))

    runpy.run_path(str(Path(__file__).parents[1] / "entrypoint.py"), run_name="__main__")

    assert llamadas == ["pagos"]

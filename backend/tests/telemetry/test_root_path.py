"""El proveedor fija su root_path desde el entorno para funcionar detrás del proxy (HU20).

Con `TELEMETRY_ROOT_PATH=/api/telemetry`, FastAPI expone Swagger, ReDoc y el openapi.json bajo ese
prefijo, de modo que "Try it out" apunta a las rutas correctas a través del proxy del backend.
"""

import importlib


def test_root_path_se_toma_del_entorno(monkeypatch) -> None:
    monkeypatch.setenv("TELEMETRY_ROOT_PATH", "/api/telemetry")
    # Sin REDIS_URL: usa el almacén en memoria y no intenta conectarse a Redis.
    monkeypatch.delenv("REDIS_URL", raising=False)
    import mocks.telemetry.main as main

    main = importlib.reload(main)
    try:
        assert main.app.root_path == "/api/telemetry"
    finally:
        # Se restaura el módulo a su estado por defecto para no afectar a otras pruebas.
        monkeypatch.delenv("TELEMETRY_ROOT_PATH", raising=False)
        importlib.reload(main)


def test_sin_root_path_es_vacio(monkeypatch) -> None:
    monkeypatch.delenv("TELEMETRY_ROOT_PATH", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    import mocks.telemetry.main as main

    main = importlib.reload(main)
    assert main.app.root_path == ""

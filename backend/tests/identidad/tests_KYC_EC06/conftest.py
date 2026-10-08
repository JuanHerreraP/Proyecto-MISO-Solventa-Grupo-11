import socket
import subprocess
import sys
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _esperar_puerto(
    host: str,
    port: int,
    timeout: float = 10.0,
):
    inicio = time.time()

    while time.time() - inicio < timeout:
        try:
            with socket.create_connection(
                (host, port),
                timeout=0.5,
            ):
                return

        except OSError:
            time.sleep(0.1)

    raise RuntimeError(
        f"No fue posible iniciar el servicio en {host}:{port}"
    )


@pytest.fixture(
    scope="session",
    autouse=True,
)
def kyc_mock_servers():

    servicios = [
        (
            "mocks.kyc.provider_a:app",
            8001,
        ),
        (
            "mocks.kyc.provider_b:app",
            8002,
        ),
        (
            "mocks.kyc.provider_c:app",
            8003,
        ),
    ]

    procesos = []

    for modulo, puerto in servicios:
        proceso = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                modulo,
                "--host",
                "127.0.0.1",
                "--port",
                str(puerto),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        procesos.append(proceso)

    for _, puerto in servicios:
        _esperar_puerto(
            "127.0.0.1",
            puerto,
        )

    yield

    for proceso in procesos:
        proceso.terminate()

    for proceso in procesos:
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()


@pytest.fixture
def client_with_provider(monkeypatch):

    def _build(
        provider_name: str,
    ) -> TestClient:

        monkeypatch.setenv(
            "KYC_PROVIDER",
            provider_name,
        )

        return TestClient(app)

    return _build
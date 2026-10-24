"""Pruebas del portal PSE simulado (desarrollo).

El portal imita el comportamiento externo de PSE: muestra una página de confirmación y,
al elegir, firma internamente la confirmación y la aplica por el servicio de pagos.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.cotizaciones import ActorCotizacion, TipoActorCotizacion, actor_actual
from app.api.pagos import obtener_pasarela, obtener_servicio
from app.cotizaciones.dominio.modelos import (
    CoberturaPrincipal,
    Cotizacion,
    EstadoCotizacion,
    RamoSeguro,
)
from app.cotizaciones.repositorio import RepositorioCotizacionesEnMemoria
from app.identidad.modelos import Rol
from app.main import app
from app.pagos.pasarela_simulada import PasarelaSimulada
from app.pagos.repositorio import RepositorioPagosEnMemoria
from app.pagos.servicio import ServicioPagos

RUTA_PAGOS = "/api/v1/pagos"
PORTAL = "/api/v1/pagos/pse-simulado"
AHORA = datetime(2027, 1, 1, tzinfo=UTC)
SECRETO = "secreto-de-pruebas"


def _cotizacion() -> Cotizacion:
    return Cotizacion(
        cotizacion_id="COT-001",
        cliente_id="CLI-001",
        ramo=RamoSeguro.VIAJE,
        estado=EstadoCotizacion.VIGENTE,
        prima_total=Decimal("45000.00"),
        cobertura_principal=CoberturaPrincipal(
            codigo="ASISTENCIA_VIAJE", nombre="Asistencia", suma_asegurada=Decimal("1000000")
        ),
        creada_en=AHORA,
        vigente_hasta=AHORA + timedelta(days=7),
    )


@pytest.fixture
def entorno(monkeypatch):
    monkeypatch.setenv("PAGOS_WEBHOOK_SECRET", SECRETO)
    cotizaciones = RepositorioCotizacionesEnMemoria()
    cotizaciones.guardar(_cotizacion())
    servicio = ServicioPagos(
        RepositorioPagosEnMemoria(), cotizaciones, PasarelaSimulada(), reloj=lambda: AHORA
    )
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    app.dependency_overrides[obtener_pasarela] = lambda: PasarelaSimulada()
    app.dependency_overrides[actor_actual] = lambda: ActorCotizacion(
        tipo=TipoActorCotizacion.USUARIO, actor_id="CLI-001", rol=Rol.CLIENTE
    )
    yield TestClient(app), cotizaciones
    app.dependency_overrides.clear()


def _iniciar_pse(cliente) -> str:
    r = cliente.post(
        RUTA_PAGOS,
        json={"cotizacion_id": "COT-001", "metodo": "PSE", "codigo_banco": "1007"},
        headers={"Idempotency-Key": "llave-pse-01"},
    )
    assert r.json()["estado"] == "PENDIENTE"
    return r.json()["referencia_pasarela"]


def test_la_redireccion_apunta_al_portal_pse(entorno) -> None:
    cliente, _ = entorno
    r = cliente.post(
        RUTA_PAGOS,
        json={
            "cotizacion_id": "COT-001",
            "metodo": "PSE",
            "codigo_banco": "1007",
            "url_retorno": "http://localhost:5173/cotizar",
        },
        headers={"Idempotency-Key": "llave-pse-02"},
    )
    url = r.json()["url_redireccion"]
    assert f"{PORTAL}/" in url
    assert "url_retorno=" in url


def test_portal_muestra_la_pagina_de_confirmacion(entorno) -> None:
    cliente, _ = entorno
    referencia = _iniciar_pse(cliente)

    pagina = cliente.get(f"{PORTAL}/{referencia}")

    assert pagina.status_code == 200
    assert "PSE" in pagina.text
    assert referencia in pagina.text


def test_portal_con_referencia_desconocida_responde_404(entorno) -> None:
    cliente, _ = entorno
    assert cliente.get(f"{PORTAL}/PSP-inexistente").status_code == 404


def test_pagar_en_el_portal_aprueba_y_redirige(entorno) -> None:
    cliente, cotizaciones = entorno
    referencia = _iniciar_pse(cliente)

    resuelto = cliente.get(
        f"{PORTAL}/resolver",
        params={
            "referencia": referencia,
            "decision": "APROBADO",
            "url_retorno": "http://localhost:5173/cotizar",
        },
        follow_redirects=False,
    )

    assert resuelto.status_code == 303
    assert "estado=APROBADO" in resuelto.headers["location"]
    assert cotizaciones.obtener("COT-001").estado is EstadoCotizacion.ACEPTADA


def test_rechazar_en_el_portal_deja_la_cotizacion_vigente(entorno) -> None:
    cliente, cotizaciones = entorno
    referencia = _iniciar_pse(cliente)

    resuelto = cliente.get(
        f"{PORTAL}/resolver",
        params={"referencia": referencia, "decision": "RECHAZADO"},
    )

    assert resuelto.json()["estado"] == "RECHAZADO"
    assert cotizaciones.obtener("COT-001").estado is EstadoCotizacion.VIGENTE

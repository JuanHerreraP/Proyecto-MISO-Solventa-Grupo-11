"""Pruebas del endpoint de historial de la póliza (HU25)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.historial_poliza import obtener_servicio
from app.api.seguridad import get_current_user
from app.desembolsos.repositorio import RepositorioDesembolsosEnMemoria
from app.identidad.modelos import Rol
from app.main import app
from app.pagos.repositorio import RepositorioPagosEnMemoria
from app.polizas.historial import ServicioHistorialPoliza
from app.polizas.repositorio import RepositorioPolizasEnMemoria
from app.polizas.repositorio_endosos import RepositorioEndososEnMemoria
from tests.historial.fabrica import CLIENTE, POLIZA, desembolso, endoso, pago, poliza

RUTA = f"/api/v1/polizas/{POLIZA}/historial"
CLIENTE_USUARIO = SimpleNamespace(id=CLIENTE, email="ana@gmail.com", rol=Rol.CLIENTE.value)


@pytest.fixture
def entorno():
    repo_polizas = RepositorioPolizasEnMemoria()
    repo_polizas.guardar(poliza())
    repo_pagos = RepositorioPagosEnMemoria()
    repo_pagos.crear(pago())
    repo_endosos = RepositorioEndososEnMemoria(repo_polizas)
    repo_endosos.registrar(endoso(), repo_polizas.obtener(POLIZA))
    repo_desembolsos = RepositorioDesembolsosEnMemoria()
    repo_desembolsos.crear(desembolso())
    servicio = ServicioHistorialPoliza(repo_polizas, repo_pagos, repo_endosos, repo_desembolsos)

    app.dependency_overrides[obtener_servicio] = lambda: servicio
    app.dependency_overrides[get_current_user] = lambda: CLIENTE_USUARIO
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_cliente_consulta_su_poliza_200(entorno) -> None:
    r = entorno.get(RUTA)

    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    cuerpo = r.json()
    assert cuerpo["poliza_id"] == POLIZA
    assert cuerpo["numero_poliza"] == "SOLV-VIA-2026-00152"
    tipos = [m["tipo"] for m in cuerpo["movimientos"]]
    # Orden descendente: desembolso (07 nov), endoso (04 nov), emisión (20 oct 14:05),
    # pago (20 oct 13:45).
    assert tipos == [
        "DESEMBOLSO_INDEMNIZACION",
        "ENDOSO",
        "EMISION",
        "PAGO_PRIMA_INICIAL",
    ]


def test_movimiento_financiero_expone_referencia_de_pasarela(entorno) -> None:
    r = entorno.get(RUTA)
    pago_mov = next(m for m in r.json()["movimientos"] if m["tipo"] == "PAGO_PRIMA_INICIAL")
    assert pago_mov["referencia"] == "PAY-001"
    assert pago_mov["referencia_externa"] == "PSP-88910"
    assert pago_mov["monto"] == "125000.00"
    assert pago_mov["estado"] == "APROBADO"


def test_movimiento_endoso_expone_linaje_y_consentimiento(entorno) -> None:
    r = entorno.get(RUTA)
    endoso_mov = next(m for m in r.json()["movimientos"] if m["tipo"] == "ENDOSO")
    cambio = endoso_mov["cambios"][0]
    assert cambio["antes"] is None
    assert cambio["despues"]["codigo"] == "EQUIPAJE"
    assert endoso_mov["consentimiento"]["explicito"] is True
    assert endoso_mov["consentimiento"]["tipo"] == "CONFIRMACION_ENDOSO"


def test_no_expone_informacion_sensible(entorno) -> None:
    cuerpo = entorno.get(RUTA).text
    # Datos técnicos/sensibles que no deben salir en el historial.
    for prohibido in (
        "idempotency_key",
        "token_cuenta",
        "token_tarjeta",
        "ip_solicitante",
        "user_agent",
    ):
        assert prohibido not in cuerpo


def test_poliza_ajena_responde_403(entorno) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="OTRO", email="otro@gmail.com", rol=Rol.CLIENTE.value
    )
    r = entorno.get(RUTA)
    assert r.status_code == 403
    assert r.json()["detail"]["codigo"] == "ACCESS_DENIED"


def test_poliza_inexistente_responde_404(entorno) -> None:
    r = entorno.get("/api/v1/polizas/POL-404/historial")
    assert r.status_code == 404
    assert r.json()["detail"]["codigo"] == "POLIZA_NO_ENCONTRADA"


def test_rol_sin_permiso_responde_403(entorno) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="ASE-1", email="asesor@solventa.com", rol=Rol.ASESOR_VENTAS.value
    )
    r = entorno.get(RUTA)
    assert r.status_code == 403
    assert r.json()["detail"]["codigo"] == "ACCESS_DENIED"


def test_rol_interno_consulta_cualquier_poliza_200(entorno) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="OPS-1", email="ops@solventa.com", rol=Rol.OPERACIONES_SINIESTROS.value
    )
    r = entorno.get(RUTA)
    assert r.status_code == 200
    assert r.json()["poliza_id"] == POLIZA


def test_analista_cumplimiento_consulta_poliza_ajena_200(entorno) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="AUD-1", email="auditor@solventa.com", rol=Rol.ANALISTA_CUMPLIMIENTO.value
    )
    r = entorno.get(RUTA)
    assert r.status_code == 200
    cuerpo = r.json()
    # El auditor revisa pólizas de cualquier cliente: la póliza es del CLIENTE, no del auditor.
    assert cuerpo["poliza_id"] == POLIZA
    assert cuerpo["cliente_id"] == CLIENTE
    assert cuerpo["nombre_ramo"] == "Seguro de viaje"
    assert cuerpo["estado"] in {"VIGENTE", "VENCIDA", "CANCELADA"}


def test_analista_cumplimiento_ve_informacion_de_auditoria_del_endoso(entorno) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="AUD-1", email="auditor@solventa.com", rol=Rol.ANALISTA_CUMPLIMIENTO.value
    )
    endoso_mov = next(m for m in entorno.get(RUTA).json()["movimientos"] if m["tipo"] == "ENDOSO")
    # Datos técnicos que el cliente no ve, pero el auditor sí (HU25 §19).
    assert endoso_mov["auditoria"]["ip_solicitante"] == "10.0.0.1"
    assert endoso_mov["auditoria"]["user_agent"] == "pruebas"
    assert endoso_mov["auditoria"]["usuario_id"] == "USR-1"
    assert endoso_mov["auditoria"]["rol"] == "CLIENTE"
    # Desglose del ajuste de prima (HU25 §20).
    assert endoso_mov["ajuste_prima"]["prima_anterior"] == "125000.00"
    assert endoso_mov["ajuste_prima"]["ajuste"] == "25000.00"
    assert endoso_mov["ajuste_prima"]["prima_nueva"] == "150000.00"
    assert endoso_mov["ajuste_prima"]["moneda"] == "COP"


def test_cliente_no_ve_informacion_de_auditoria(entorno) -> None:
    # El fixture usa un CLIENTE; la vista de auditoría debe quedar en None.
    endoso_mov = next(m for m in entorno.get(RUTA).json()["movimientos"] if m["tipo"] == "ENDOSO")
    assert endoso_mov["auditoria"] is None
    assert endoso_mov["ajuste_prima"] is None


def test_sin_autenticacion_responde_401() -> None:
    app.dependency_overrides.clear()
    r = TestClient(app).get(RUTA)
    assert r.status_code == 401

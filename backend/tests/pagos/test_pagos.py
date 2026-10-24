import json
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
from app.pagos.servicio import ServicioPagos, firmar

RUTA = "/api/v1/pagos"
AHORA = datetime(2027, 1, 1, tzinfo=UTC)
SECRETO = "secreto-de-pruebas"


class PasarelaContadora(PasarelaSimulada):
    def __init__(self):
        super().__init__()
        self.llamadas = 0

    def cobrar(self, solicitud):
        self.llamadas += 1
        return super().cobrar(solicitud)


def cotizacion(cliente="CLI-001", cot_id="COT-001", vigente_hasta=None) -> Cotizacion:
    return Cotizacion(
        cotizacion_id=cot_id,
        cliente_id=cliente,
        ramo=RamoSeguro.VIAJE,
        estado=EstadoCotizacion.VIGENTE,
        prima_total=Decimal("45000.00"),
        cobertura_principal=CoberturaPrincipal(
            codigo="ASISTENCIA_VIAJE", nombre="Asistencia", suma_asegurada=Decimal("1000000")
        ),
        creada_en=AHORA,
        vigente_hasta=vigente_hasta or AHORA + timedelta(days=7),
    )


@pytest.fixture
def entorno(monkeypatch):
    monkeypatch.setenv("PAGOS_WEBHOOK_SECRET", SECRETO)
    cotizaciones = RepositorioCotizacionesEnMemoria()
    cotizaciones.guardar(cotizacion())
    pagos = RepositorioPagosEnMemoria()
    pasarela = PasarelaContadora()
    servicio = ServicioPagos(pagos, cotizaciones, pasarela, reloj=lambda: AHORA)
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    app.dependency_overrides[obtener_pasarela] = lambda: pasarela
    app.dependency_overrides[actor_actual] = lambda: ActorCotizacion(
        tipo=TipoActorCotizacion.USUARIO, actor_id="CLI-001", rol=Rol.CLIENTE
    )
    yield TestClient(app), cotizaciones, pasarela
    app.dependency_overrides.clear()


def cuerpo_tarjeta(token="tok_visa_aprobado", cot="COT-001") -> dict:
    return {"cotizacion_id": cot, "metodo": "TARJETA", "token_tarjeta": token}


def pagar(cliente, cuerpo, llave="llave-0001"):
    return cliente.post(RUTA, json=cuerpo, headers={"Idempotency-Key": llave})


def test_pago_aprobado_se_asocia_a_la_cotizacion(entorno) -> None:
    cliente, cotizaciones, _ = entorno

    r = pagar(cliente, cuerpo_tarjeta())

    assert r.status_code == 201
    assert r.json()["estado"] == "APROBADO"
    assert r.json()["monto"] == "45000.00"
    assert r.json()["cotizacion_id"] == "COT-001"
    assert "huella_solicitud" not in r.json()
    assert cotizaciones.obtener("COT-001").estado is EstadoCotizacion.ACEPTADA


def test_pago_rechazado_deja_la_cotizacion_vigente(entorno) -> None:
    cliente, cotizaciones, _ = entorno

    r = pagar(cliente, cuerpo_tarjeta("tok_rechazado_1"))

    assert r.json()["estado"] == "RECHAZADO"
    assert r.json()["motivo_rechazo"] == "FONDOS_INSUFICIENTES"
    assert cotizaciones.obtener("COT-001").estado is EstadoCotizacion.VIGENTE


def test_reintento_con_la_misma_llave_no_vuelve_a_cobrar(entorno) -> None:
    cliente, _, pasarela = entorno

    primero = pagar(cliente, cuerpo_tarjeta())
    segundo = pagar(cliente, cuerpo_tarjeta())

    assert (primero.status_code, segundo.status_code) == (201, 200)
    assert segundo.json() == primero.json()
    assert pasarela.llamadas == 1


def test_misma_llave_con_cuerpo_distinto_es_conflicto(entorno) -> None:
    cliente, _, _ = entorno
    pagar(cliente, cuerpo_tarjeta("tok_rechazado_1"))

    r = pagar(cliente, cuerpo_tarjeta("tok_otro_token"))

    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "LLAVE_IDEMPOTENCIA_REUTILIZADA"


def test_no_permite_pagar_dos_veces_la_misma_cotizacion(entorno) -> None:
    cliente, _, pasarela = entorno
    pagar(cliente, cuerpo_tarjeta(), "llave-0001")

    r = pagar(cliente, cuerpo_tarjeta(), "llave-0002")

    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "COTIZACION_YA_PAGADA"
    assert pasarela.llamadas == 1


def test_rechaza_numero_de_tarjeta_en_claro(entorno) -> None:
    cliente, _, pasarela = entorno

    r = pagar(cliente, cuerpo_tarjeta("4111 1111 1111 1111"))

    assert r.status_code == 422
    assert "4111" not in r.text
    assert pasarela.llamadas == 0


def test_exige_idempotency_key(entorno) -> None:
    cliente, _, _ = entorno

    assert cliente.post(RUTA, json=cuerpo_tarjeta()).status_code == 422


def test_cliente_no_puede_pagar_cotizacion_ajena(entorno) -> None:
    cliente, cotizaciones, _ = entorno
    cotizaciones.guardar(cotizacion(cliente="CLI-999", cot_id="COT-999"))

    r = pagar(cliente, cuerpo_tarjeta(cot="COT-999"))

    assert r.status_code == 404


def test_cotizacion_vencida_no_se_paga(entorno) -> None:
    cliente, cotizaciones, _ = entorno
    cotizaciones.guardar(
        cotizacion(cot_id="COT-OLD", vigente_hasta=AHORA + timedelta(seconds=1)).model_copy(
            update={"creada_en": AHORA - timedelta(days=8), "vigente_hasta": AHORA}
        )
    )

    r = pagar(cliente, cuerpo_tarjeta(cot="COT-OLD"))

    assert r.status_code == 409
    assert r.json()["detail"]["codigo"] == "COTIZACION_NO_VIGENTE"


def test_solo_el_cliente_puede_pagar(entorno) -> None:
    cliente, _, _ = entorno
    app.dependency_overrides[actor_actual] = lambda: ActorCotizacion(
        tipo=TipoActorCotizacion.USUARIO, actor_id="ASE-1", rol=Rol.ASESOR_VENTAS
    )

    assert pagar(cliente, cuerpo_tarjeta()).status_code == 403


def test_pasarela_caida_deja_pago_pendiente_y_reintento_no_duplica(entorno) -> None:
    cliente, _, pasarela = entorno

    r = pagar(cliente, cuerpo_tarjeta("tok_caido_1"))
    reintento = pagar(cliente, cuerpo_tarjeta("tok_caido_1"))

    assert r.status_code == 502
    assert r.json()["detail"]["codigo"] == "PASARELA_NO_DISPONIBLE"
    assert reintento.status_code == 200
    assert reintento.json()["estado"] == "PENDIENTE"
    assert pasarela.llamadas == 1


def confirmar(cliente, referencia, estado, firma=None, secreto=SECRETO):
    cuerpo = json.dumps({"referencia": referencia, "estado": estado}).encode()
    firma = firma if firma is not None else firmar(cuerpo, secreto.encode())
    return cliente.post(
        f"{RUTA}/confirmaciones",
        content=cuerpo,
        headers={"X-Firma-Pasarela": firma, "Content-Type": "application/json"},
    )


def test_pse_devuelve_redireccion_y_la_confirmacion_aprueba(entorno) -> None:
    cliente, cotizaciones, _ = entorno

    r = pagar(cliente, {"cotizacion_id": "COT-001", "metodo": "PSE", "codigo_banco": "1007"})
    assert r.json()["estado"] == "PENDIENTE"
    assert "/api/v1/pagos/pse-simulado/" in r.json()["url_redireccion"]
    assert cotizaciones.obtener("COT-001").estado is EstadoCotizacion.VIGENTE

    c = confirmar(cliente, r.json()["referencia_pasarela"], "APROBADO")

    assert c.status_code == 200 and c.json()["estado"] == "APROBADO"
    assert cotizaciones.obtener("COT-001").estado is EstadoCotizacion.ACEPTADA
    consulta = cliente.get(f"{RUTA}/{r.json()['pago_id']}")
    assert consulta.json()["estado"] == "APROBADO"


def test_confirmacion_repetida_o_contradictoria_no_cambia_el_estado_final(entorno) -> None:
    cliente, _, _ = entorno
    r = pagar(cliente, {"cotizacion_id": "COT-001", "metodo": "PSE", "codigo_banco": "1007"})
    ref = r.json()["referencia_pasarela"]
    confirmar(cliente, ref, "APROBADO")

    repetida = confirmar(cliente, ref, "APROBADO")
    contradictoria = confirmar(cliente, ref, "RECHAZADO")

    assert repetida.json()["estado"] == "APROBADO"
    assert contradictoria.json()["estado"] == "APROBADO"


def test_confirmacion_con_firma_invalida_se_rechaza(entorno) -> None:
    cliente, _, _ = entorno
    r = pagar(cliente, {"cotizacion_id": "COT-001", "metodo": "PSE", "codigo_banco": "1007"})
    ref = r.json()["referencia_pasarela"]

    assert confirmar(cliente, ref, "APROBADO", firma="0" * 64).status_code == 401
    assert confirmar(cliente, ref, "APROBADO", secreto="otro").status_code == 401


def test_confirmacion_de_pago_desconocido_y_cuerpo_mal_formado(entorno) -> None:
    cliente, _, _ = entorno

    assert confirmar(cliente, "PSP-NO-EXISTE", "APROBADO").status_code == 404
    mala = cliente.post(f"{RUTA}/confirmaciones", content=b"no-json")
    assert mala.status_code == 400


def test_consulta_de_pago_ajeno_da_404(entorno) -> None:
    cliente, _, _ = entorno

    assert cliente.get(f"{RUTA}/PAG-NADA").status_code == 404


def test_lista_solo_los_pagos_del_cliente_del_mas_reciente_al_mas_antiguo(entorno) -> None:
    cliente, cotizaciones, _ = entorno
    cotizaciones.guardar(cotizacion(cot_id="COT-002"))
    antiguo = pagar(cliente, cuerpo_tarjeta(token="tok_rechazado_1"), llave="llave-0001").json()
    pagar(cliente, cuerpo_tarjeta(cot="COT-002"), llave="llave-0002")
    repositorio = app.dependency_overrides[obtener_servicio]()._pagos
    pago = repositorio.obtener(antiguo["pago_id"])
    repositorio.guardar(pago.model_copy(update={"creado_en": AHORA - timedelta(days=30)}))

    respuesta = cliente.get(RUTA)

    assert respuesta.status_code == 200
    pagos = respuesta.json()
    assert [p["cotizacion_id"] for p in pagos] == ["COT-002", "COT-001"]
    assert all("huella_solicitud" not in p for p in pagos)


def test_lista_vacia_para_un_cliente_sin_pagos(entorno) -> None:
    cliente, _, _ = entorno
    assert cliente.get(RUTA).json() == []

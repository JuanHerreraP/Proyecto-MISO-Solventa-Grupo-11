from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.cotizaciones import obtener_servicio
from app.cotizaciones.repositorio import RepositorioCotizacionesEnMemoria
from app.cotizaciones.servicio import ServicioCotizaciones
from app.cotizaciones.servicio_personalizacion import ServicioPersonalizacionCotizacion
from app.main import app
from app.perfilamiento.enriquecimiento.memoria import RepositorioConsentimientosEnMemoria
from app.perfilamiento.repositorio import RepositorioPerfilesEnMemoria

RUTA = "/api/v1/cotizaciones"


@pytest.fixture
def cliente():
    servicio = ServicioCotizaciones(
        repositorio=RepositorioCotizacionesEnMemoria(),
        personalizador=ServicioPersonalizacionCotizacion(
            perfiles=RepositorioPerfilesEnMemoria(),
            consentimientos=RepositorioConsentimientosEnMemoria(),
        ),
        generar_id=lambda: "COT-001",
        reloj=lambda: datetime(2027, 1, 1, tzinfo=UTC),
    )
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    yield TestClient(app)
    app.dependency_overrides.clear()


def solicitud_valida() -> dict[str, object]:
    return {
        "cliente_id": "CLI-001",
        "ramo": "VIAJE",
        "datos_riesgo": {
            "destino": "Lima",
            "fecha_inicio": "2027-01-10",
            "fecha_fin": "2027-01-20",
            "numero_viajeros": 2,
            "valor_asegurado": 15_000_000,
        },
    }


def test_expone_el_catalogo_comun_para_todos_los_canales(cliente) -> None:
    respuesta = cliente.get(f"{RUTA}/ramos")

    assert respuesta.status_code == 200
    assert {ramo["ramo"] for ramo in respuesta.json()} == {
        "VIAJE",
        "PROTECCION_DISPOSITIVOS",
        "VIDA",
        "PARAMETRICO",
    }


def test_crea_consulta_y_lista_una_cotizacion(cliente) -> None:
    creada = cliente.post(RUTA, json=solicitud_valida())
    consultada = cliente.get(f"{RUTA}/COT-001")
    listado = cliente.get(RUTA, params={"cliente_id": "CLI-001"})

    assert creada.status_code == 201
    assert creada.json()["prima_total"] == "45000.00"
    assert creada.json()["cobertura_principal"]["codigo"] == "ASISTENCIA_VIAJE"
    assert consultada.json() == creada.json()
    assert listado.json() == [creada.json()]


def test_retorna_errores_estructurados_para_datos_incompletos(cliente) -> None:
    solicitud = solicitud_valida()
    solicitud["datos_riesgo"] = {"destino": "Lima"}

    respuesta = cliente.post(RUTA, json=solicitud)

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["codigo"] == "DATOS_RIESGO_INVALIDOS"
    assert {error["campo"] for error in respuesta.json()["detail"]["errores"]} == {
        "fecha_inicio",
        "fecha_fin",
        "numero_viajeros",
        "valor_asegurado",
    }


def test_consulta_inexistente_devuelve_no_encontrado(cliente) -> None:
    respuesta = cliente.get(f"{RUTA}/COT-INEXISTENTE")

    assert respuesta.status_code == 404

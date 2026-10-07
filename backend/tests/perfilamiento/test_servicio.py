import pytest

from app.perfilamiento.dominio.modelos import Dictamen, OrigenSenales
from app.perfilamiento.repositorio import RepositorioPerfilesEnMemoria
from app.perfilamiento.servicio import (
    ConsentimientoNoVigente,
    ServicioPerfilamiento,
    a_oferta_cliente,
)
from tests.perfilamiento.fabrica import senales


class RelojManual:
    def __init__(self):
        self.ahora = 0.0

    def __call__(self) -> float:
        return self.ahora


def test_el_perfil_generado_queda_disponible_para_la_cotizacion():
    servicio = ServicioPerfilamiento(RepositorioPerfilesEnMemoria())

    perfil = servicio.generar_perfil(senales())

    assert servicio.consultar_perfil("CLI-001") == perfil
    assert perfil.version_reglas == "1.0.0"
    assert perfil.origen_senales is OrigenSenales.FUENTES_EXTERNAS
    assert perfil.tiempo_calculo_ms >= 0


def test_sin_consentimiento_vigente_no_se_genera_ni_se_guarda_el_perfil():
    servicio = ServicioPerfilamiento(RepositorioPerfilesEnMemoria())

    with pytest.raises(ConsentimientoNoVigente):
        servicio.generar_perfil(senales(consentimiento_vigente=False))

    assert servicio.consultar_perfil("CLI-001") is None


def test_el_perfil_deja_de_estar_disponible_al_vencer():
    reloj = RelojManual()
    servicio = ServicioPerfilamiento(
        RepositorioPerfilesEnMemoria(vigencia_segundos=60, reloj=reloj)
    )
    servicio.generar_perfil(senales())

    reloj.ahora = 59
    assert servicio.consultar_perfil("CLI-001") is not None

    reloj.ahora = 60
    assert servicio.consultar_perfil("CLI-001") is None


def test_un_nuevo_calculo_reemplaza_el_perfil_anterior():
    servicio = ServicioPerfilamiento(RepositorioPerfilesEnMemoria())
    servicio.generar_perfil(senales())

    servicio.generar_perfil(senales(nivel_endeudamiento=0.95))

    assert servicio.consultar_perfil("CLI-001").dictamen is Dictamen.RECHAZADO


def test_la_oferta_del_cliente_no_expone_reglas_ni_puntaje():
    servicio = ServicioPerfilamiento(RepositorioPerfilesEnMemoria())
    perfil = servicio.generar_perfil(senales())

    oferta = a_oferta_cliente(perfil).model_dump()

    assert set(oferta) == {
        "cliente_id",
        "dictamen",
        "extraprima_porcentaje",
        "explicacion",
        "fecha_calculo",
    }

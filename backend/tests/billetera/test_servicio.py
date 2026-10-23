from datetime import date, timedelta

import pytest

from app.polizas.dominio.modelos import EstadoPoliza, EstadoRegistroPoliza
from app.polizas.repositorio import RepositorioEnlacesEnMemoria, RepositorioPolizasEnMemoria
from app.polizas.servicio import (
    EnlaceNoEncontrado,
    EnlaceVencido,
    PolizaNoEncontrada,
    ServicioBilletera,
    huella,
)
from tests.billetera.fabrica import AHORA, poliza


class Reloj:
    def __init__(self, ahora=AHORA):
        self.ahora = ahora

    def __call__(self):
        return self.ahora


@pytest.fixture
def repositorios():
    return RepositorioPolizasEnMemoria(), RepositorioEnlacesEnMemoria()


@pytest.fixture
def reloj():
    return Reloj()


@pytest.fixture
def servicio(repositorios, reloj):
    polizas, enlaces = repositorios
    return ServicioBilletera(
        polizas, enlaces, reloj=reloj, horas_enlace=24, generar_token=lambda: "token-fijo"
    )


def sembrar(repositorios, *polizas):
    for p in polizas:
        repositorios[0].guardar(p)


def test_sin_polizas_la_billetera_queda_vacia(servicio):
    billetera = servicio.billetera("CLI-001")

    assert billetera.polizas == []
    assert billetera.total_vigentes == 0
    assert billetera.total_inactivas == 0


def test_lista_solo_las_polizas_del_titular(servicio, repositorios):
    sembrar(
        repositorios,
        poliza(),
        poliza(poliza_id="POL-2", numero_poliza="SOL-VI-000002", cliente_id="CLI-002"),
    )

    billetera = servicio.billetera("CLI-001")

    assert [p.poliza_id for p in billetera.polizas] == ["POL-1"]


def test_muestra_numero_ramo_estado_y_fechas(servicio, repositorios):
    sembrar(repositorios, poliza())

    [vista] = servicio.billetera("CLI-001").polizas

    assert vista.numero_poliza == "SOL-VI-000001"
    assert vista.nombre_ramo == "Seguro de viaje"
    assert vista.estado is EstadoPoliza.VIGENTE
    assert vista.activa is True
    assert vista.fecha_inicio == date(2026, 10, 1)
    assert vista.fecha_fin == date(2026, 12, 31)


def test_vigentes_primero_y_luego_inactivas(servicio, repositorios):
    sembrar(
        repositorios,
        poliza(
            poliza_id="VENCIDA",
            numero_poliza="SOL-VI-000010",
            fecha_inicio=date(2025, 1, 1),
            fecha_fin=date(2025, 6, 30),
        ),
        poliza(poliza_id="LARGA", numero_poliza="SOL-VI-000011", fecha_fin=date(2027, 9, 30)),
        poliza(
            poliza_id="CANCELADA",
            numero_poliza="SOL-VI-000012",
            estado=EstadoRegistroPoliza.CANCELADA,
        ),
        poliza(poliza_id="CORTA", numero_poliza="SOL-VI-000013", fecha_fin=date(2026, 11, 15)),
    )

    billetera = servicio.billetera("CLI-001")

    assert [p.poliza_id for p in billetera.polizas] == ["CORTA", "LARGA", "CANCELADA", "VENCIDA"]
    assert [p.activa for p in billetera.polizas] == [True, True, False, False]
    assert billetera.total_vigentes == 2
    assert billetera.total_inactivas == 2


def test_una_poliza_pasa_a_inactiva_al_dia_siguiente_de_su_fin(servicio, repositorios, reloj):
    sembrar(repositorios, poliza(fecha_fin=date(2026, 10, 21)))
    assert servicio.billetera("CLI-001").polizas[0].activa is True

    reloj.ahora = AHORA + timedelta(days=1)

    [vista] = servicio.billetera("CLI-001").polizas
    assert vista.activa is False
    assert vista.estado is EstadoPoliza.VENCIDA


def test_el_certificado_incluye_qr_y_documento_enmascarado(servicio, repositorios):
    sembrar(repositorios, poliza())

    certificado = servicio.certificado("CLI-001", "POL-1")

    assert certificado.contenido_qr == "SOLVENTA|SOL-VI-000001|a1b2c3d4e5f60718"
    assert certificado.documento_titular == "CC ****5678"
    assert certificado.titular == "Ana Pérez"


def test_el_certificado_de_otro_titular_no_existe_para_el_cliente(servicio, repositorios):
    sembrar(repositorios, poliza(cliente_id="CLI-002"))

    with pytest.raises(PolizaNoEncontrada):
        servicio.certificado("CLI-001", "POL-1")


def test_compartir_genera_un_enlace_temporal_y_guarda_solo_la_huella(servicio, repositorios):
    sembrar(repositorios, poliza())

    enlace = servicio.compartir("CLI-001", "POL-1", "https://api.solventa.co/")

    assert enlace.url == "https://api.solventa.co/api/v1/certificados-compartidos/token-fijo"
    assert enlace.expira_en == AHORA + timedelta(hours=24)
    guardado = repositorios[1].obtener(huella("token-fijo"))
    assert guardado is not None
    assert "token-fijo" not in guardado.model_dump_json()


def test_no_se_puede_compartir_la_poliza_de_otro_titular(servicio, repositorios):
    sembrar(repositorios, poliza(cliente_id="CLI-002"))

    with pytest.raises(PolizaNoEncontrada):
        servicio.compartir("CLI-001", "POL-1", "https://api.solventa.co")


def test_el_enlace_vigente_muestra_el_certificado_sin_la_prima(servicio, repositorios):
    sembrar(repositorios, poliza())
    servicio.compartir("CLI-001", "POL-1", "https://api.solventa.co")

    compartido = servicio.certificado_compartido("token-fijo")

    assert compartido.numero_poliza == "SOL-VI-000001"
    assert "prima_total" not in compartido.model_dump()
    assert "poliza_id" not in compartido.model_dump()


def test_el_enlace_vencido_ya_no_muestra_el_certificado(servicio, repositorios, reloj):
    sembrar(repositorios, poliza())
    servicio.compartir("CLI-001", "POL-1", "https://api.solventa.co")

    reloj.ahora = AHORA + timedelta(hours=24)

    with pytest.raises(EnlaceVencido):
        servicio.certificado_compartido("token-fijo")


def test_un_token_desconocido_no_muestra_nada(servicio):
    with pytest.raises(EnlaceNoEncontrado):
        servicio.certificado_compartido("otro-token")


def test_si_la_poliza_cambia_de_titular_el_enlace_deja_de_servir(servicio, repositorios):
    sembrar(repositorios, poliza())
    servicio.compartir("CLI-001", "POL-1", "https://api.solventa.co")
    repositorios[0].guardar(poliza(cliente_id="CLI-009"))

    with pytest.raises(EnlaceNoEncontrado):
        servicio.certificado_compartido("token-fijo")


def test_los_tokens_reales_son_distintos_y_largos(repositorios, reloj):
    servicio = ServicioBilletera(*repositorios, reloj=reloj, horas_enlace=1)
    sembrar(repositorios, poliza())

    primero = servicio.compartir("CLI-001", "POL-1", "https://x").url.rsplit("/", 1)[1]
    segundo = servicio.compartir("CLI-001", "POL-1", "https://x").url.rsplit("/", 1)[1]

    assert primero != segundo
    assert len(primero) >= 43


@pytest.mark.parametrize(
    ("valor", "esperado"), [(None, 24), ("48", 48), ("0", 24), ("999", 24), ("abc", 24)]
)
def test_la_vigencia_del_enlace_se_configura_con_limites(monkeypatch, valor, esperado):
    from app.polizas.servicio import horas_vigencia_enlace

    if valor is None:
        monkeypatch.delenv("BILLETERA_ENLACE_HORAS", raising=False)
    else:
        monkeypatch.setenv("BILLETERA_ENLACE_HORAS", valor)

    assert horas_vigencia_enlace() == esperado

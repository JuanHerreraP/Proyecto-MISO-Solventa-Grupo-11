"""Job de vencimientos: avisos a 15 y 3 días de que una póliza vence."""

from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.notificaciones.canal import EnviadorPushSimulado
from app.notificaciones.modelos import TipoNotificacion
from app.notificaciones.vencimientos import ServicioVencimientos
from app.polizas.dominio.modelos import EstadoRegistroPoliza, RamoPoliza
from app.polizas.modelos_db import PolizaDB
from app.polizas.repositorio import RepositorioPolizasEnMemoria, RepositorioPolizasPostgres
from tests.billetera.fabrica import poliza
from tests.notificaciones.fabrica import (
    AHORA,
    CLIENTE,
    HOY,
    OTRO,
    crear_servicio,
    dispositivo,
    preferencia,
)


def vida(numero: int, dias: int, cliente_id: str = CLIENTE, **cambios):
    """Una póliza de vida que vence dentro de `dias` días (renovable)."""
    datos = {
        "poliza_id": f"POL-{numero}",
        "numero_poliza": f"SOL-VD-{numero:06d}",
        "cliente_id": cliente_id,
        "ramo": RamoPoliza.VIDA,
        "fecha_inicio": HOY - timedelta(days=300),
        "fecha_fin": HOY + timedelta(days=dias),
    }
    datos.update(cambios)
    return poliza(**datos)


@pytest.fixture(params=["memoria", "sqlite"])
def entorno(request):
    """El job con las pólizas en memoria o sobre la base de datos."""
    if request.param == "memoria":
        polizas, cerrar = RepositorioPolizasEnMemoria(), lambda: None
    else:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        PolizaDB.__table__.create(engine)
        sesion = sessionmaker(bind=engine)()
        polizas = RepositorioPolizasPostgres(sesion)

        def cerrar():
            sesion.close()
            engine.dispose()

    enviador = EnviadorPushSimulado()
    notificaciones, repos, reloj = crear_servicio(enviador=enviador)
    repos.dispositivos.guardar(dispositivo("token-1", cliente_id=CLIENTE))
    repos.dispositivos.guardar(dispositivo("token-2", cliente_id=OTRO, numero=2))
    job = ServicioVencimientos(polizas, notificaciones, reloj=reloj)
    yield job, polizas, repos, enviador, reloj
    cerrar()


def resumen_de(resumen, dias: int):
    return next(a for a in resumen.avisos if a.dias == dias)


# --- Los avisos de 15 y 3 días -------------------------------------------------------------


def test_avisa_a_quince_y_a_tres_dias_del_vencimiento(entorno) -> None:
    job, polizas, repos, enviador, _ = entorno
    polizas.guardar(vida(1, dias=15))
    polizas.guardar(vida(2, dias=3))

    resumen = job.ejecutar()

    assert resumen.fecha == HOY
    assert (resumen_de(resumen, 15).candidatas, resumen_de(resumen, 15).notificadas) == (1, 1)
    assert (resumen_de(resumen, 3).candidatas, resumen_de(resumen, 3).notificadas) == (1, 1)
    por_poliza = {n.datos["poliza_id"]: n for n in repos.notificaciones.listar(CLIENTE)}
    assert por_poliza["POL-1"].cuerpo == (
        "Tu póliza SOL-VD-000001 vence en 15 días. Renuévala para mantener tu cobertura."
    )
    assert por_poliza["POL-2"].datos["dias"] == "3"
    assert all(n.tipo is TipoNotificacion.VENCIMIENTO_POLIZA for n in por_poliza.values())


def test_el_push_lleva_a_la_renovacion_de_la_poliza(entorno) -> None:
    job, polizas, _, enviador, _ = entorno
    polizas.guardar(vida(1, dias=15))

    job.ejecutar()

    (push,) = enviador.enviados
    assert push.tokens == ("token-1",)
    assert push.datos["tipo"] == "VENCIMIENTO_POLIZA"
    assert push.datos["poliza_id"] == "POL-1"  # abre la renovación de esa póliza
    assert push.datos["fecha_fin"] == (HOY + timedelta(days=15)).isoformat()


@pytest.mark.parametrize("dias", [0, 1, 2, 4, 10, 14, 16, 30])
def test_solo_avisa_cuando_faltan_exactamente_quince_o_tres_dias(entorno, dias) -> None:
    job, polizas, repos, _, _ = entorno
    polizas.guardar(vida(1, dias=dias))

    resumen = job.ejecutar()

    assert repos.notificaciones.listar(CLIENTE) == []
    assert sum(a.candidatas for a in resumen.avisos) == 0


def test_cada_cliente_recibe_el_aviso_de_su_poliza(entorno) -> None:
    job, polizas, repos, enviador, _ = entorno
    polizas.guardar(vida(1, dias=15, cliente_id=CLIENTE))
    polizas.guardar(vida(2, dias=15, cliente_id=OTRO))

    job.ejecutar()

    assert [n.datos["poliza_id"] for n in repos.notificaciones.listar(CLIENTE)] == ["POL-1"]
    assert [n.datos["poliza_id"] for n in repos.notificaciones.listar(OTRO)] == ["POL-2"]
    assert sorted(p.tokens[0] for p in enviador.enviados) == ["token-1", "token-2"]


# --- Qué pólizas se avisan -----------------------------------------------------------------


@pytest.mark.parametrize(
    "ramo", [RamoPoliza.VIDA, RamoPoliza.PROTECCION_DISPOSITIVOS, RamoPoliza.PARAMETRICO]
)
def test_avisa_las_pólizas_de_los_ramos_renovables(entorno, ramo) -> None:
    job, polizas, repos, _, _ = entorno
    polizas.guardar(vida(1, dias=15, ramo=ramo))

    job.ejecutar()

    assert len(repos.notificaciones.listar(CLIENTE)) == 1


def test_el_seguro_de_viaje_no_se_renueva_asi_que_no_se_avisa(entorno) -> None:
    job, polizas, repos, _, _ = entorno
    polizas.guardar(vida(1, dias=15, ramo=RamoPoliza.VIAJE))

    resumen = job.ejecutar()

    assert repos.notificaciones.listar(CLIENTE) == []
    assert resumen_de(resumen, 15).candidatas == 0


def test_una_poliza_cancelada_no_se_avisa(entorno) -> None:
    job, polizas, repos, _, _ = entorno
    polizas.guardar(vida(1, dias=15, estado=EstadoRegistroPoliza.CANCELADA))

    job.ejecutar()

    assert repos.notificaciones.listar(CLIENTE) == []


def test_una_poliza_renovada_cambio_su_fecha_de_fin_y_ya_no_se_avisa(entorno) -> None:
    job, polizas, repos, _, _ = entorno
    # Se renovó antes de tiempo: su vigencia ahora termina dentro de un año.
    polizas.guardar(vida(1, dias=15, fecha_fin=HOY + timedelta(days=380)))

    job.ejecutar()

    assert repos.notificaciones.listar(CLIENTE) == []


# --- Idempotencia, fecha y errores ---------------------------------------------------------


def test_ejecutar_el_job_dos_veces_el_mismo_dia_no_duplica_los_avisos(entorno) -> None:
    job, polizas, repos, enviador, _ = entorno
    polizas.guardar(vida(1, dias=15))
    job.ejecutar()

    segunda = job.ejecutar()

    aviso = resumen_de(segunda, 15)
    assert (aviso.candidatas, aviso.notificadas, aviso.repetidas) == (1, 0, 1)
    assert len(repos.notificaciones.listar(CLIENTE)) == 1 and len(enviador.enviados) == 1


def test_al_dia_siguiente_avisa_la_poliza_que_ahora_vence_en_tres(entorno) -> None:
    job, polizas, repos, _, reloj = entorno
    polizas.guardar(vida(1, dias=15))
    job.ejecutar()
    reloj.avanzar(days=12)

    job.ejecutar()

    assert sorted(n.datos["dias"] for n in repos.notificaciones.listar(CLIENTE)) == ["15", "3"]


def test_se_puede_correr_el_job_para_una_fecha_pasada(entorno) -> None:
    job, polizas, repos, _, _ = entorno
    polizas.guardar(vida(1, dias=10))  # vence en 10 días: hoy no toca

    resumen = job.ejecutar(HOY - timedelta(days=5))  # pero hace 5 días faltaban 15

    assert resumen.fecha == HOY - timedelta(days=5)
    assert len(repos.notificaciones.listar(CLIENTE)) == 1


def test_el_dia_se_cuenta_en_hora_de_bogota(entorno) -> None:
    job, polizas, repos, _, reloj = entorno
    polizas.guardar(vida(1, dias=15))
    # 22:00 UTC son las 17:00 en Bogotá: sigue siendo el mismo día.
    reloj.ahora = AHORA.replace(hour=22)
    assert job.ejecutar().fecha == HOY
    # 03:00 UTC aún es el día anterior en Bogotá.
    reloj.ahora = AHORA.replace(hour=3)
    assert job.ejecutar().fecha == HOY - timedelta(days=1)


def test_una_poliza_que_falla_no_frena_el_resto_del_lote(entorno, caplog) -> None:
    job, polizas, repos, _, _ = entorno
    polizas.guardar(vida(1, dias=15))
    polizas.guardar(vida(2, dias=15))
    original = job._notificaciones.notificar_evento

    def con_falla(cliente_id, evento):
        if evento.datos["poliza_id"] == "POL-1":
            raise RuntimeError("falla de una póliza")
        return original(cliente_id, evento)

    job._notificaciones.notificar_evento = con_falla

    resumen = job.ejecutar()

    aviso = resumen_de(resumen, 15)
    assert (aviso.candidatas, aviso.notificadas, aviso.errores) == (2, 1, 1)
    assert [n.datos["poliza_id"] for n in repos.notificaciones.listar(CLIENTE)] == ["POL-2"]
    assert "No se pudo avisar el vencimiento de la póliza POL-1" in caplog.text


# --- Push y agrupación ---------------------------------------------------------------------


def test_con_el_push_deshabilitado_el_aviso_igual_queda_en_la_bandeja(entorno) -> None:
    job, polizas, repos, enviador, _ = entorno
    repos.preferencias.guardar(preferencia(False))
    polizas.guardar(vida(1, dias=15))

    job.ejecutar()

    assert len(repos.notificaciones.listar(CLIENTE)) == 1 and enviador.enviados == []


def test_varias_polizas_del_mismo_cliente_el_mismo_dia_se_agrupan(entorno) -> None:
    job, polizas, repos, enviador, _ = entorno
    polizas.guardar(vida(1, dias=15))
    polizas.guardar(vida(2, dias=15))
    polizas.guardar(vida(3, dias=3))

    job.ejecutar()

    # El primero es un aviso normal; los demás, un resumen que reemplaza al anterior.
    assert [p.agrupado for p in enviador.enviados[:2]] == [False, True]
    assert enviador.enviados[-1].cuerpo == "Tienes 3 pólizas próximas a vencer."
    assert len({p.etiqueta for p in enviador.enviados}) == 1
    assert len(repos.notificaciones.listar(CLIENTE)) == 3


def test_el_repositorio_solo_devuelve_las_vigentes_que_vencen_ese_dia(entorno) -> None:
    _, polizas, _, _, _ = entorno
    polizas.guardar(vida(1, dias=15))
    polizas.guardar(vida(2, dias=15, estado=EstadoRegistroPoliza.CANCELADA))
    polizas.guardar(vida(3, dias=16))

    encontradas = polizas.listar_que_vencen_el(HOY + timedelta(days=15))

    assert [p.poliza_id for p in encontradas] == ["POL-1"]
    assert polizas.listar_que_vencen_el(HOY + timedelta(days=99)) == []

"""Patrón Cache-Aside: la caché se consulta primero y Redis puede fallar sin romper nada."""

from datetime import timedelta

import fakeredis
import pytest

from app.infraestructura.redis_cliente import AlmacenRedis
from app.perfilamiento.dominio.modelos import OrigenSenales
from app.perfilamiento.enriquecimiento.cache_redis import CacheSenalesRedis, UltimosResultadosRedis
from app.perfilamiento.enriquecimiento.modelos import OrigenDato, TipoFuente
from app.perfilamiento.repositorio import RepositorioPerfilesRedis
from tests.enriquecimiento.dobles import ENTORNO, FINANZAS, Escenario
from tests.perfilamiento.fabrica import senales as senales_perfil


class RedisCaido:
    def get(self, *_, **__):
        raise ConnectionError("sin conexión")

    set = delete = get


@pytest.fixture
def redis():
    return fakeredis.FakeRedis(decode_responses=True)


def escenario_con_redis(redis, frescura=timedelta(minutes=60)):
    escenario = Escenario(
        cache=CacheSenalesRedis(AlmacenRedis(redis, "senales")),
        ultimos=UltimosResultadosRedis(AlmacenRedis(redis, "enriquecimiento")),
        frescura=frescura,
    )
    return escenario.con_consentimiento()


def test_con_dato_fresco_no_se_consulta_al_proveedor(redis):
    escenario = escenario_con_redis(redis)
    escenario.enriquecer()
    resultado = escenario.enriquecer()

    assert escenario.open_finance.consultas == 1
    assert escenario.open_data.consultas == 1
    assert {t.origen for t in resultado.fuentes} == {OrigenDato.CACHE}
    assert resultado.senales.origen is OrigenSenales.CACHE
    assert resultado.senales.open_finance == FINANZAS
    assert resultado.senales.open_data == ENTORNO


def test_vencida_la_frescura_se_consulta_de_nuevo_al_proveedor(redis):
    escenario = escenario_con_redis(redis)
    escenario.enriquecer()
    escenario.reloj.avanzar(minutes=61)

    resultado = escenario.enriquecer()

    assert escenario.open_finance.consultas == 2
    assert {t.origen for t in resultado.fuentes} == {OrigenDato.FUENTE_EXTERNA}


def test_sin_frescura_el_proveedor_va_primero_y_la_cache_respalda(redis):
    escenario = escenario_con_redis(redis, frescura=timedelta(0))
    escenario.enriquecer()
    escenario.enriquecer()
    assert escenario.open_finance.consultas == 2

    escenario.open_finance.falla = "respuesta HTTP 503"
    resultado = escenario.enriquecer()

    assert resultado.senales.origen is OrigenSenales.CACHE


def test_otra_replica_ve_el_dato_y_el_ultimo_resultado(redis):
    primera = escenario_con_redis(redis)
    primera.enriquecer()

    segunda = escenario_con_redis(redis)
    resultado = segunda.enriquecer()

    assert segunda.open_finance.consultas == 0
    assert resultado.senales.open_finance == FINANZAS
    assert segunda.servicio.ultimo("CLI-001") is not None


def test_redis_caido_no_rompe_el_enriquecimiento():
    caido = RedisCaido()
    escenario = escenario_con_redis(caido)

    resultado = escenario.enriquecer()

    assert resultado.senales.open_finance == FINANZAS
    assert {t.origen for t in resultado.fuentes} == {OrigenDato.FUENTE_EXTERNA}
    assert escenario.servicio.ultimo("CLI-001") is None


def test_un_dato_ilegible_en_redis_se_ignora(redis):
    cache = CacheSenalesRedis(AlmacenRedis(redis, "senales"))
    redis.set("senales:OPEN_FINANCE:CLI-001", "no es json")

    assert cache.obtener("CLI-001", TipoFuente.OPEN_FINANCE) is None


def test_el_dato_vence_en_redis(redis):
    almacen = AlmacenRedis(redis, "senales")
    cache = CacheSenalesRedis(almacen, vigencia=timedelta(hours=2))
    escenario = Escenario(cache=cache).con_consentimiento()
    escenario.enriquecer()

    assert 0 < redis.ttl("senales:OPEN_FINANCE:CLI-001") <= 7200


def test_perfiles_en_redis_se_comparten_y_toleran_la_caida(redis):
    from app.perfilamiento.servicio import ServicioPerfilamiento

    repo = RepositorioPerfilesRedis(AlmacenRedis(redis, "perfil"))
    perfil = ServicioPerfilamiento(repo).generar_perfil(senales_perfil())

    otra = RepositorioPerfilesRedis(AlmacenRedis(redis, "perfil"))
    assert otra.obtener(perfil.cliente_id) == perfil
    assert otra.obtener("NO-EXISTE") is None

    caido = RepositorioPerfilesRedis(AlmacenRedis(RedisCaido(), "perfil"))
    caido.guardar(perfil)
    assert caido.obtener(perfil.cliente_id) is None

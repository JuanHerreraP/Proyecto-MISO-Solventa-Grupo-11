"""Pruebas del almacén de eventos del proveedor de telemetría (HU20).

El almacén compartido (Redis) da una vista consistente entre réplicas: un evento generado por una
réplica puede consultarse o reenviarse desde cualquier otra. Se usa fakeredis para no depender de
un Redis real.
"""

import fakeredis

from mocks.telemetry.almacen import AlmacenEnMemoria, AlmacenRedis
from mocks.telemetry.modelos import EventoTelemetria, RespuestaSimulacion


def _evento(evento_id="FLIGHT-AV1-20261026-abc") -> EventoTelemetria:
    return EventoTelemetria(
        evento_id=evento_id,
        tipo_evento="RETRASO_VUELO",
        valor_observado=215.0,
        unidad="MINUTOS",
        fecha_evento="2026-10-26T20:00:00Z",
        fuente="MOCK_FLIGHT_PROVIDER",
    )


def _resultado(evento_id="FLIGHT-AV1-20261026-abc") -> RespuestaSimulacion:
    return RespuestaSimulacion(
        evento_id=evento_id,
        tipo_evento="RETRASO_VUELO",
        enviado=True,
        solventa_status=200,
    )


def test_memoria_guarda_consulta_y_lista() -> None:
    almacen = AlmacenEnMemoria()
    almacen.guardar(_evento(), _resultado())
    assert almacen.obtener_evento("FLIGHT-AV1-20261026-abc") is not None
    assert [r.evento_id for r in almacen.listar_resultados()] == ["FLIGHT-AV1-20261026-abc"]
    assert almacen.obtener_evento("NO-EXISTE") is None


def test_redis_comparte_entre_instancias() -> None:
    # Dos instancias del almacén sobre el MISMO Redis simulan dos réplicas del backend.
    servidor = fakeredis.FakeServer()
    cliente_a = fakeredis.FakeStrictRedis(server=servidor, decode_responses=True)
    cliente_b = fakeredis.FakeStrictRedis(server=servidor, decode_responses=True)
    replica_a = AlmacenRedis(cliente_a)
    replica_b = AlmacenRedis(cliente_b)

    replica_a.guardar(_evento(), _resultado())

    # La réplica B ve el evento que generó la réplica A (consulta y reenvío consistentes).
    visto = replica_b.obtener_evento("FLIGHT-AV1-20261026-abc")
    assert visto is not None
    assert visto.evento_id == "FLIGHT-AV1-20261026-abc"
    assert [r.evento_id for r in replica_b.listar_resultados()] == ["FLIGHT-AV1-20261026-abc"]


def test_redis_tolera_fallo_en_lectura() -> None:
    class ClienteRoto:
        def get(self, *a, **k):
            raise RuntimeError("Redis caído")

        def smembers(self, *a, **k):
            raise RuntimeError("Redis caído")

    almacen = AlmacenRedis(ClienteRoto())
    # Un fallo de Redis nunca rompe el proveedor: devuelve "no hay".
    assert almacen.obtener_evento("x") is None
    assert almacen.listar_resultados() == []

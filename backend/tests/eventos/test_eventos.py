"""Eventos de negocio: modelo, publicador SNS y registro de eventos procesados."""

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.eventos.modelos import EventoNegocio, TipoEvento
from app.eventos.procesados import (
    EventoProcesadoDB,
    RepositorioEventosProcesadosEnMemoria,
    RepositorioEventosProcesadosPostgres,
)
from app.eventos.publicador import (
    PublicacionFallida,
    PublicadorEnMemoria,
    PublicadorSNS,
    publicador_negocio,
)

AHORA = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)


def evento(**cambios) -> EventoNegocio:
    datos = {
        "evento_id": "PAGO_PARAMETRICO:SIN-1",
        "tipo": TipoEvento.SINIESTRO_PARAMETRICO_APROBADO,
        "ocurrido_en": AHORA,
        "datos": {"siniestro_id": "SIN-1", "monto_aprobado": "500000.00"},
    }
    datos.update(cambios)
    return EventoNegocio(**datos)


# --- Modelo ----------------------------------------------------------------------------------


def test_el_evento_viaja_como_json_y_se_lee_de_vuelta() -> None:
    original = evento()

    leido = EventoNegocio.desde_cuerpo(original.como_json())

    assert leido == original


def test_se_desenvuelve_el_sobre_de_sns_si_la_entrega_no_es_cruda() -> None:
    sobre = json.dumps({"Type": "Notification", "Message": evento().como_json()})

    assert EventoNegocio.desde_cuerpo(sobre) == evento()


def test_un_cuerpo_con_un_tipo_desconocido_o_campos_extra_no_se_acepta() -> None:
    desconocido = json.loads(evento().como_json()) | {"tipo": "OTRA_COSA"}
    extra = json.loads(evento().como_json()) | {"sorpresa": "x"}

    with pytest.raises(ValidationError):
        EventoNegocio.desde_cuerpo(json.dumps(desconocido))
    with pytest.raises(ValidationError):
        EventoNegocio.desde_cuerpo(json.dumps(extra))


def test_un_cuerpo_que_no_es_json_falla() -> None:
    with pytest.raises(ValueError):
        EventoNegocio.desde_cuerpo("{no es json")


# --- Publicador SNS --------------------------------------------------------------------------


class _ClienteSns:
    def __init__(self, respuesta=None, falla: Exception | None = None):
        self.llamadas: list[dict] = []
        self._respuesta = {"MessageId": "msg-1"} if respuesta is None else respuesta
        self._falla = falla

    def publish(self, **kwargs):
        self.llamadas.append(kwargs)
        if self._falla:
            raise self._falla
        return self._respuesta


def test_publica_el_evento_con_su_tipo_como_atributo_y_devuelve_el_message_id() -> None:
    cliente = _ClienteSns()

    message_id = PublicadorSNS("arn:aws:sns:us-east-1:1:eventos", cliente).publicar(evento())

    assert message_id == "msg-1"
    llamada = cliente.llamadas[0]
    assert llamada["TopicArn"] == "arn:aws:sns:us-east-1:1:eventos"
    assert EventoNegocio.desde_cuerpo(llamada["Message"]) == evento()
    assert llamada["MessageAttributes"]["tipo"]["StringValue"] == "SINIESTRO_PARAMETRICO_APROBADO"


def test_un_fallo_de_sns_se_traduce_en_publicacion_fallida() -> None:
    publicador = PublicadorSNS("arn:x", _ClienteSns(falla=RuntimeError("sin red")))

    with pytest.raises(PublicacionFallida):
        publicador.publicar(evento())


def test_sin_message_id_el_evento_no_esta_confirmado() -> None:
    publicador = PublicadorSNS("arn:x", _ClienteSns(respuesta={}))

    with pytest.raises(PublicacionFallida, match="MessageId"):
        publicador.publicar(evento())


def test_sin_arn_no_se_puede_crear_el_publicador(monkeypatch) -> None:
    monkeypatch.delenv("SNS_TOPIC_ARN", raising=False)

    with pytest.raises(ValueError, match="SNS_TOPIC_ARN"):
        PublicadorSNS()


def test_el_publicador_en_memoria_guarda_los_eventos() -> None:
    publicador = PublicadorEnMemoria()

    assert publicador.publicar(evento()) == "mem-1"
    assert publicador.publicar(evento(evento_id="OTRO")) == "mem-2"
    assert [e.evento_id for e in publicador.eventos] == ["PAGO_PARAMETRICO:SIN-1", "OTRO"]


def test_sin_topico_configurado_no_hay_publicador_y_con_el_se_crea_uno(monkeypatch) -> None:
    publicador_negocio.cache_clear()
    monkeypatch.delenv("SNS_TOPIC_ARN", raising=False)
    assert publicador_negocio() is None

    publicador_negocio.cache_clear()
    monkeypatch.setenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:1:eventos")
    assert isinstance(publicador_negocio(), PublicadorSNS)
    # Es uno por proceso: no se crea un cliente de AWS en cada solicitud.
    assert publicador_negocio() is publicador_negocio()
    publicador_negocio.cache_clear()


# --- Eventos procesados ----------------------------------------------------------------------


def test_en_memoria_un_evento_se_marca_una_sola_vez_por_consumidor() -> None:
    repo = RepositorioEventosProcesadosEnMemoria()

    assert not repo.ya_procesado("E-1", "pagos")
    assert repo.marcar("E-1", "pagos", AHORA) is True
    assert repo.ya_procesado("E-1", "pagos")
    assert repo.marcar("E-1", "pagos", AHORA) is False
    # Otro consumidor sí puede procesar el mismo evento.
    assert repo.marcar("E-1", "auditoria", AHORA) is True


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    EventoProcesadoDB.__table__.create(engine)
    with sessionmaker(bind=engine)() as sesion:
        yield sesion
    engine.dispose()


def test_en_la_base_el_segundo_registro_del_mismo_evento_es_un_duplicado(db) -> None:
    repo = RepositorioEventosProcesadosPostgres(db)

    assert repo.marcar("E-1", "pagos", AHORA) is True
    assert repo.ya_procesado("E-1", "pagos")
    assert repo.marcar("E-1", "pagos", AHORA) is False
    # Tras el conflicto la sesión sigue usable.
    assert repo.marcar("E-2", "pagos", AHORA) is True
    assert not repo.ya_procesado("E-3", "pagos")

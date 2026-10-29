"""Evaluación paramétrica de eventos de telemetría (HU20).

Solventa recibe una observación externa (retraso de vuelo, evento climático) y decide. El
proveedor solo informa; aquí está la lógica de negocio: buscar pólizas paramétricas vigentes
que apliquen al evento, comparar el valor observado contra el umbral contratado y, si lo
alcanza, crear un siniestro AUTOMATICO. La idempotencia se garantiza por `evento_id`.

La condición contratada se guardó al sembrar la póliza en `cobertura_principal.descripcion`
como pares `clave=valor` (mismos códigos del catálogo de cotización), por ejemplo:

    tipo_evento=RETRASO_VUELO; numero_vuelo=AV123; ubicacion=BOG; umbral_disparo=180; unidad=MINUTOS
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum

from pydantic import BaseModel

from app.polizas.dominio.modelos import EstadoPoliza, Poliza, hoy_en_colombia
from app.polizas.repositorio import RepositorioPolizas
from app.siniestros.modelos import (
    EstadoSiniestro,
    OrigenSiniestro,
    Siniestro,
)
from app.siniestros.repositorio import RepositorioSiniestros


class ResultadoTelemetria(str, Enum):
    """Qué hizo Solventa con el evento."""

    SINIESTRO_CREADO = "SINIESTRO_CREADO"
    SIN_COBERTURA = "SIN_COBERTURA"  # no hay póliza vigente que aplique o no se alcanzó el umbral
    DUPLICADO = "DUPLICADO"  # el evento ya se había procesado (idempotencia)


class RespuestaTelemetria(BaseModel):
    """Resultado de procesar un evento de telemetría."""

    evento_id: str
    resultado: ResultadoTelemetria
    siniestro_id: str | None = None
    poliza_id: str | None = None


def parsear_condicion(descripcion: str | None) -> dict[str, str]:
    """Convierte 'a=1; b=2' en {'a': '1', 'b': '2'}. Tolera vacíos y espacios."""
    condicion: dict[str, str] = {}
    if not descripcion:
        return condicion
    for parte in descripcion.split(";"):
        if "=" not in parte:
            continue
        clave, _, valor = parte.partition("=")
        clave = clave.strip().lower()
        valor = valor.strip()
        if clave:
            condicion[clave] = valor
    return condicion


def _a_decimal(valor: object) -> Decimal | None:
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None


class EventoParametrico(BaseModel):
    """Vista normalizada del evento externo que necesita la evaluación."""

    evento_id: str
    tipo_evento: str
    valor_observado: Decimal
    fecha_evento: datetime
    numero_vuelo: str | None = None
    ubicacion: str | None = None


class ServicioTelemetria:
    """Caso de uso: procesar un evento de telemetría y decidir si crea un siniestro."""

    def __init__(
        self,
        siniestros: RepositorioSiniestros,
        polizas: RepositorioPolizas,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = lambda: f"SIN-{uuid.uuid4()}",
    ):
        self._siniestros = siniestros
        self._polizas = polizas
        self._reloj = reloj
        self._generar_id = generar_id

    def procesar(self, evento: EventoParametrico) -> RespuestaTelemetria:
        # 1) Idempotencia: un evento ya visto no vuelve a generar siniestro.
        existente = self._siniestros.obtener_por_evento(evento.evento_id)
        if existente is not None:
            return RespuestaTelemetria(
                evento_id=evento.evento_id,
                resultado=ResultadoTelemetria.DUPLICADO,
                siniestro_id=existente.siniestro_id,
                poliza_id=existente.poliza_id,
            )

        ahora = self._reloj()
        hoy = hoy_en_colombia(ahora)

        # 2) Buscar la póliza paramétrica vigente que aplique y cuyo umbral se alcance.
        for poliza in self._polizas.listar_parametricas():
            if poliza.estado_en(hoy) is not EstadoPoliza.VIGENTE:
                continue
            condicion = parsear_condicion(poliza.cobertura_principal.descripcion)
            if not self._aplica(condicion, evento):
                continue
            umbral = _a_decimal(condicion.get("umbral_disparo"))
            if umbral is None or evento.valor_observado < umbral:
                continue

            siniestro = self._crear_siniestro(poliza, evento, ahora)
            self._siniestros.guardar(siniestro)
            return RespuestaTelemetria(
                evento_id=evento.evento_id,
                resultado=ResultadoTelemetria.SINIESTRO_CREADO,
                siniestro_id=siniestro.siniestro_id,
                poliza_id=poliza.poliza_id,
            )

        # 3) Ninguna póliza vigente aplica o no se alcanzó el umbral: no se reclama.
        return RespuestaTelemetria(
            evento_id=evento.evento_id,
            resultado=ResultadoTelemetria.SIN_COBERTURA,
        )

    @staticmethod
    def _aplica(condicion: dict[str, str], evento: EventoParametrico) -> bool:
        """La póliza aplica si el tipo de evento y el discriminante coinciden."""
        if condicion.get("tipo_evento", "").upper() != evento.tipo_evento.upper():
            return False
        if evento.tipo_evento.upper() == "RETRASO_VUELO":
            esperado = condicion.get("numero_vuelo", "").upper()
            return bool(esperado) and esperado == (evento.numero_vuelo or "").upper()
        if evento.tipo_evento.upper() == "EVENTO_CLIMATICO":
            esperado = condicion.get("ubicacion", "").upper()
            return bool(esperado) and esperado == (evento.ubicacion or "").upper()
        return False

    def _crear_siniestro(
        self, poliza: Poliza, evento: EventoParametrico, ahora: datetime
    ) -> Siniestro:
        lugar = evento.ubicacion or evento.numero_vuelo or "No especificado"
        descripcion = (
            f"Siniestro paramétrico automático por evento {evento.tipo_evento}: "
            f"valor observado {evento.valor_observado}. Origen telemetría externa."
        )
        return Siniestro(
            siniestro_id=self._generar_id(),
            cliente_id=poliza.cliente_id,
            poliza_id=poliza.poliza_id,
            origen=OrigenSiniestro.AUTOMATICO,
            estado=EstadoSiniestro.REGISTRADO,
            evento_id=evento.evento_id,
            fecha_evento=evento.fecha_evento.date(),
            hora_evento=evento.fecha_evento.timetz().replace(tzinfo=None),
            lugar=lugar[:200],
            descripcion=descripcion[:2000],
            # La suma asegurada contratada es la estimación del pago paramétrico.
            estimacion_danos=poliza.cobertura_principal.suma_asegurada,
            moneda=poliza.moneda,
            registrado_por="TELEMETRIA",
            registrado_en=ahora,
        )

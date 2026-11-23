"""Endpoint de integración de telemetría externa (HU20).

Recibe los eventos que empuja el proveedor externo (retraso de vuelo, clima) y, por defecto, los
encola para que un worker los procese a su ritmo (contrapresión): así un pico del proveedor no
tumba el backend. La autenticación es `sistema → sistema` mediante la cabecera `X-API-Key`: no usa
JWT de usuario. La credencial se lee de la variable de entorno `SOLVENTA_TELEMETRY_API_KEY`;
nunca se escribe en el código.

Modos de operación (variable `EC_MODO_SINCRONO`, por defecto `false`):

- Asíncrono (recomendado): valida el cuerpo, publica en la cola y responde 202 solo si el
  transporte confirmó la recepción (hay `MessageId`). Si el publicador falla, responde 503 para
  que el proveedor reintente. El publicador se elige por entorno: `PublicadorSQS` si está
  definido `SQS_QUEUE_URL`, si no `PublicadorEnMemoria`.
- Síncrono (`EC_MODO_SINCRONO=true`): conserva el comportamiento anterior, procesando el evento
  en línea con `ServicioTelemetria`. Útil para desarrollo local y para no romper pruebas.

Queda preparado para sustituir la API Key por OAuth Client Credentials o API Gateway sin tocar el
servicio: bastaría cambiar `verificar_api_key`.
"""

import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.desembolsos import construir_evaluacion
from app.infraestructura.database import get_db
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.siniestros.cola import PublicacionFallida, PublicadorEventos, construir_publicador
from app.siniestros.metricas import EVENTOS_RECIBIDOS, MetricasTelemetria
from app.siniestros.repositorio import RepositorioSiniestrosPostgres
from app.siniestros.telemetria import (
    EventoParametrico,
    ResultadoTelemetria,
    ServicioTelemetria,
)

router = APIRouter(prefix="/api/v1/integraciones/telemetria", tags=["integraciones"])

API_KEY_POR_DEFECTO = "solventa-telemetry-dev"


def modo_sincrono() -> bool:
    """Si es verdadero, el evento se procesa en línea en vez de encolarse."""
    return os.getenv("EC_MODO_SINCRONO", "false").strip().lower() == "true"


def verificar_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Valida la credencial de servicio. Comparación en tiempo constante."""
    esperada = os.getenv("SOLVENTA_TELEMETRY_API_KEY", API_KEY_POR_DEFECTO)
    if not x_api_key or not secrets.compare_digest(x_api_key, esperada):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "codigo": "API_KEY_INVALIDA",
                "mensaje": "Credencial de servicio ausente o inválida.",
            },
        )


def obtener_servicio(db: Session = Depends(get_db)) -> ServicioTelemetria:
    # El siniestro paramétrico se aprueba solo y su desembolso se ordena de inmediato (HU15).
    evaluacion = construir_evaluacion(db)
    return ServicioTelemetria(
        siniestros=RepositorioSiniestrosPostgres(db),
        polizas=RepositorioPolizasPostgres(db),
        al_crear=evaluacion.aprobar_automatico,
    )


def obtener_publicador() -> PublicadorEventos:
    """Publicador de la cola. Se sobreescribe en pruebas con uno en memoria o uno que falla."""
    return construir_publicador()


def obtener_metricas() -> MetricasTelemetria:
    return MetricasTelemetria()


class EventoTelemetriaEntrada(BaseModel):
    """Cuerpo del evento que envía el proveedor externo.

    Se aceptan campos extra (`fuente`, `unidad`, etc.): el proveedor puede enriquecer el evento
    sin romper la integración. Solo se exige lo que Solventa necesita para decidir.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    evento_id: str = Field(min_length=1, max_length=120)
    tipo_evento: str = Field(min_length=1, max_length=40)
    valor_observado: float
    fecha_evento: str = Field(min_length=1)
    numero_vuelo: str | None = Field(default=None, max_length=20)
    ubicacion: str | None = Field(default=None, max_length=120)


# El resultado de negocio se mapea a un código HTTP: creado -> 201, el resto -> 200 (recibido).
_ESTADOS = {
    ResultadoTelemetria.SINIESTRO_CREADO: status.HTTP_201_CREATED,
    ResultadoTelemetria.SIN_COBERTURA: status.HTTP_200_OK,
    ResultadoTelemetria.DUPLICADO: status.HTTP_200_OK,
}


@router.post(
    "/eventos",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Recibe un evento de telemetría externa y lo encola para evaluación paramétrica",
    responses={
        200: {"description": "Modo síncrono: evento procesado (sin cobertura o duplicado)."},
        201: {"description": "Modo síncrono: se creó un siniestro automático."},
        202: {"description": "Evento aceptado y encolado para su procesamiento."},
        401: {"description": "Credencial de servicio ausente o inválida."},
        503: {"description": "La cola no está disponible: reintentar."},
    },
    dependencies=[Depends(verificar_api_key)],
)
def recibir_evento(
    entrada: EventoTelemetriaEntrada,
    servicio: ServicioTelemetria = Depends(obtener_servicio),
    publicador: PublicadorEventos = Depends(obtener_publicador),
    metricas: MetricasTelemetria = Depends(obtener_metricas),
) -> JSONResponse:
    if modo_sincrono():
        return _procesar_inline(entrada, servicio)

    try:
        message_id = publicador.publicar(entrada.model_dump())
    except PublicacionFallida as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "codigo": "COLA_NO_DISPONIBLE",
                "mensaje": "No se pudo encolar el evento; reintentar.",
            },
        ) from error
    metricas.contar(EVENTOS_RECIBIDOS)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"evento_id": entrada.evento_id, "estado": "ENCOLADO", "message_id": message_id},
    )


def _procesar_inline(
    entrada: EventoTelemetriaEntrada, servicio: ServicioTelemetria
) -> JSONResponse:
    evento = EventoParametrico(
        evento_id=entrada.evento_id,
        tipo_evento=entrada.tipo_evento,
        valor_observado=entrada.valor_observado,
        fecha_evento=entrada.fecha_evento,
        numero_vuelo=entrada.numero_vuelo,
        ubicacion=entrada.ubicacion,
    )
    resultado = servicio.procesar(evento)
    return JSONResponse(
        status_code=_ESTADOS[resultado.resultado],
        content=resultado.model_dump(),
    )

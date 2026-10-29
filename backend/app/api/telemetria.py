"""Endpoint de integración de telemetría externa (HU20).

Recibe los eventos que empuja el proveedor externo (retraso de vuelo, clima) y delega en el
servicio paramétrico. La autenticación es `sistema → sistema` mediante la cabecera `X-API-Key`:
no usa JWT de usuario. La credencial se lee de la variable de entorno
`SOLVENTA_TELEMETRY_API_KEY`; nunca se escribe en el código.

Queda preparado para sustituir la API Key por OAuth Client Credentials o API Gateway sin tocar
el servicio: bastaría cambiar `verificar_api_key`.
"""

import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.infraestructura.database import get_db
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.siniestros.repositorio import RepositorioSiniestrosPostgres
from app.siniestros.telemetria import (
    EventoParametrico,
    RespuestaTelemetria,
    ResultadoTelemetria,
    ServicioTelemetria,
)

router = APIRouter(prefix="/api/v1/integraciones/telemetria", tags=["integraciones"])

API_KEY_POR_DEFECTO = "solventa-telemetry-dev"


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
    return ServicioTelemetria(
        siniestros=RepositorioSiniestrosPostgres(db),
        polizas=RepositorioPolizasPostgres(db),
    )


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
    response_model=RespuestaTelemetria,
    status_code=status.HTTP_200_OK,
    summary="Recibe un evento de telemetría externa y evalúa la cobertura paramétrica",
    responses={
        200: {"description": "Evento recibido: sin cobertura o ya procesado (idempotente)."},
        201: {"description": "Se creó un siniestro automático por alcanzar el umbral."},
        401: {"description": "Credencial de servicio ausente o inválida."},
    },
    dependencies=[Depends(verificar_api_key)],
)
def recibir_evento(
    entrada: EventoTelemetriaEntrada,
    servicio: ServicioTelemetria = Depends(obtener_servicio),
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

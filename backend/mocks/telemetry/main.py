"""Proveedor externo simulado de telemetría (HU20).

Aplicación FastAPI independiente del backend de Solventa. Simula proveedores externos de
información (seguimiento de vuelos, clima), genera un evento y lo empuja hacia Solventa.

El proveedor NO decide si corresponde un siniestro: no compara umbrales, no consulta pólizas
ni clientes, no crea siniestros ni pagos. Solo informa la observación. Solventa decide.

Ejecución local:
    uvicorn mocks.telemetry.main:app --reload --port 8004
"""

from fastapi import Depends, FastAPI, HTTPException, status

from mocks.telemetry.cliente_solventa import (
    ClienteSolventa,
    ErrorEntregaSolventa,
    ErrorRespuestaSolventa,
)
from mocks.telemetry.modelos import (
    EventoTelemetria,
    RespuestaSimulacion,
    SolicitudEventoClimatico,
    SolicitudRetrasoVuelo,
    construir_evento_clima,
    construir_evento_vuelo,
    generar_id_clima,
    generar_id_vuelo,
)

app = FastAPI(title="Telemetry Provider Mock")

# Almacén en memoria solo para la demo de idempotencia y la consulta de eventos. No es una base
# de datos: se reinicia con el proceso y guarda los eventos ya generados por su evento_id.
_eventos: dict[str, EventoTelemetria] = {}
_resultados: dict[str, RespuestaSimulacion] = {}


def obtener_cliente() -> ClienteSolventa:
    """Dependencia inyectable; en pruebas se sustituye por un doble."""
    return ClienteSolventa()


def _entregar(evento: EventoTelemetria, cliente: ClienteSolventa) -> RespuestaSimulacion:
    """Empuja el evento a Solventa y traduce los fallos a códigos HTTP del proveedor."""
    try:
        solventa_status = cliente.enviar_evento(evento.model_dump())
    except ErrorEntregaSolventa:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "codigo": "SOLVENTA_UNAVAILABLE",
                "mensaje": "No fue posible entregar el evento a Solventa.",
            },
        ) from None
    except ErrorRespuestaSolventa as error:
        # Solventa respondió con error (401/403/422/500...). No se oculta: se propaga como 502.
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail={
                "codigo": "SOLVENTA_ERROR",
                "mensaje": "Solventa rechazó el evento.",
                "solventa_status": error.status_code,
                "solventa_detalle": error.cuerpo,
            },
        ) from None

    _eventos[evento.evento_id] = evento
    resultado = RespuestaSimulacion(
        evento_id=evento.evento_id,
        tipo_evento=evento.tipo_evento,
        enviado=True,
        solventa_status=solventa_status,
    )
    _resultados[evento.evento_id] = resultado
    return resultado


@app.get("/health")
def health() -> dict[str, str]:
    """Salud del proveedor. No contacta a Solventa."""
    return {"status": "ok", "service": "telemetry-provider"}


@app.post("/simulate/flight-delay", response_model=RespuestaSimulacion)
def simular_retraso_vuelo(
    solicitud: SolicitudRetrasoVuelo,
    cliente: ClienteSolventa = Depends(obtener_cliente),
) -> RespuestaSimulacion:
    """Simula un retraso de vuelo, genera el evento y lo empuja a Solventa."""
    evento_id = generar_id_vuelo(solicitud.numero_vuelo, solicitud.fecha_evento)
    evento = construir_evento_vuelo(solicitud, evento_id)
    return _entregar(evento, cliente)


@app.post("/simulate/weather-event", response_model=RespuestaSimulacion)
def simular_evento_climatico(
    solicitud: SolicitudEventoClimatico,
    cliente: ClienteSolventa = Depends(obtener_cliente),
) -> RespuestaSimulacion:
    """Simula un evento climático, genera el evento y lo empuja a Solventa."""
    evento_id = generar_id_clima(solicitud.ubicacion, solicitud.fecha_evento)
    evento = construir_evento_clima(solicitud, evento_id)
    return _entregar(evento, cliente)


@app.post("/simulate/retry/{evento_id}", response_model=RespuestaSimulacion)
def reenviar_evento(
    evento_id: str,
    cliente: ClienteSolventa = Depends(obtener_cliente),
) -> RespuestaSimulacion:
    """Reenvía un evento ya generado conservando el MISMO evento_id (demo de idempotencia)."""
    evento = _eventos.get(evento_id)
    if evento is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "codigo": "EVENTO_NO_ENCONTRADO",
                "mensaje": "No existe un evento generado con ese identificador.",
            },
        )
    return _entregar(evento, cliente)


@app.get("/events", response_model=list[RespuestaSimulacion])
def listar_eventos() -> list[RespuestaSimulacion]:
    """Eventos generados en esta ejecución. Solo para desarrollo/demo."""
    return list(_resultados.values())

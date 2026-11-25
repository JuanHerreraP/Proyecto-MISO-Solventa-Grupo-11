"""Proveedor externo simulado de telemetría (HU20).

Aplicación FastAPI independiente del backend de Solventa. Simula proveedores externos de
información (seguimiento de vuelos, clima), genera un evento y lo empuja hacia Solventa.

El proveedor NO decide si corresponde un siniestro: no compara umbrales, no consulta pólizas
ni clientes, no crea siniestros ni pagos. Solo informa la observación. Solventa decide.

Ejecución local:
    uvicorn mocks.telemetry.main:app --reload --port 8004

En AWS corre como contenedor acompañante del backend (puerto 8004, solo accesible dentro de la
tarea). El backend lo publica de forma controlada en `/api/telemetry/*` mediante un proxy inverso
con autenticación HTTP Basic. Para que Swagger, ReDoc y el `openapi.json` funcionen detrás de ese
prefijo se fija `root_path` desde la variable de entorno `TELEMETRY_ROOT_PATH`
(p. ej. `/api/telemetry`). Vacío = ejecución local directa en el puerto 8004.
"""

import os

from fastapi import Depends, FastAPI, HTTPException, status

from mocks.telemetry.almacen import (
    AlmacenEnMemoria,
    AlmacenEventos,
    construir_almacen,
)
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

# `root_path` deja que FastAPI sepa bajo qué prefijo lo ve el cliente (lo pone el proxy/CloudFront)
# sin que las rutas internas cambien: así `/docs`, `/redoc` y `/openapi.json` apuntan al prefijo
# correcto y Swagger puede ejecutar peticiones con "Try it out".
ROOT_PATH = os.getenv("TELEMETRY_ROOT_PATH", "").rstrip("/")

app = FastAPI(title="Telemetry Provider Mock", root_path=ROOT_PATH)

# Almacén de eventos. En AWS (con REDIS_URL) es compartido entre réplicas; en local y en pruebas
# es en memoria. Se expone a nivel de módulo para poder sustituirlo en las pruebas.
_almacen: AlmacenEventos = construir_almacen()

# Compatibilidad con las pruebas existentes, que limpian estos diccionarios entre casos. Cuando el
# almacén es el de memoria, son sus mismos diccionarios internos.
if isinstance(_almacen, AlmacenEnMemoria):
    _eventos = _almacen._eventos
    _resultados = _almacen._resultados
else:  # pragma: no cover - solo en AWS con Redis
    _eventos: dict[str, EventoTelemetria] = {}
    _resultados: dict[str, RespuestaSimulacion] = {}


def obtener_cliente() -> ClienteSolventa:
    """Dependencia inyectable; en pruebas se sustituye por un doble."""
    return ClienteSolventa()


def obtener_almacen() -> AlmacenEventos:
    """Dependencia inyectable del almacén; en pruebas se sustituye por uno en memoria."""
    return _almacen


def _entregar(
    evento: EventoTelemetria,
    cliente: ClienteSolventa,
    almacen: AlmacenEventos,
) -> RespuestaSimulacion:
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

    resultado = RespuestaSimulacion(
        evento_id=evento.evento_id,
        tipo_evento=evento.tipo_evento,
        enviado=True,
        solventa_status=solventa_status,
    )
    almacen.guardar(evento, resultado)
    return resultado


@app.get("/health")
def health() -> dict[str, str]:
    """Salud del proveedor. No contacta a Solventa."""
    return {"status": "ok", "service": "telemetry-provider"}


@app.post("/simulate/flight-delay", response_model=RespuestaSimulacion)
def simular_retraso_vuelo(
    solicitud: SolicitudRetrasoVuelo,
    cliente: ClienteSolventa = Depends(obtener_cliente),
    almacen: AlmacenEventos = Depends(obtener_almacen),
) -> RespuestaSimulacion:
    """Simula un retraso de vuelo, genera el evento y lo empuja a Solventa."""
    evento_id = generar_id_vuelo(solicitud.numero_vuelo, solicitud.fecha_evento)
    evento = construir_evento_vuelo(solicitud, evento_id)
    return _entregar(evento, cliente, almacen)


@app.post("/simulate/weather-event", response_model=RespuestaSimulacion)
def simular_evento_climatico(
    solicitud: SolicitudEventoClimatico,
    cliente: ClienteSolventa = Depends(obtener_cliente),
    almacen: AlmacenEventos = Depends(obtener_almacen),
) -> RespuestaSimulacion:
    """Simula un evento climático, genera el evento y lo empuja a Solventa."""
    evento_id = generar_id_clima(solicitud.ubicacion, solicitud.fecha_evento)
    evento = construir_evento_clima(solicitud, evento_id)
    return _entregar(evento, cliente, almacen)


@app.post("/simulate/retry/{evento_id}", response_model=RespuestaSimulacion)
def reenviar_evento(
    evento_id: str,
    cliente: ClienteSolventa = Depends(obtener_cliente),
    almacen: AlmacenEventos = Depends(obtener_almacen),
) -> RespuestaSimulacion:
    """Reenvía un evento ya generado conservando el MISMO evento_id (demo de idempotencia).

    El evento se busca en el almacén compartido, así que el reenvío funciona aunque la petición
    original la haya atendido otra réplica del backend.
    """
    evento = almacen.obtener_evento(evento_id)
    if evento is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "codigo": "EVENTO_NO_ENCONTRADO",
                "mensaje": "No existe un evento generado con ese identificador.",
            },
        )
    return _entregar(evento, cliente, almacen)


@app.get("/events", response_model=list[RespuestaSimulacion])
def listar_eventos(
    almacen: AlmacenEventos = Depends(obtener_almacen),
) -> list[RespuestaSimulacion]:
    """Eventos generados y vistos entre todas las réplicas. Solo para desarrollo/demo."""
    return almacen.listar_resultados()

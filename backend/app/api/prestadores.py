"""API de consulta de prestadores cercanos (HU06).

Devuelve los prestadores activos que ofrecen el servicio pedido, dentro del radio, ordenados
del más cercano al más lejano. Reutiliza el servicio y las validaciones de póliza de
`app.api.asistencias`. El `cliente_id` sale de la sesión.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.asistencias import cliente_actual, obtener_servicio, traducir_errores_poliza
from app.asistencias.modelos import (
    RADIO_KM_MAXIMO,
    RADIO_KM_MINIMO,
    RADIO_KM_POR_DEFECTO,
    TipoServicioAsistencia,
)
from app.asistencias.servicio import (
    PolizaAjena,
    PolizaNoEncontrada,
    PolizaNoVigente,
    RadioInvalido,
    ServicioAsistencias,
    ServicioNoDisponible,
)
from app.asistencias.vistas import PrestadoresCercanos, Ubicacion, a_prestador_cercano

router = APIRouter(prefix="/api/v1/prestadores", tags=["prestadores"])


@router.get(
    "/cercanos",
    response_model=PrestadoresCercanos,
    summary="Prestadores cercanos compatibles con un servicio, ordenados por distancia",
    responses={
        403: {"description": "La póliza no pertenece al cliente autenticado."},
        404: {"description": "La póliza no existe."},
        409: {"description": "La póliza no está vigente."},
        422: {"description": "Servicio incompatible con el ramo, o radio fuera de rango."},
    },
)
def prestadores_cercanos(
    respuesta: Response,
    poliza_id: Annotated[str, Query(min_length=1, max_length=50)],
    servicio: Annotated[
        TipoServicioAsistencia, Query(description="Servicio de asistencia requerido")
    ],
    latitud: Annotated[float, Query(ge=-90, le=90)],
    longitud: Annotated[float, Query(ge=-180, le=180)],
    radio_km: Annotated[
        float, Query(ge=RADIO_KM_MINIMO, le=RADIO_KM_MAXIMO)
    ] = RADIO_KM_POR_DEFECTO,
    usuario=Depends(cliente_actual),
    servicio_asistencias: ServicioAsistencias = Depends(obtener_servicio),
) -> PrestadoresCercanos:
    respuesta.headers["Cache-Control"] = "no-store"
    respuesta.headers["Pragma"] = "no-cache"
    try:
        compatibles = servicio_asistencias.prestadores_cercanos(
            cliente_id=str(usuario.id),
            poliza_id=poliza_id,
            servicio=servicio,
            latitud=latitud,
            longitud=longitud,
            radio_km=radio_km,
        )
    except RadioInvalido:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {
                "codigo": "RADIO_INVALIDO",
                "mensaje": (
                    f"El radio debe estar entre {int(RADIO_KM_MINIMO)} y {int(RADIO_KM_MAXIMO)} km."
                ),
            },
        ) from None
    except (
        PolizaNoEncontrada,
        PolizaAjena,
        PolizaNoVigente,
        ServicioNoDisponible,
    ) as error:
        raise traducir_errores_poliza(error) from None

    return PrestadoresCercanos(
        poliza_id=poliza_id,
        servicio=servicio,
        ubicacion=Ubicacion(latitud=latitud, longitud=longitud),
        prestadores=[
            a_prestador_cercano(c.prestador, c.servicio, c.distancia) for c in compatibles
        ],
    )


__all__ = ["router"]

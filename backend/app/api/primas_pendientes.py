"""API de las primas pendientes de pago del cliente (HU21).

Lista, en un solo lugar, lo que el cliente debe resolver para tener su cobertura al día: las
renovaciones iniciadas sin pagar, las cotizaciones vigentes sin pagar y los contratos pagados
que faltan por firmar. El pago se hace con `POST /api/v1/pagos` sobre el `cotizacion_id` del
ítem; la firma sigue en el portal web.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.pagos import cliente_pagador
from app.api.renovaciones import obtener_servicio as obtener_renovaciones
from app.cotizaciones.repositorio import RepositorioCotizacionesPostgres
from app.firmas.repositorio import RepositorioFirmasPostgres
from app.infraestructura.database import get_db
from app.pagos.repositorio import RepositorioPagosPostgres
from app.polizas.dominio.primas_pendientes import PrimasPendientes
from app.polizas.primas_pendientes import ServicioPrimasPendientes
from app.polizas.renovacion import ServicioRenovaciones
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_renovaciones import RepositorioRenovacionesPostgres

router = APIRouter(prefix="/api/v1/primas-pendientes", tags=["primas-pendientes"])


def obtener_servicio(
    db: Session = Depends(get_db),
    renovaciones: ServicioRenovaciones = Depends(obtener_renovaciones),
) -> ServicioPrimasPendientes:
    return ServicioPrimasPendientes(
        cotizaciones=RepositorioCotizacionesPostgres(db),
        pagos=RepositorioPagosPostgres(db),
        polizas=RepositorioPolizasPostgres(db),
        renovaciones=RepositorioRenovacionesPostgres(db),
        firmas=RepositorioFirmasPostgres(db),
        aplicar_pago=renovaciones.aplicar_pago,
    )


@router.get(
    "",
    response_model=PrimasPendientes,
    summary="Lista las primas pendientes del cliente, las más urgentes primero",
)
def listar_primas_pendientes(
    response: Response,
    cliente_id: str = Depends(cliente_pagador),
    servicio: ServicioPrimasPendientes = Depends(obtener_servicio),
) -> PrimasPendientes:
    response.headers["Cache-Control"] = "no-store"
    return servicio.listar(cliente_id)

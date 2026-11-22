"""API de la renovación automática de la póliza (HU17 / BPM-69).

- El cliente titular (o el asesor de la venta asistida) consulta y cambia la preferencia. Solo el
  cliente registra o quita la tarjeta tokenizada con la que se cobra la renovación.
- El cliente descarga el documento contractual de cada periodo renovado automáticamente.
- Operaciones (rol `SERVICIO_INTERNO`) puede ejecutar la tarea diaria a demanda. En AWS la
  ejecuta una tarea programada con `python -m app.polizas.tarea_renovacion_automatica`.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.cancelaciones import solicitante_actual
from app.api.emision import obtener_almacen
from app.api.enriquecimiento import obtener_consentimientos
from app.api.pagos import armar_comprobantes, obtener_pasarela
from app.api.perfilamiento import obtener_repositorio as obtener_perfiles
from app.api.seguridad import requiere_roles
from app.cotizaciones.repositorio import RepositorioCotizacionesPostgres
from app.cotizaciones.servicio_personalizacion import ServicioPersonalizacionCotizacion
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.pagos.pasarela_simulada import PasarelaSimulada
from app.pagos.puertos import PasarelaPagos
from app.pagos.repositorio import RepositorioPagosPostgres
from app.pagos.servicio import ServicioPagos, en_cadena
from app.perfilamiento.enriquecimiento.puertos import RepositorioConsentimientos
from app.perfilamiento.repositorio import RepositorioPerfiles
from app.polizas.almacenamiento import AlmacenDocumentos, AlmacenNoDisponible, crear_almacen
from app.polizas.comunicaciones import CorreoRenovacionSimulado, EnviadorCorreoRenovacion
from app.polizas.directorio_correos import DirectorioCorreosIdentidad
from app.polizas.dominio.renovacion import RenovacionNoEncontrada
from app.polizas.dominio.renovacion_automatica import ResultadoEjecucion
from app.polizas.emision import AccesoDenegado, DocumentoAlterado, DocumentoNoDisponible
from app.polizas.endosos import Solicitante
from app.polizas.renovacion import ServicioRenovaciones
from app.polizas.renovacion_automatica import (
    RenovacionAutomaticaNoDisponible,
    ServicioRenovacionAutomatica,
)
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.polizas.repositorio_renovacion_automatica import (
    RepositorioCiclosPostgres,
    RepositorioPreferenciasPostgres,
)
from app.polizas.repositorio_renovaciones import RepositorioRenovacionesPostgres
from app.polizas.servicio import PolizaNoEncontrada
from app.polizas.vistas_renovacion_automatica import (
    PreferenciaSolicitud,
    RenovacionAutomaticaVista,
    a_vista,
    medio_de,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/polizas", tags=["renovacion-automatica"])
router_operaciones = APIRouter(
    prefix="/api/v1/operaciones/renovaciones-automaticas", tags=["renovacion-automatica"]
)
operador_actual = requiere_roles(Rol.SERVICIO_INTERNO.value)

_correo = CorreoRenovacionSimulado()


def obtener_correo() -> EnviadorCorreoRenovacion:
    return _correo


def construir_servicio(
    db: Session,
    pasarela: PasarelaPagos | None = None,
    almacen: AlmacenDocumentos | None = None,
    correo: EnviadorCorreoRenovacion | None = None,
    personalizador: ServicioPersonalizacionCotizacion | None = None,
) -> ServicioRenovacionAutomatica:
    """Arma el servicio con los adaptadores de base de datos; lo usan la API y la tarea."""
    polizas = RepositorioPolizasPostgres(db)
    cotizaciones = RepositorioCotizacionesPostgres(db)
    renovaciones = RepositorioRenovacionesPostgres(db)
    pagos = RepositorioPagosPostgres(db)
    if personalizador is None:
        personalizador = ServicioPersonalizacionCotizacion(
            perfiles=obtener_perfiles(), consentimientos=obtener_consentimientos()
        )
    servicio_renovaciones = ServicioRenovaciones(
        polizas=polizas,
        renovaciones=renovaciones,
        cotizaciones=cotizaciones,
        personalizador=personalizador,
        pagos=pagos,
    )
    comprobantes = armar_comprobantes(db)
    servicio_pagos = ServicioPagos(
        pagos=pagos,
        cotizaciones=cotizaciones,
        pasarela=pasarela or PasarelaSimulada(),
        # Igual que en el pago manual: aplica la renovación y emite el comprobante (HU21).
        al_aprobar=en_cadena(servicio_renovaciones.aplicar_pago, comprobantes.emitir),
        concepto_de=comprobantes.concepto_de,
    )
    return ServicioRenovacionAutomatica(
        polizas=polizas,
        cotizaciones=cotizaciones,
        preferencias=RepositorioPreferenciasPostgres(db),
        ciclos=RepositorioCiclosPostgres(db),
        renovaciones=renovaciones,
        servicio_renovaciones=servicio_renovaciones,
        pagos=pagos,
        servicio_pagos=servicio_pagos,
        almacen=almacen or crear_almacen(),
        correo=correo or obtener_correo(),
        directorio=DirectorioCorreosIdentidad(db),
    )


def obtener_servicio(
    db: Session = Depends(get_db),
    pasarela: PasarelaPagos = Depends(obtener_pasarela),
    almacen: AlmacenDocumentos = Depends(obtener_almacen),
    correo: EnviadorCorreoRenovacion = Depends(obtener_correo),
    perfiles: RepositorioPerfiles = Depends(obtener_perfiles),
    consentimientos: RepositorioConsentimientos = Depends(obtener_consentimientos),
) -> ServicioRenovacionAutomatica:
    return construir_servicio(
        db,
        pasarela=pasarela,
        almacen=almacen,
        correo=correo,
        personalizador=ServicioPersonalizacionCotizacion(
            perfiles=perfiles, consentimientos=consentimientos
        ),
    )


def _error(codigo: str, mensaje: str) -> dict[str, str]:
    return {"codigo": codigo, "mensaje": mensaje}


def _traducir(error: Exception) -> HTTPException:
    if isinstance(error, PolizaNoEncontrada):
        return HTTPException(
            status.HTTP_404_NOT_FOUND, _error("POLIZA_NO_ENCONTRADA", "La póliza no existe.")
        )
    if isinstance(error, RenovacionNoEncontrada):
        return HTTPException(
            status.HTTP_404_NOT_FOUND,
            _error("RENOVACION_NO_ENCONTRADA", "La renovación no existe."),
        )
    if isinstance(error, AccesoDenegado):
        return HTTPException(
            status.HTTP_403_FORBIDDEN,
            _error(
                "ACCESO_DENEGADO",
                "Solo el cliente titular registra su tarjeta; el asesor solo gestiona las "
                "pólizas de sus ventas asistidas.",
            ),
        )
    if isinstance(error, RenovacionAutomaticaNoDisponible):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            _error(
                "RAMO_NO_RENOVABLE",
                "Este seguro no se renueva: se contrata de nuevo cuando lo necesites.",
            ),
        )
    if isinstance(error, (DocumentoNoDisponible, AlmacenNoDisponible)):
        return HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            _error("DOCUMENTO_NO_DISPONIBLE", "El documento no está disponible en este momento."),
        )
    if isinstance(error, DocumentoAlterado):
        return HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            _error("DOCUMENTO_ALTERADO", "El documento no pasó la verificación de integridad."),
        )
    raise error


_ERRORES = (
    PolizaNoEncontrada,
    RenovacionNoEncontrada,
    AccesoDenegado,
    RenovacionAutomaticaNoDisponible,
    DocumentoNoDisponible,
    AlmacenNoDisponible,
    DocumentoAlterado,
)


@router.get(
    "/{poliza_id}/renovacion-automatica",
    response_model=RenovacionAutomaticaVista,
    summary="Estado de la renovación automática de la póliza",
    description=(
        "Indica si está activa, si hay una tarjeta registrada (solo sus últimos dígitos), "
        "cuándo se envía el preaviso y cuándo se cobra, y en qué quedó el último periodo."
    ),
)
def consultar(
    poliza_id: str,
    respuesta: Response,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioRenovacionAutomatica = Depends(obtener_servicio),
) -> RenovacionAutomaticaVista:
    respuesta.headers["Cache-Control"] = "no-store"
    try:
        poliza, preferencia, ciclo = servicio.consultar(solicitante, poliza_id)
    except _ERRORES as error:
        raise _traducir(error) from None
    return a_vista(poliza, preferencia, ciclo)


@router.put(
    "/{poliza_id}/renovacion-automatica",
    response_model=RenovacionAutomaticaVista,
    summary="Activa o desactiva la renovación automática y registra la tarjeta",
    description=(
        "`tarjeta` lleva el token de la pasarela, nunca el número de la tarjeta. Sin `tarjeta` "
        "se conserva la registrada; `quitar_tarjeta` la elimina. Registrar o quitar la tarjeta "
        "es exclusivo del cliente titular."
    ),
)
def configurar(
    poliza_id: str,
    solicitud: PreferenciaSolicitud,
    respuesta: Response,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioRenovacionAutomatica = Depends(obtener_servicio),
) -> RenovacionAutomaticaVista:
    respuesta.headers["Cache-Control"] = "no-store"
    try:
        servicio.configurar(
            solicitante,
            poliza_id,
            activa=solicitud.activa,
            medio_pago=medio_de(solicitud),
            quitar_medio_pago=solicitud.quitar_tarjeta,
        )
        poliza, preferencia, ciclo = servicio.consultar(solicitante, poliza_id)
    except _ERRORES as error:
        raise _traducir(error) from None
    return a_vista(poliza, preferencia, ciclo)


@router.get(
    "/{poliza_id}/renovacion-automatica/{renovacion_id}/documento",
    response_class=Response,
    summary="Documento contractual de un periodo renovado automáticamente (PDF)",
    responses={200: {"content": {"application/pdf": {}}}},
)
def descargar_documento(
    poliza_id: str,
    renovacion_id: str,
    solicitante: Solicitante = Depends(solicitante_actual),
    servicio: ServicioRenovacionAutomatica = Depends(obtener_servicio),
) -> Response:
    try:
        documento = servicio.documento(solicitante, poliza_id, renovacion_id)
    except _ERRORES as error:
        raise _traducir(error) from None
    return Response(
        content=documento.contenido,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{documento.nombre_archivo}"',
            "X-Huella-Documento": documento.huella_sha256,
            "Cache-Control": "no-store",
        },
    )


@router_operaciones.post(
    "/ejecuciones",
    response_model=ResultadoEjecucion,
    summary="Ejecuta a demanda la tarea diaria de renovación automática",
    description=(
        "Envía los preavisos pendientes, cobra las renovaciones que vencen hoy y da seguimiento "
        "a los ciclos abiertos. Es idempotente: ejecutarla varias veces el mismo día no repite "
        "correos ni cobros."
    ),
)
def ejecutar(
    _operador=Depends(operador_actual),
    servicio: ServicioRenovacionAutomatica = Depends(obtener_servicio),
) -> ResultadoEjecucion:
    return servicio.ejecutar()

"""API del desembolso de indemnizaciones (HU15 / BPM-65).

- El cliente registra la cuenta donde recibe sus indemnizaciones y consulta sus desembolsos.
- Operaciones/Siniestros revisa la bandeja, aprueba (lo que ordena el desembolso) o rechaza,
  y reintenta un desembolso pendiente o fallido.
"""

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.seguridad import requiere_roles
from app.desembolsos.modelos import (
    CuentaDesembolso,
    Desembolso,
    EstadoDesembolso,
    MedioDesembolso,
    SolicitudCuenta,
    TipoCuenta,
)
from app.desembolsos.red_simulada import RedDesembolsosSimulada
from app.desembolsos.repositorio import (
    RepositorioCuentasPostgres,
    RepositorioDesembolsosPostgres,
)
from app.desembolsos.servicio import (
    DesembolsoNoEncontrado,
    DesembolsoNoReintentable,
    ServicioDesembolsos,
)
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.polizas.repositorio import RepositorioPolizasPostgres
from app.siniestros.evaluacion import (
    MontoInvalido,
    ServicioEvaluacion,
    SiniestroNoEncontrado,
    SiniestroYaEvaluado,
)
from app.siniestros.modelos import (
    EstadoSiniestro,
    OrigenSiniestro,
    SolicitudAprobacion,
    SolicitudRechazo,
)
from app.siniestros.repositorio import RepositorioSiniestrosPostgres

router_cliente = APIRouter(prefix="/api/v1/desembolsos", tags=["desembolsos"])
router_operaciones = APIRouter(prefix="/api/v1/operaciones/siniestros", tags=["desembolsos"])

cliente_actual = requiere_roles(Rol.CLIENTE.value)
operador_actual = requiere_roles(Rol.OPERACIONES_SINIESTROS.value)


def obtener_red() -> RedDesembolsosSimulada:
    return RedDesembolsosSimulada()


def construir_desembolsos(db: Session, red=None) -> ServicioDesembolsos:
    return ServicioDesembolsos(
        desembolsos=RepositorioDesembolsosPostgres(db),
        cuentas=RepositorioCuentasPostgres(db),
        red=red or obtener_red(),
    )


def construir_evaluacion(db: Session, red=None) -> ServicioEvaluacion:
    return ServicioEvaluacion(
        siniestros=RepositorioSiniestrosPostgres(db),
        polizas=RepositorioPolizasPostgres(db),
        desembolsos=construir_desembolsos(db, red),
    )


def obtener_desembolsos(
    db: Session = Depends(get_db), red=Depends(obtener_red)
) -> ServicioDesembolsos:
    return construir_desembolsos(db, red)


def obtener_evaluacion(
    db: Session = Depends(get_db), red=Depends(obtener_red)
) -> ServicioEvaluacion:
    return construir_evaluacion(db, red)


# --- Vistas -----------------------------------------------------------------------------


class CuentaVista(BaseModel):
    """La cuenta tal como se muestra: banco, tipo y últimos dígitos. Nunca el token."""

    codigo_banco: str
    nombre_banco: str
    tipo_cuenta: TipoCuenta
    ultimos_digitos: str
    actualizada_en: datetime


class DesembolsoVista(BaseModel):
    desembolso_id: str
    siniestro_id: str
    poliza_id: str
    monto: Decimal
    moneda: str
    medio: MedioDesembolso
    destino: str | None
    estado: EstadoDesembolso
    intento: int
    referencia_transaccion: str | None
    codigo_retiro: str | None
    motivo_fallo: str | None
    creado_en: datetime
    completado_en: datetime | None


class SiniestroBandeja(BaseModel):
    siniestro_id: str
    poliza_id: str
    cliente_id: str
    origen: OrigenSiniestro
    estado: EstadoSiniestro
    fecha_evento: date
    lugar: str
    descripcion: str
    estimacion_danos: Decimal
    moneda: str
    registrado_en: datetime
    monto_aprobado: Decimal | None
    evaluado_por: str | None
    evaluado_en: datetime | None
    motivo_rechazo: str | None
    desembolso: DesembolsoVista | None


def _cuenta(cuenta: CuentaDesembolso) -> CuentaVista:
    return CuentaVista(
        codigo_banco=cuenta.codigo_banco,
        nombre_banco=cuenta.nombre_banco,
        tipo_cuenta=cuenta.tipo_cuenta,
        ultimos_digitos=cuenta.ultimos_digitos,
        actualizada_en=cuenta.actualizada_en,
    )


def _desembolso(desembolso: Desembolso, con_codigo: bool) -> DesembolsoVista:
    datos = desembolso.model_dump(include=set(DesembolsoVista.model_fields))
    # El código de retiro es como dinero en efectivo: solo lo ve el titular.
    if not con_codigo:
        datos["codigo_retiro"] = None
    return DesembolsoVista(**datos)


def _bandeja(siniestro, desembolso) -> SiniestroBandeja:
    datos = siniestro.model_dump(include=set(SiniestroBandeja.model_fields) - {"desembolso"})
    return SiniestroBandeja(
        **datos,
        desembolso=_desembolso(desembolso, con_codigo=False) if desembolso else None,
    )


def _sin_cache(respuesta: Response) -> None:
    respuesta.headers["Cache-Control"] = "no-store"


def _error(codigo: str, mensaje: str) -> dict[str, str]:
    return {"codigo": codigo, "mensaje": mensaje}


# --- Cliente ----------------------------------------------------------------------------


@router_cliente.get(
    "/cuenta",
    response_model=CuentaVista | None,
    summary="Cuenta registrada para recibir indemnizaciones (null si no hay)",
)
def consultar_cuenta(
    respuesta: Response,
    usuario=Depends(cliente_actual),
    servicio: ServicioDesembolsos = Depends(obtener_desembolsos),
) -> CuentaVista | None:
    _sin_cache(respuesta)
    cuenta = servicio.cuenta(str(usuario.id))
    return _cuenta(cuenta) if cuenta else None


@router_cliente.put(
    "/cuenta",
    response_model=CuentaVista,
    summary="Registra o reemplaza la cuenta donde el cliente recibe sus indemnizaciones",
    description=(
        "El número de cuenta se tokeniza en la red de desembolsos y no se guarda en Solventa: "
        "solo quedan el banco, el tipo y los últimos cuatro dígitos."
    ),
)
def registrar_cuenta(
    solicitud: SolicitudCuenta,
    respuesta: Response,
    usuario=Depends(cliente_actual),
    servicio: ServicioDesembolsos = Depends(obtener_desembolsos),
) -> CuentaVista:
    _sin_cache(respuesta)
    return _cuenta(servicio.registrar_cuenta(str(usuario.id), solicitud))


@router_cliente.get(
    "",
    response_model=list[DesembolsoVista],
    summary="Desembolsos de las indemnizaciones del cliente, del más reciente al más antiguo",
)
def listar_desembolsos(
    respuesta: Response,
    usuario=Depends(cliente_actual),
    servicio: ServicioDesembolsos = Depends(obtener_desembolsos),
) -> list[DesembolsoVista]:
    _sin_cache(respuesta)
    return [_desembolso(d, con_codigo=True) for d in servicio.listar_de_cliente(str(usuario.id))]


# --- Operaciones/Siniestros -------------------------------------------------------------


@router_operaciones.get(
    "",
    response_model=list[SiniestroBandeja],
    summary="Bandeja de siniestros con su desembolso, del más reciente al más antiguo",
)
def bandeja(
    respuesta: Response,
    estado: EstadoSiniestro | None = None,
    _operador=Depends(operador_actual),
    servicio: ServicioEvaluacion = Depends(obtener_evaluacion),
) -> list[SiniestroBandeja]:
    _sin_cache(respuesta)
    return [_bandeja(s, d) for s, d in servicio.bandeja(estado)]


@router_operaciones.post(
    "/{siniestro_id}/aprobacion",
    response_model=SiniestroBandeja,
    summary="Aprueba el siniestro y ordena el desembolso de la indemnización",
    description=(
        "Sin monto se aprueba la estimación de daños, con tope en la suma asegurada. "
        "Repetir la misma aprobación devuelve el mismo desembolso: nunca se paga dos veces."
    ),
    responses={
        404: {"description": "El siniestro no existe."},
        409: {"description": "El siniestro ya fue rechazado o aprobado por otro monto."},
        422: {"description": "El monto supera la suma asegurada."},
    },
)
def aprobar(
    siniestro_id: str,
    solicitud: SolicitudAprobacion,
    operador=Depends(operador_actual),
    servicio: ServicioEvaluacion = Depends(obtener_evaluacion),
) -> SiniestroBandeja:
    try:
        siniestro, desembolso = servicio.aprobar(
            siniestro_id, str(operador.id), solicitud.monto_aprobado
        )
    except (SiniestroNoEncontrado, SiniestroYaEvaluado, MontoInvalido) as error:
        raise _traducir(error) from None
    return _bandeja(siniestro, desembolso)


@router_operaciones.post(
    "/{siniestro_id}/rechazo",
    response_model=SiniestroBandeja,
    summary="Rechaza el siniestro con un motivo",
)
def rechazar(
    siniestro_id: str,
    solicitud: SolicitudRechazo,
    operador=Depends(operador_actual),
    servicio: ServicioEvaluacion = Depends(obtener_evaluacion),
) -> SiniestroBandeja:
    try:
        siniestro = servicio.rechazar(siniestro_id, str(operador.id), solicitud.motivo)
    except (SiniestroNoEncontrado, SiniestroYaEvaluado) as error:
        raise _traducir(error) from None
    return _bandeja(siniestro, None)


@router_operaciones.post(
    "/{siniestro_id}/desembolso/reintento",
    response_model=DesembolsoVista,
    summary="Reintenta un desembolso pendiente o fallido",
)
def reintentar(
    siniestro_id: str,
    _operador=Depends(operador_actual),
    servicio: ServicioEvaluacion = Depends(obtener_evaluacion),
) -> DesembolsoVista:
    try:
        desembolso = servicio.reintentar_desembolso(siniestro_id)
    except (
        SiniestroNoEncontrado,
        SiniestroYaEvaluado,
        DesembolsoNoEncontrado,
        DesembolsoNoReintentable,
    ) as error:
        raise _traducir(error) from None
    return _desembolso(desembolso, con_codigo=False)


def _traducir(error: Exception) -> HTTPException:
    if isinstance(error, SiniestroNoEncontrado):
        return HTTPException(
            status.HTTP_404_NOT_FOUND, _error("SINIESTRO_NO_ENCONTRADO", "El siniestro no existe.")
        )
    if isinstance(error, SiniestroYaEvaluado):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            _error(
                "SINIESTRO_YA_EVALUADO",
                f"El siniestro está {error.estado.value.lower()} y no admite esta decisión.",
            ),
        )
    if isinstance(error, MontoInvalido):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            _error(
                "MONTO_INVALIDO",
                f"El monto debe ser mayor que cero y no superar la suma asegurada ({error.tope}).",
            ),
        )
    if isinstance(error, DesembolsoNoEncontrado):
        return HTTPException(
            status.HTTP_404_NOT_FOUND,
            _error("DESEMBOLSO_NO_ENCONTRADO", "El siniestro no tiene desembolso."),
        )
    if isinstance(error, DesembolsoNoReintentable):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            _error("DESEMBOLSO_COMPLETADO", "El desembolso ya se completó."),
        )
    raise error

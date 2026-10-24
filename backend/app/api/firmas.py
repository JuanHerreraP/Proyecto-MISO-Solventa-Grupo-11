"""API de la firma electrónica del contrato de seguro (HU14 / BPM-60)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.pagos import cliente_pagador
from app.cotizaciones.repositorio import RepositorioCotizacionesPostgres
from app.firmas.contrato import ContratoSeguro
from app.firmas.modelos import CanalOtp, EstadoFirma, ProcesoFirma
from app.firmas.proveedor_simulado import ProveedorFirmaSimulado
from app.firmas.puertos import ProveedorFirmaElectronica, ProveedorFirmaNoDisponible
from app.firmas.repositorio import RepositorioFirmasPostgres, RepositorioTitularesPostgres
from app.firmas.servicio import (
    DocumentoAlterado,
    FirmaBloqueada,
    FirmaNoDisponible,
    FirmaNoEncontrada,
    OtpRechazado,
    ReenvioNoPermitido,
    ServicioFirmas,
)
from app.infraestructura.database import get_db
from app.pagos.repositorio import RepositorioPagosPostgres

router = APIRouter(prefix="/api/v1/firmas", tags=["firmas"])

_proveedor_simulado = ProveedorFirmaSimulado()


def obtener_proveedor() -> ProveedorFirmaElectronica:
    return _proveedor_simulado


def obtener_servicio(
    db: Session = Depends(get_db),
    proveedor: ProveedorFirmaElectronica = Depends(obtener_proveedor),
) -> ServicioFirmas:
    return ServicioFirmas(
        firmas=RepositorioFirmasPostgres(db),
        cotizaciones=RepositorioCotizacionesPostgres(db),
        pagos=RepositorioPagosPostgres(db),
        titulares=RepositorioTitularesPostgres(db),
        proveedor=proveedor,
    )


class RespuestaFirma(BaseModel):
    """Lo que ve el cliente del proceso. Nunca incluye el OTP ni su hash."""

    firma_id: str
    cotizacion_id: str
    estado: EstadoFirma
    contrato: ContratoSeguro
    huella_documento: str
    documento_integro: bool
    otp_canal: CanalOtp | None
    otp_destino: str | None
    otp_expira_en: AwareDatetime | None
    reenvio_disponible_en: datetime | None
    intentos_restantes: int
    envios_restantes: int
    firmado_en: AwareDatetime | None
    ip_firmante: str | None
    referencia_proveedor: str | None

    @classmethod
    def de(cls, proceso: ProcesoFirma) -> "RespuestaFirma":
        return cls(
            firma_id=proceso.firma_id,
            cotizacion_id=proceso.cotizacion_id,
            estado=proceso.estado,
            contrato=proceso.contrato,
            huella_documento=proceso.huella_documento,
            documento_integro=proceso.documento_integro(),
            otp_canal=proceso.otp_canal,
            otp_destino=proceso.otp_destino,
            otp_expira_en=proceso.otp_expira_en,
            reenvio_disponible_en=proceso.reenvio_disponible_en(),
            intentos_restantes=proceso.intentos_restantes,
            envios_restantes=proceso.envios_restantes,
            firmado_en=proceso.firmado_en,
            ip_firmante=proceso.ip_firmante,
            referencia_proveedor=proceso.referencia_proveedor,
        )


class SolicitudOtp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canal: CanalOtp = CanalOtp.SMS


class SolicitudFirma(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    codigo: str = Field(pattern=r"^\d{6}$")
    huella_documento: str = Field(pattern=r"^[0-9a-f]{64}$")


_NO_DISPONIBLE = {
    "COTIZACION_NO_ENCONTRADA": (status.HTTP_404_NOT_FOUND, "La cotización no existe."),
    "PAGO_NO_APROBADO": (
        status.HTTP_409_CONFLICT,
        "El contrato se firma después de que el pago de la prima quede aprobado.",
    ),
    "COTIZACION_INCOMPLETA": (status.HTTP_409_CONFLICT, "La cotización no tiene cobertura."),
    "TITULAR_SIN_DATOS": (status.HTTP_409_CONFLICT, "Faltan los datos del titular."),
    "DESTINO_NO_DISPONIBLE": (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "No hay un destino registrado para ese canal. Elija otro canal.",
    ),
}

_MENSAJES_OTP = {
    "OTP_NO_EMITIDO": "Primero solicite el código de firma.",
    "OTP_INCORRECTO": "El código no es correcto.",
    "OTP_VENCIDO": "El código venció. Solicite uno nuevo.",
    "OTP_INTENTOS_AGOTADOS": "Agotó los intentos con este código. Solicite uno nuevo.",
}

_MENSAJES_REENVIO = {
    "ESPERA_REENVIO": "Espere unos segundos antes de pedir otro código.",
    "ENVIOS_AGOTADOS": "Ya se enviaron todos los códigos permitidos.",
    "YA_FIRMADO": "El contrato ya fue firmado.",
}


def _error(codigo_http: int, codigo: str, mensaje: str, proceso: ProcesoFirma | None = None):
    detalle: dict[str, object] = {"codigo": codigo, "mensaje": mensaje}
    if proceso is not None:
        detalle["intentos_restantes"] = proceso.intentos_restantes
        detalle["envios_restantes"] = proceso.envios_restantes
        disponible = proceso.reenvio_disponible_en()
        detalle["reenvio_disponible_en"] = disponible.isoformat() if disponible else None
    return HTTPException(codigo_http, detail=detalle)


def _no_disponible(error: FirmaNoDisponible) -> HTTPException:
    codigo_http, mensaje = _NO_DISPONIBLE[error.codigo]
    return _error(codigo_http, error.codigo, mensaje)


_BLOQUEADA = (
    status.HTTP_423_LOCKED,
    "FIRMA_BLOQUEADA",
    "El proceso de firma se bloqueó por intentos fallidos. Comuníquese con su asesor.",
)
_PROVEEDOR_CAIDO = (
    status.HTTP_503_SERVICE_UNAVAILABLE,
    "PROVEEDOR_FIRMA_NO_DISPONIBLE",
    "El servicio de firma no responde. Intente de nuevo en unos minutos.",
)


@router.get(
    "/{cotizacion_id}",
    response_model=RespuestaFirma,
    summary="Presenta el contrato prellenado de una cotización pagada",
    description=(
        "Disponible solo cuando el pago de la prima está APROBADO. La primera consulta arma "
        "el contrato con las condiciones particulares y fija su huella SHA-256; las "
        "siguientes devuelven el mismo documento."
    ),
)
def presentar_contrato(
    cotizacion_id: str,
    cliente_id: str = Depends(cliente_pagador),
    servicio: ServicioFirmas = Depends(obtener_servicio),
) -> RespuestaFirma:
    try:
        return RespuestaFirma.de(servicio.presentar(cliente_id, cotizacion_id))
    except FirmaNoDisponible as error:
        raise _no_disponible(error) from None


@router.post(
    "/{cotizacion_id}/otp",
    response_model=RespuestaFirma,
    summary="Envía el código OTP de firma por SMS o correo",
    description=(
        "El código vence a los 5 minutos y admite 3 intentos. Se permiten 3 envíos por "
        "proceso, con 30 segundos entre uno y otro."
    ),
)
def solicitar_otp(
    cotizacion_id: str,
    solicitud: SolicitudOtp,
    cliente_id: str = Depends(cliente_pagador),
    servicio: ServicioFirmas = Depends(obtener_servicio),
) -> RespuestaFirma:
    try:
        return RespuestaFirma.de(servicio.solicitar_otp(cliente_id, cotizacion_id, solicitud.canal))
    except FirmaNoDisponible as error:
        raise _no_disponible(error) from None
    except ReenvioNoPermitido as error:
        codigo_http = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if error.codigo == "ESPERA_REENVIO"
            else status.HTTP_409_CONFLICT
        )
        raise _error(
            codigo_http, error.codigo, _MENSAJES_REENVIO[error.codigo], error.proceso
        ) from None
    except FirmaBloqueada:
        raise _error(*_BLOQUEADA) from None
    except ProveedorFirmaNoDisponible:
        raise _error(*_PROVEEDOR_CAIDO) from None


@router.post(
    "/{cotizacion_id}/firma",
    response_model=RespuestaFirma,
    summary="Firma el contrato con el código OTP",
    description=(
        "El cliente envía el código y la huella del contrato que revisó. Si la huella no es "
        "la del contrato guardado, la firma se rechaza. Quedan registrados la fecha, la IP, "
        "el firmante, la huella y el sello del proveedor. Repetir la firma de un contrato ya "
        "firmado devuelve la firma existente."
    ),
)
def firmar_contrato(
    cotizacion_id: str,
    solicitud: SolicitudFirma,
    request: Request,
    cliente_id: str = Depends(cliente_pagador),
    servicio: ServicioFirmas = Depends(obtener_servicio),
) -> RespuestaFirma:
    try:
        proceso = servicio.firmar(
            cliente_id,
            cotizacion_id,
            solicitud.codigo,
            solicitud.huella_documento,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except FirmaNoEncontrada:
        raise _error(
            status.HTTP_404_NOT_FOUND, "FIRMA_NO_ENCONTRADA", "No hay contrato para firmar."
        ) from None
    except FirmaNoDisponible as error:
        raise _no_disponible(error) from None
    except DocumentoAlterado:
        raise _error(
            status.HTTP_409_CONFLICT,
            "DOCUMENTO_ALTERADO",
            "El contrato firmado no coincide con el contrato presentado.",
        ) from None
    except OtpRechazado as error:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error.codigo,
            _MENSAJES_OTP[error.codigo],
            error.proceso,
        ) from None
    except FirmaBloqueada:
        raise _error(*_BLOQUEADA) from None
    except ProveedorFirmaNoDisponible:
        raise _error(*_PROVEEDOR_CAIDO) from None
    return RespuestaFirma.de(proceso)

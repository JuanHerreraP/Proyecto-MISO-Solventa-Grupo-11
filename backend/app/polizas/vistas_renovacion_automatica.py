"""Lo que la API de renovación automática expone (HU17 / BPM-69).

Nunca incluye el token de la tarjeta: solo sus últimos cuatro dígitos, si el cliente los dio.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.pagos.modelos import validar_token_pago
from app.polizas.dominio.modelos import Poliza
from app.polizas.dominio.renovacion import RAMOS_RENOVABLES
from app.polizas.dominio.renovacion_automatica import (
    CicloRenovacionAutomatica,
    EstadoCicloRenovacion,
    MedioPagoRegistrado,
    PreferenciaRenovacionAutomatica,
    preaviso_desde,
)


class TarjetaRegistrada(BaseModel):
    ultimos_digitos: str | None


class CicloVista(BaseModel):
    """El último periodo que gestionó la renovación automática y en qué quedó."""

    vence_el: date
    estado: EstadoCicloRenovacion
    preaviso_enviado_en: datetime | None
    prima_avisada: Decimal | None
    moneda: str | None
    renovacion_id: str | None
    motivo: str | None
    documento_disponible: bool
    contrato_enviado_en: datetime | None


class RenovacionAutomaticaVista(BaseModel):
    poliza_id: str
    disponible: bool
    activa: bool
    tarjeta: TarjetaRegistrada | None
    vence_el: date
    preaviso_desde: date
    cobro_programado_para: date
    actualizado_en: datetime | None
    ultimo_ciclo: CicloVista | None


class TarjetaSolicitud(BaseModel):
    """Token de la pasarela (nunca el número de la tarjeta) y, opcional, sus últimos dígitos."""

    model_config = ConfigDict(extra="forbid")

    token_tarjeta: str = Field(min_length=8, max_length=200)
    ultimos_digitos: str | None = Field(default=None, pattern=r"^\d{4}$")

    _sin_pan = field_validator("token_tarjeta")(validar_token_pago)


class PreferenciaSolicitud(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activa: bool
    tarjeta: TarjetaSolicitud | None = None
    quitar_tarjeta: bool = False


def medio_de(solicitud: PreferenciaSolicitud) -> MedioPagoRegistrado | None:
    if solicitud.tarjeta is None:
        return None
    return MedioPagoRegistrado(
        token_tarjeta=solicitud.tarjeta.token_tarjeta,
        ultimos_digitos=solicitud.tarjeta.ultimos_digitos,
    )


def a_vista(
    poliza: Poliza,
    preferencia: PreferenciaRenovacionAutomatica,
    ciclo: CicloRenovacionAutomatica | None,
) -> RenovacionAutomaticaVista:
    medio = preferencia.medio_pago
    return RenovacionAutomaticaVista(
        poliza_id=poliza.poliza_id,
        disponible=poliza.ramo in RAMOS_RENOVABLES,
        activa=preferencia.activa,
        tarjeta=TarjetaRegistrada(ultimos_digitos=medio.ultimos_digitos) if medio else None,
        vence_el=poliza.fecha_fin,
        preaviso_desde=preaviso_desde(poliza),
        cobro_programado_para=poliza.fecha_fin,
        actualizado_en=preferencia.actualizado_en,
        ultimo_ciclo=_ciclo(ciclo) if ciclo else None,
    )


def _ciclo(ciclo: CicloRenovacionAutomatica) -> CicloVista:
    return CicloVista(
        vence_el=ciclo.vence_el,
        estado=ciclo.estado,
        preaviso_enviado_en=ciclo.preaviso_enviado_en,
        prima_avisada=ciclo.prima_avisada,
        moneda=ciclo.moneda,
        renovacion_id=ciclo.renovacion_id,
        motivo=ciclo.motivo,
        documento_disponible=ciclo.huella_documento is not None,
        contrato_enviado_en=ciclo.contrato_enviado_en,
    )

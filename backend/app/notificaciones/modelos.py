"""Modelos de las notificaciones al cliente (push y bandeja dentro de la app).

Todo evento importante (un pago paramétrico, un siniestro que cambia de estado, una póliza por
vencer) se **registra siempre** como notificación, y el cliente la consulta dentro de la app
aunque tenga el push deshabilitado. El push es un canal adicional que solo se manda si el
cliente lo tiene habilitado y registró un dispositivo.
"""

from datetime import date
from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class TipoNotificacion(str, Enum):
    PAGO_PARAMETRICO = "PAGO_PARAMETRICO"
    VENCIMIENTO_POLIZA = "VENCIMIENTO_POLIZA"
    ESTADO_SINIESTRO = "ESTADO_SINIESTRO"


class Notificacion(BaseModel):
    """Una notificación de la bandeja del cliente."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    notificacion_id: str = Field(min_length=1, max_length=60)
    cliente_id: str = Field(min_length=1, max_length=50)
    tipo: TipoNotificacion
    # Identifica el evento que la originó (p. ej. "SIN-1:APROBADO"): registrarlo dos veces no
    # duplica la notificación.
    clave: str = Field(min_length=1, max_length=150)
    titulo: str = Field(min_length=1, max_length=120)
    cuerpo: str = Field(min_length=1, max_length=400)
    # A dónde lleva al tocarla (poliza_id, siniestro_id…) y datos para mostrarla.
    datos: dict[str, str] = Field(default_factory=dict)
    # Día (hora de Bogotá) y tipo: los eventos de un mismo grupo se agrupan en el push.
    dia: date
    creada_en: AwareDatetime
    leida_en: AwareDatetime | None = None

    @property
    def grupo(self) -> str:
        return grupo_de(self.tipo, self.dia)

    @property
    def leida(self) -> bool:
        return self.leida_en is not None


def grupo_de(tipo: TipoNotificacion, dia: date) -> str:
    """Los eventos del mismo tipo y del mismo día pertenecen al mismo grupo."""
    return f"{tipo.value}:{dia.isoformat()}"


class DispositivoPush(BaseModel):
    """Un dispositivo del cliente al que se le puede mandar push (token de FCM)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dispositivo_id: str = Field(min_length=1, max_length=60)
    cliente_id: str = Field(min_length=1, max_length=50)
    token: str = Field(min_length=1, max_length=512)
    plataforma: str = Field(default="ANDROID", min_length=1, max_length=20)
    activo: bool = True
    registrado_en: AwareDatetime
    actualizado_en: AwareDatetime


class PreferenciaNotificacion(BaseModel):
    """Si el cliente quiere recibir push. Sin preferencia guardada, el push está habilitado."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cliente_id: str = Field(min_length=1, max_length=50)
    push_habilitado: bool = True
    actualizado_en: AwareDatetime


class MotivoSinPush(str, Enum):
    """Por qué una notificación quedó solo en la bandeja."""

    PUSH_DESHABILITADO = "PUSH_DESHABILITADO"
    SIN_DISPOSITIVOS = "SIN_DISPOSITIVOS"


class PushPendiente(BaseModel):
    """Lo que debe enviarse por push: lo decide el servicio y lo envía el canal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cliente_id: str
    tokens: tuple[str, ...]
    titulo: str
    cuerpo: str
    datos: dict[str, str]
    # Mismo `etiqueta` = el push nuevo reemplaza al anterior en el teléfono (FCM `tag`).
    etiqueta: str
    # Cuántos eventos del grupo van hasta ahora; más de uno significa push agrupado.
    total_del_grupo: int = Field(ge=1)

    @property
    def agrupado(self) -> bool:
        return self.total_del_grupo > 1


RESUMEN_AGRUPADO: dict[TipoNotificacion, tuple[str, str]] = {
    TipoNotificacion.PAGO_PARAMETRICO: (
        "Pagos de tu seguro paramétrico",
        "Tienes {n} pagos nuevos de tu seguro paramétrico hoy.",
    ),
    TipoNotificacion.VENCIMIENTO_POLIZA: (
        "Vencimiento de tus pólizas",
        "Tienes {n} pólizas próximas a vencer.",
    ),
    TipoNotificacion.ESTADO_SINIESTRO: (
        "Cambios en tus siniestros",
        "Tienes {n} actualizaciones en tus siniestros hoy.",
    ),
}


def resumen_de(tipo: TipoNotificacion, total: int) -> tuple[str, str]:
    """Título y cuerpo del push que reemplaza a los individuales cuando hay varios en el día."""
    titulo, cuerpo = RESUMEN_AGRUPADO[tipo]
    return titulo, cuerpo.format(n=total)

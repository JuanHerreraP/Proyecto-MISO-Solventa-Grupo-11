"""Los eventos que generan notificaciones (HU05) y sus mensajes.

Aquí vive el texto de cada notificación y a dónde lleva al tocarla, para que los disparadores
(la evaluación de siniestros, el job de vencimientos) no repitan redacción ni claves. Cada evento
tiene una `clave` estable: registrarlo dos veces no duplica la notificación.

Qué lleva cada `datos` (el destino de la app móvil):
- Pago paramétrico y estado del siniestro: `siniestro_id` abre el detalle del siniestro.
- Vencimiento: `poliza_id` abre el flujo de renovación.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.notificaciones.modelos import TipoNotificacion
from app.polizas.dominio.modelos import Poliza
from app.siniestros.modelos import EstadoSiniestro, Siniestro


@dataclass(frozen=True)
class EventoNotificacion:
    tipo: TipoNotificacion
    clave: str
    titulo: str
    cuerpo: str
    datos: dict[str, str]


def formatear_monto(monto: Decimal, moneda: str) -> str:
    """ "$150.000 COP", con punto de miles y coma decimal solo si hay centavos."""
    redondeado = monto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    entero, centavos = divmod(int(redondeado * 100), 100)
    texto = f"{entero:,}".replace(",", ".")
    if centavos:
        texto += f",{centavos:02d}"
    return f"${texto} {moneda}"


def _numero_poliza(siniestro: Siniestro, poliza: Poliza | None) -> str:
    return poliza.numero_poliza if poliza is not None else siniestro.poliza_id


def _datos_siniestro(siniestro: Siniestro, poliza: Poliza | None) -> dict[str, str]:
    return {
        "siniestro_id": siniestro.siniestro_id,
        "poliza_id": siniestro.poliza_id,
        "numero_poliza": _numero_poliza(siniestro, poliza),
        "estado": siniestro.estado.value,
    }


def pago_parametrico(siniestro: Siniestro, poliza: Poliza | None) -> EventoNotificacion:
    """Se aprobó el pago de un seguro paramétrico (criterio 1): lleva el monto y la póliza."""
    monto = siniestro.monto_aprobado or siniestro.estimacion_danos
    numero = _numero_poliza(siniestro, poliza)
    return EventoNotificacion(
        tipo=TipoNotificacion.PAGO_PARAMETRICO,
        clave=f"PAGO_PARAMETRICO:{siniestro.siniestro_id}",
        titulo="Aprobamos el pago de tu seguro paramétrico",
        cuerpo=f"Se aprobó un pago de {formatear_monto(monto, siniestro.moneda)} "
        f"por tu póliza {numero}.",
        datos={
            **_datos_siniestro(siniestro, poliza),
            "monto": str(monto),
            "moneda": siniestro.moneda,
        },
    )


def estado_siniestro(siniestro: Siniestro, poliza: Poliza | None) -> EventoNotificacion:
    """Un siniestro cambió de estado (criterio 3): al tocarla se abre su detalle."""
    numero = _numero_poliza(siniestro, poliza)
    if siniestro.estado is EstadoSiniestro.APROBADO:
        monto = siniestro.monto_aprobado
        por = f" por {formatear_monto(monto, siniestro.moneda)}" if monto else ""
        titulo = "Tu siniestro fue aprobado"
        cuerpo = f"Aprobamos tu siniestro de la póliza {numero}{por}."
    elif siniestro.estado is EstadoSiniestro.RECHAZADO:
        titulo = "Tu siniestro fue rechazado"
        cuerpo = (
            f"Revisamos tu siniestro de la póliza {numero} y no pudimos aprobarlo. "
            "Consulta el detalle para ver el motivo."
        )
    else:
        titulo = "Tu siniestro cambió de estado"
        cuerpo = f"Tu siniestro de la póliza {numero} ahora está en {siniestro.estado.value}."
    return EventoNotificacion(
        tipo=TipoNotificacion.ESTADO_SINIESTRO,
        clave=f"ESTADO_SINIESTRO:{siniestro.siniestro_id}:{siniestro.estado.value}",
        titulo=titulo,
        cuerpo=cuerpo,
        datos=_datos_siniestro(siniestro, poliza),
    )


def vencimiento_poliza(poliza: Poliza, dias: int) -> EventoNotificacion:
    """La póliza vence en `dias` días (criterio 2): al tocarla se abre la renovación."""
    cuando = "mañana" if dias == 1 else f"en {dias} días"
    return EventoNotificacion(
        tipo=TipoNotificacion.VENCIMIENTO_POLIZA,
        # Una por póliza, por fecha de fin (una renovación la cambia) y por aviso (15 o 3 días).
        clave=f"VENCIMIENTO:{poliza.poliza_id}:{poliza.fecha_fin.isoformat()}:{dias}",
        titulo="Tu póliza está por vencer",
        cuerpo=f"Tu póliza {poliza.numero_poliza} vence {cuando}. "
        "Renuévala para mantener tu cobertura.",
        datos={
            "poliza_id": poliza.poliza_id,
            "numero_poliza": poliza.numero_poliza,
            "dias": str(dias),
            "fecha_fin": poliza.fecha_fin.isoformat(),
        },
    )

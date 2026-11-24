"""Evento que Siniestros publica al aprobar un siniestro paramétrico.

El identificador se deriva del siniestro: publicar dos veces el mismo hecho (un reintento, o el
barrido de pendientes) produce el mismo evento, y el consumidor de pagos lo reconoce como
repetido en lugar de pagar dos veces.
"""

from app.eventos.modelos import EventoNegocio, TipoEvento
from app.siniestros.modelos import Siniestro


def evento_pago_parametrico(siniestro: Siniestro) -> EventoNegocio:
    return EventoNegocio(
        evento_id=f"PAGO_PARAMETRICO:{siniestro.siniestro_id}",
        tipo=TipoEvento.SINIESTRO_PARAMETRICO_APROBADO,
        ocurrido_en=siniestro.evaluado_en or siniestro.registrado_en,
        datos={
            "siniestro_id": siniestro.siniestro_id,
            "cliente_id": siniestro.cliente_id,
            "poliza_id": siniestro.poliza_id,
            "monto_aprobado": str(siniestro.monto_aprobado or ""),
            "moneda": siniestro.moneda,
        },
    )

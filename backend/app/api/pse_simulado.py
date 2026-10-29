"""Portal PSE simulado para desarrollo (sustituye al portal real del banco).

No es parte del dominio de pagos: imita el comportamiento externo de PSE. Sirve una
página HTML con botones "Pagar" y "Rechazar" y, al elegir, firma internamente la
confirmación (el secreto vive en el backend, nunca en el navegador) y la entrega al
mismo servicio que usaría la pasarela real por el webhook.
"""

import html
import json
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.pagos import obtener_servicio
from app.pagos.modelos import EstadoPago
from app.pagos.servicio import (
    FirmaInvalida,
    PagoNoEncontrado,
    ServicioPagos,
    firmar,
    secreto_webhook,
)

router = APIRouter(prefix="/api/v1/pagos/pse-simulado", tags=["pse-simulado"])


def _enlace_resolver(referencia: str, decision: str, url_retorno: str | None) -> str:
    parametros = {"referencia": referencia, "decision": decision}
    if url_retorno:
        parametros["url_retorno"] = url_retorno
    return "resolver?" + urlencode(parametros)


def _pagina(referencia: str, monto: str | None, url_retorno: str | None) -> str:
    detalle_monto = (
        f'<p class="monto">Total a pagar: <strong>{html.escape(monto)}</strong></p>'
        if monto
        else ""
    )
    href_pagar = html.escape(_enlace_resolver(referencia, "APROBADO", url_retorno))
    href_rechazar = html.escape(_enlace_resolver(referencia, "RECHAZADO", url_retorno))
    ref = html.escape(referencia)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PSE · Pago simulado</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background: #eef2f8; margin: 0;
           display: grid; place-items: center; min-height: 100vh; }}
    .tarjeta {{ background: #fff; border-radius: 14px;
               box-shadow: 0 10px 30px rgba(16,27,50,.12); padding: 32px; width: 360px; }}
    .marca {{ display: flex; align-items: center; gap: 10px; color: #c0392b;
             font-weight: 800; font-size: 20px; margin-bottom: 8px; }}
    h1 {{ font-size: 18px; margin: 0 0 4px; }}
    p {{ color: #5a6578; font-size: 14px; }}
    .monto {{ color: #101b32; }}
    .ref {{ font-size: 12px; color: #8a93a6; word-break: break-all; }}
    .acciones {{ display: flex; gap: 10px; margin-top: 20px; }}
    a.boton {{ flex: 1; padding: 12px; border-radius: 10px; font-weight: 700;
              font-size: 14px; text-align: center; text-decoration: none; }}
    .pagar {{ background: #1b8a4a; color: #fff; }}
    .rechazar {{ background: #fff; color: #c0392b; border: 1px solid #e3b3ad; }}
  </style>
</head>
<body>
  <div class="tarjeta">
    <div class="marca">🏦 PSE</div>
    <h1>Confirma tu débito bancario</h1>
    <p>Estás en el portal simulado de tu banco. Confirma o rechaza el pago
       para volver a Solventa.</p>
    {detalle_monto}
    <p class="ref">Referencia: {ref}</p>
    <div class="acciones">
      <a class="boton pagar" href="{href_pagar}">Pagar</a>
      <a class="boton rechazar" href="{href_rechazar}">Rechazar</a>
    </div>
  </div>
</body>
</html>"""


@router.get(
    "/resolver",
    summary="Aplica la decisión del portal PSE simulado y redirige de vuelta a la app",
)
def resolver_pse(
    referencia: str,
    decision: EstadoPago,
    url_retorno: str | None = None,
    servicio: ServicioPagos = Depends(obtener_servicio),
):
    cuerpo = json.dumps({"referencia": referencia, "estado": decision.value}).encode()
    firma = firmar(cuerpo, secreto_webhook())
    try:
        pago = servicio.confirmar(cuerpo, firma, referencia, decision, None)
    except FirmaInvalida:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Error de firma interna."
        ) from None
    except PagoNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Referencia de pago desconocida.") from None

    if url_retorno:
        separador = "&" if "?" in url_retorno else "?"
        destino = f"{url_retorno}{separador}pago={pago.pago_id}&estado={pago.estado.value}"
        return RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)
    return {"pago_id": pago.pago_id, "estado": pago.estado.value}


@router.get(
    "/{referencia}",
    response_class=HTMLResponse,
    summary="Página simulada del portal PSE (desarrollo)",
)
def portal_pse(
    referencia: str,
    url_retorno: str | None = None,
    servicio: ServicioPagos = Depends(obtener_servicio),
) -> HTMLResponse:
    try:
        pago = servicio.consultar_por_referencia(referencia)
    except PagoNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Referencia de pago desconocida.") from None
    monto = f"{pago.monto} {pago.moneda}"
    return HTMLResponse(_pagina(referencia, monto, url_retorno))

"""API de la billetera digital de pólizas para la app Android (HU07 / BPM-31)."""

import os
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.seguridad import requiere_roles
from app.identidad.modelos import Rol
from app.infraestructura.database import get_db
from app.polizas.repositorio import RepositorioEnlacesPostgres, RepositorioPolizasPostgres
from app.polizas.servicio import (
    RUTA_CERTIFICADO_COMPARTIDO,
    EnlaceNoEncontrado,
    EnlaceVencido,
    PolizaNoEncontrada,
    ServicioBilletera,
)
from app.polizas.vistas import Billetera, CertificadoCompartido, CertificadoPoliza, EnlaceCompartido

router = APIRouter(prefix="/api/v1/billetera", tags=["billetera"])
router_publico = APIRouter(prefix=RUTA_CERTIFICADO_COMPARTIDO, tags=["billetera"])

cliente_actual = requiere_roles(Rol.CLIENTE)

POLIZA_NO_ENCONTRADA = {
    "codigo": "POLIZA_NO_ENCONTRADA",
    "mensaje": "No encontramos esa póliza en tu billetera.",
}


def obtener_servicio(db: Session = Depends(get_db)) -> ServicioBilletera:
    return ServicioBilletera(RepositorioPolizasPostgres(db), RepositorioEnlacesPostgres(db))


def _sin_cache(respuesta: Response) -> None:
    respuesta.headers["Cache-Control"] = "no-store"
    respuesta.headers["Pragma"] = "no-cache"


def url_publica(request: Request) -> str:
    """Detrás del API Gateway la URL interna no sirve para compartir; se configura aparte."""
    return os.getenv("SOLVENTA_URL_PUBLICA") or str(request.base_url)


@router.get(
    "/polizas",
    response_model=Billetera,
    summary="Lista las pólizas del cliente autenticado, vigentes primero",
)
def consultar_billetera(
    respuesta: Response,
    usuario=Depends(cliente_actual),
    servicio: ServicioBilletera = Depends(obtener_servicio),
) -> Billetera:
    _sin_cache(respuesta)
    return servicio.billetera(str(usuario.id))


@router.get(
    "/polizas/{poliza_id}/certificado",
    response_model=CertificadoPoliza,
    summary="Certificado digital de una póliza del cliente, con el contenido de su QR",
)
def consultar_certificado(
    poliza_id: str,
    respuesta: Response,
    usuario=Depends(cliente_actual),
    servicio: ServicioBilletera = Depends(obtener_servicio),
) -> CertificadoPoliza:
    _sin_cache(respuesta)
    try:
        return servicio.certificado(str(usuario.id), poliza_id)
    except PolizaNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, POLIZA_NO_ENCONTRADA) from None


@router.post(
    "/polizas/{poliza_id}/enlaces",
    response_model=EnlaceCompartido,
    status_code=status.HTTP_201_CREATED,
    summary="Genera un enlace temporal para compartir el certificado",
)
def compartir_certificado(
    poliza_id: str,
    request: Request,
    respuesta: Response,
    usuario=Depends(cliente_actual),
    servicio: ServicioBilletera = Depends(obtener_servicio),
) -> EnlaceCompartido:
    _sin_cache(respuesta)
    try:
        return servicio.compartir(str(usuario.id), poliza_id, url_publica(request))
    except PolizaNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, POLIZA_NO_ENCONTRADA) from None


@router_publico.get(
    "/{token}",
    response_model=CertificadoCompartido,
    summary="Certificado compartido; no requiere sesión mientras el enlace esté vigente",
    responses={410: {"description": "El enlace venció"}},
)
def ver_certificado_compartido(
    token: str,
    request: Request,
    servicio: ServicioBilletera = Depends(obtener_servicio),
):
    try:
        certificado = servicio.certificado_compartido(token)
    except EnlaceNoEncontrado:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            {"codigo": "ENLACE_NO_ENCONTRADO", "mensaje": "El enlace no existe."},
        ) from None
    except EnlaceVencido:
        raise HTTPException(
            status.HTTP_410_GONE,
            {"codigo": "ENLACE_VENCIDO", "mensaje": "El enlace para ver este certificado venció."},
        ) from None

    encabezados = {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        "X-Robots-Tag": "noindex, nofollow",
        "Referrer-Policy": "no-referrer",
    }
    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(pagina_certificado(certificado), headers=encabezados)
    return Response(
        content=certificado.model_dump_json(),
        media_type="application/json",
        headers=encabezados,
    )


def pagina_certificado(c: CertificadoCompartido) -> str:
    """Vista mínima para quien abre el enlace desde un navegador. Todo se escapa."""
    estado = "Vigente" if c.activa else c.estado.value.capitalize()
    filas = [
        ("Póliza", c.numero_poliza),
        ("Seguro", c.nombre_ramo),
        ("Estado", estado),
        ("Titular", c.titular),
        ("Documento", c.documento_titular),
        ("Vigencia", f"{c.fecha_inicio:%d/%m/%Y} al {c.fecha_fin:%d/%m/%Y}"),
        ("Cobertura principal", c.cobertura_principal),
        ("Suma asegurada", f"{c.moneda} {c.suma_asegurada:,.2f}"),
    ]
    cuerpo = "".join(f"<dt>{escape(k)}</dt><dd>{escape(str(v))}</dd>" for k, v in filas)
    vence = f"{c.enlace_expira_en:%d/%m/%Y %H:%M} UTC"
    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Certificado de póliza · Solventa</title>"
        "<style>body{font-family:system-ui,sans-serif;max-width:32rem;margin:2rem auto;"
        "padding:0 1rem;color:#1b2430}h1{font-size:1.4rem}dt{font-weight:600;margin-top:.8rem}"
        "dd{margin:0}.nota{margin-top:1.5rem;font-size:.85rem;color:#5b6573}</style></head>"
        f"<body><h1>Certificado de póliza</h1><dl>{cuerpo}</dl>"
        f"<p class='nota'>Este enlace temporal vence el {escape(vence)}.</p></body></html>"
    )

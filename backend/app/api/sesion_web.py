"""Sesión web: refresh en cookie HttpOnly, access en memoria y CSRF explícito."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import autenticacion
from app.identidad.modelos import RespuestaLogin, SolicitudLogin, SolicitudRefresh
from app.identidad.web import nombre_cookie, opciones_cookie, origenes_web
from app.infraestructura.database import get_db

router = APIRouter(prefix="/api/v1/auth/web", tags=["Sesión web"])


class SesionWeb(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    csrf_token: str


class TokenCSRF(BaseModel):
    csrf_token: str


def validar_origen(request: Request, obligatorio: bool = True) -> None:
    origen = request.headers.get("origin")
    if (obligatorio and not origen) or (origen is not None and origen not in origenes_web()):
        raise HTTPException(
            403, detail={"codigo": "CSRF_REJECTED", "mensaje": "Origen no permitido."}
        )
    if request.headers.get("sec-fetch-site") == "cross-site" and not origen:
        raise HTTPException(403, detail={"codigo": "CSRF_REJECTED", "mensaje": "Origen requerido."})


def validar_csrf(request: Request) -> str:
    validar_origen(request)
    cookie = request.cookies.get(nombre_cookie("csrf"), "")
    cabecera = request.headers.get("x-csrf-token", "")
    if not cookie or not cabecera or not secrets.compare_digest(cookie.encode(), cabecera.encode()):
        raise HTTPException(
            403,
            detail={"codigo": "CSRF_REJECTED", "mensaje": "Validación CSRF requerida."},
        )
    return cookie


def borrar_cookies(response: Response) -> None:
    for tipo in ("refresh", "csrf"):
        response.delete_cookie(nombre_cookie(tipo), **opciones_cookie())


def respuesta_error(error: HTTPException) -> Response:
    response = JSONResponse(
        {"detail": error.detail}, status_code=error.status_code, headers=error.headers
    )
    borrar_cookies(response)
    return response


def establecer_sesion(response: Response, sesion: RespuestaLogin, csrf: str) -> SesionWeb:
    response.set_cookie(
        nombre_cookie("refresh"),
        sesion.refresh_token,
        max_age=sesion.refresh_expires_in,
        **opciones_cookie(),
    )
    response.set_cookie(
        nombre_cookie("csrf"), csrf, max_age=sesion.refresh_expires_in, **opciones_cookie()
    )
    return SesionWeb(
        access_token=sesion.access_token,
        token_type=sesion.token_type,
        expires_in=sesion.expires_in,
        csrf_token=csrf,
    )


@router.get("/csrf", response_model=TokenCSRF)
def obtener_csrf(request: Request, response: Response) -> TokenCSRF:
    # Solo lectura de la sesión: obtener el reto CSRF no prolonga la inactividad.
    validar_origen(request, obligatorio=False)
    csrf = request.cookies.get(nombre_cookie("csrf")) or secrets.token_urlsafe(32)
    response.set_cookie(nombre_cookie("csrf"), csrf, max_age=7 * 86400, **opciones_cookie())
    return TokenCSRF(csrf_token=csrf)


@router.post("/login", response_model=SesionWeb)
def login_web(
    solicitud: SolicitudLogin,
    request: Request,
    response: Response,
    _csrf: str = Depends(validar_csrf),
    db: Session = Depends(get_db),
):
    sesion = autenticacion.login(solicitud, request, db)
    anterior = request.cookies.get(nombre_cookie("refresh"))
    if anterior:
        try:
            autenticacion.cerrar_sesion(SolicitudRefresh(refresh_token=anterior), request, db)
        except HTTPException:
            pass  # Una cookie anterior inválida no impide un login con credenciales válidas.
    return establecer_sesion(response, sesion, secrets.token_urlsafe(32))


@router.post("/refresh", response_model=SesionWeb)
def refresh_web(
    request: Request,
    response: Response,
    csrf: str = Depends(validar_csrf),
    db: Session = Depends(get_db),
):
    token = request.cookies.get(nombre_cookie("refresh"))
    if not token:
        return respuesta_error(
            HTTPException(401, detail={"codigo": "SESSION_REQUIRED", "mensaje": "Inicie sesión."})
        )
    try:
        sesion = autenticacion.renovar_sesion(SolicitudRefresh(refresh_token=token), request, db)
    except HTTPException as error:
        return respuesta_error(error)
    return establecer_sesion(response, sesion, csrf)


@router.post("/logout", status_code=204, response_class=Response)
def logout_web(
    request: Request,
    _csrf: str = Depends(validar_csrf),
    db: Session = Depends(get_db),
):
    token = request.cookies.get(nombre_cookie("refresh"))
    if token:
        try:
            autenticacion.cerrar_sesion(SolicitudRefresh(refresh_token=token), request, db)
        except HTTPException as error:
            return respuesta_error(error)
    response = Response(status_code=204)
    borrar_cookies(response)
    return response

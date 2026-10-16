"""Configuración de orígenes y cookies de la sesión del navegador."""

import os
from urllib.parse import urlsplit


def origenes_web() -> list[str]:
    valores = os.getenv("WEB_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(
        ","
    )
    origenes = [valor.strip().rstrip("/") for valor in valores if valor.strip()]
    if not origenes:
        raise ValueError("WEB_ALLOWED_ORIGINS requiere al menos un origen explícito.")
    for origen in origenes:
        url = urlsplit(origen)
        if (
            url.scheme not in {"http", "https"}
            or not url.netloc
            or url.path
            or url.query
            or url.fragment
            or url.username
            or "*" in origen
        ):
            raise ValueError("WEB_ALLOWED_ORIGINS solo admite orígenes HTTP(S) explícitos.")
    return origenes


def opciones_cookie() -> dict:
    valor_seguro = os.getenv("WEB_COOKIE_SECURE", "true").lower()
    if valor_seguro not in {"true", "false"}:
        raise ValueError("WEB_COOKIE_SECURE debe ser true o false.")
    seguro = valor_seguro == "true"
    if os.getenv("APP_ENV", "development").lower() in {"production", "prod"} and not seguro:
        raise ValueError("Las cookies deben ser Secure en producción.")
    same_site = os.getenv("WEB_COOKIE_SAMESITE", "lax").lower()
    if same_site not in {"lax", "strict", "none"}:
        raise ValueError("WEB_COOKIE_SAMESITE debe ser lax, strict o none.")
    if same_site == "none" and not seguro:
        raise ValueError("SameSite=None requiere cookies Secure.")
    return {"secure": seguro, "httponly": True, "samesite": same_site, "path": "/"}


def nombre_cookie(tipo: str) -> str:
    prefijo = "__Host-" if opciones_cookie()["secure"] else ""
    return f"{prefijo}solventa_{tipo}"

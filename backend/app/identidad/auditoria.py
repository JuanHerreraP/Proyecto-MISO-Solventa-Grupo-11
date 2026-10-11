"""Registro de eventos de autenticación y autorización."""

import logging
from enum import Enum
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError

from app.identidad.modelos_db import EventoAutenticacionDB
from app.infraestructura.database import SessionLocal


logger = logging.getLogger(__name__)


class TipoEventoAuth(str, Enum):
    USER_REGISTERED = "USER_REGISTERED"
    REGISTRATION_REJECTED = "REGISTRATION_REJECTED"

    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"

    TOKEN_REQUIRED = "TOKEN_REQUIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_REFRESHED = "TOKEN_REFRESHED"

    ACCESS_DENIED = "ACCESS_DENIED"


def registrar_evento_auth(
    tipo_evento: TipoEventoAuth,
    exitoso: bool,
    usuario_id: str | UUID | None = None,
    email: str | None = None,
    detalle: str | None = None,
    request: Request | None = None,
) -> None:

    db = SessionLocal()

    try:
        ip = None
        user_agent = None

        if request is not None:
            if request.client is not None:
                ip = request.client.host

            user_agent = request.headers.get(
                "user-agent"
            )

        usuario_uuid = None

        if usuario_id:
            try:
                usuario_uuid = UUID(
                    str(usuario_id)
                )
            except ValueError:
                usuario_uuid = None

        evento = EventoAutenticacionDB(
            usuario_id=usuario_uuid,
            email=(
                email.strip().lower()
                if email
                else None
            ),
            tipo_evento=tipo_evento.value,
            exitoso=exitoso,
            detalle=detalle,
            ip=ip,
            user_agent=user_agent,
        )

        db.add(evento)
        db.commit()

    except SQLAlchemyError:
        db.rollback()

        # La auditoría no debe tumbar
        # el flujo principal.
        logger.exception(
            "No fue posible registrar "
            "el evento de auditoría."
        )

    finally:
        db.close()
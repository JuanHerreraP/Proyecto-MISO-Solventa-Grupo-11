"""Creación automática del usuario manager (SERVICIO_INTERNO) al arranque.

El equipo necesita un manager de bootstrap para poder crear, a su vez, usuarios con
otros roles (por ejemplo ASESOR_VENTAS) desde el endpoint protegido
`POST /api/v1/auth/users`. Antes esto dependía de ejecutar `crear_admin.py` como tarea
puntual; al fallar ese paso no había ningún SERVICIO_INTERNO y el flujo quedaba bloqueado.

Esta función se ejecuta en `crear_app()`. Es idempotente: si el manager ya existe, lo
reactiva y le asegura el rol sin duplicarlo. Las credenciales se leen de variables de
entorno con valores por defecto pensados solo para desarrollo local.

Variables de entorno:
    BOOTSTRAP_MANAGER         "1"/"true" para habilitarlo. Por defecto habilitado.
    BOOTSTRAP_MANAGER_EMAIL   Correo del manager. Por defecto "manager@solventa.com".
    BOOTSTRAP_MANAGER_PASSWORD Contraseña en texto plano; se hashea. Por defecto "Manager123!".
    BOOTSTRAP_MANAGER_NOMBRE  Nombre. Por defecto "Manager".
    BOOTSTRAP_MANAGER_APELLIDO Apellido. Por defecto "Solventa".
"""

import logging
import os
from datetime import date

from pwdlib import PasswordHash
from sqlalchemy import select

from app.identidad.modelos import Rol
from app.identidad.modelos_db import UsuarioDB
from app.infraestructura.database import SessionLocal

logger = logging.getLogger(__name__)

EMAIL_POR_DEFECTO = "manager@solventa.com"
PASSWORD_POR_DEFECTO = "Manager123!"


def _habilitado() -> bool:
    valor = os.getenv("BOOTSTRAP_MANAGER", "1").strip().lower()
    return valor in {"1", "true", "yes", "on", "si", "sí"}


def asegurar_manager_bootstrap() -> None:
    """Crea o reactiva el manager de bootstrap. No propaga errores al arranque.

    Un fallo aquí (por ejemplo, la base todavía no lista) no debe impedir que la API
    levante; se registra y se continúa. El esquema ya se preparó antes de llamarla.
    """
    if not _habilitado():
        logger.info("Bootstrap del manager deshabilitado por configuración.")
        return

    email = os.getenv("BOOTSTRAP_MANAGER_EMAIL", EMAIL_POR_DEFECTO).strip().lower()
    password = os.getenv("BOOTSTRAP_MANAGER_PASSWORD", PASSWORD_POR_DEFECTO)
    nombre = os.getenv("BOOTSTRAP_MANAGER_NOMBRE", "Manager")
    apellido = os.getenv("BOOTSTRAP_MANAGER_APELLIDO", "Solventa")

    hasher = PasswordHash.recommended()
    db = SessionLocal()
    try:
        existente = db.scalar(select(UsuarioDB).where(UsuarioDB.email == email))
        if existente is not None:
            # Idempotente: asegura rol y estado sin tocar la contraseña de un manager ya usado.
            cambios = False
            if existente.rol != Rol.SERVICIO_INTERNO.value:
                existente.rol = Rol.SERVICIO_INTERNO.value
                cambios = True
            if not existente.activo:
                existente.activo = True
                cambios = True
            if cambios:
                db.commit()
                logger.info("Manager de bootstrap actualizado: %s", email)
            else:
                logger.info("Manager de bootstrap ya existe: %s", email)
            return

        usuario = UsuarioDB(
            nombre=nombre,
            apellido=apellido,
            email=email,
            password_hash=hasher.hash(password),
            rol=Rol.SERVICIO_INTERNO.value,
            activo=True,
            tipo_documento="ADMIN",
            numero_documento=f"ADMIN-{email}",
            fecha_nacimiento=date(1970, 1, 1),
            celular=None,
            kyc_validado=True,
            referencia_kyc="bootstrap-manager",
            consentimiento_kyc=True,
        )
        db.add(usuario)
        db.commit()
        logger.info("Manager de bootstrap creado con rol SERVICIO_INTERNO: %s", email)
    except Exception:  # noqa: BLE001 - el arranque no debe caer por el bootstrap.
        db.rollback()
        logger.exception("No fue posible asegurar el manager de bootstrap.")
    finally:
        db.close()

"""Crea (o reactiva) un usuario administrativo de bootstrap.

Pensado para ejecutarse como tarea puntual de ECS (RunTask con command override),
en la misma red y con las mismas credenciales de RDS que el backend. Reutiliza el
mismo hashing (`pwdlib.PasswordHash.recommended()`) y el mismo repositorio que la
API, de modo que el usuario creado puede iniciar sesión de forma normal.

Salta la verificación KYC porque un administrador interno no se registra por el
flujo público de clientes. No debe exponerse como endpoint ni dejarse accesible.

Variables de entorno:
    ADMIN_EMAIL     Correo del administrador (obligatorio).
    ADMIN_PASSWORD  Contraseña en texto plano; se hashea antes de guardar (obligatorio).
    ADMIN_ROL       Rol a asignar. Por defecto SERVICIO_INTERNO.
    ADMIN_NOMBRE    Nombre. Por defecto "Admin".
    ADMIN_APELLIDO  Apellido. Por defecto "Solventa".

El entrypoint ya construye DATABASE_URL a partir de DB_HOST/DB_PASSWORD, pero este
script también lo hace por si se invoca directamente, para no depender del orden.
"""

import os
import sys
from datetime import date
from urllib.parse import quote


def _asegurar_database_url() -> None:
    if os.environ.get("DATABASE_URL"):
        return
    if not os.environ.get("DB_HOST"):
        return
    usuario = quote(os.environ.get("DB_USER", "solventa"), safe="")
    password = quote(os.environ.get("DB_PASSWORD", ""), safe="")
    os.environ["DATABASE_URL"] = (
        f"postgresql+psycopg://{usuario}:{password}@{os.environ['DB_HOST']}"
        ":5432/solventa?sslmode=require"
    )


def main() -> int:
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        print("ERROR: ADMIN_EMAIL y ADMIN_PASSWORD son obligatorios.", file=sys.stderr)
        return 2

    _asegurar_database_url()

    from pwdlib import PasswordHash

    from app.identidad.modelos import Rol
    from app.identidad.modelos_db import UsuarioDB
    from app.infraestructura.database import (
        Base,
        SessionLocal,
        engine,
        esperar_base_disponible,
    )

    rol_texto = os.environ.get("ADMIN_ROL", Rol.SERVICIO_INTERNO.value)
    try:
        rol = Rol(rol_texto)
    except ValueError:
        validos = ", ".join(r.value for r in Rol)
        print(f"ERROR: rol invalido '{rol_texto}'. Validos: {validos}", file=sys.stderr)
        return 2

    esperar_base_disponible()
    Base.metadata.create_all(bind=engine)

    hasher = PasswordHash.recommended()
    email_normalizado = email.strip().lower()

    db = SessionLocal()
    try:
        from sqlalchemy import select

        existente = db.scalar(select(UsuarioDB).where(UsuarioDB.email == email_normalizado))
        if existente is not None:
            # Idempotente: reactiva, asegura el rol y actualiza la contraseña.
            existente.rol = rol.value
            existente.activo = True
            existente.password_hash = hasher.hash(password)
            db.commit()
            print(
                f"Usuario ya existia; actualizado a rol {rol.value} "
                f"y reactivado: {email_normalizado}"
            )
            return 0

        usuario = UsuarioDB(
            nombre=os.environ.get("ADMIN_NOMBRE", "Admin"),
            apellido=os.environ.get("ADMIN_APELLIDO", "Solventa"),
            email=email_normalizado,
            password_hash=hasher.hash(password),
            rol=rol.value,
            activo=True,
            tipo_documento="ADMIN",
            numero_documento=f"ADMIN-{email_normalizado}",
            fecha_nacimiento=date(1970, 1, 1),
            celular=None,
            kyc_validado=True,
            referencia_kyc="bootstrap-admin",
            consentimiento_kyc=True,
        )
        db.add(usuario)
        db.commit()
        print(f"Administrador creado con rol {rol.value}: {email_normalizado}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

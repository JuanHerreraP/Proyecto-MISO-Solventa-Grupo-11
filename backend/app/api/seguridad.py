from types import SimpleNamespace

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.identidad.auditoria import TipoEventoAuth, registrar_evento_auth
from app.identidad.modelos import Rol
from app.identidad.repositorio import RepositorioSesionesPostgres, RepositorioUsuariosPostgres
from app.identidad.tokens import TokenExpiradoError, TokenInvalidoError, validar_access_token
from app.infraestructura.database import get_db

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    if credentials is None:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.TOKEN_REQUIRED,
            exitoso=False,
            detalle="TOKEN_REQUIRED",
            request=request,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "codigo": "TOKEN_REQUIRED",
                "mensaje": "Se requiere autenticación.",
            },
        )

    try:
        payload = validar_access_token(credentials.credentials)
    except TokenExpiradoError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.TOKEN_EXPIRED,
            exitoso=False,
            detalle="TOKEN_EXPIRED",
            request=request,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "codigo": "TOKEN_EXPIRED",
                "mensaje": str(error),
            },
        ) from error
    except TokenInvalidoError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.TOKEN_INVALID,
            exitoso=False,
            detalle="TOKEN_INVALID",
            request=request,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "codigo": "TOKEN_INVALID",
                "mensaje": str(error),
            },
        ) from error

    repositorio = RepositorioUsuariosPostgres(db)
    try:
        usuario = repositorio.buscar_por_id(payload["sub"])
    except (ValueError, TypeError, AttributeError):
        usuario = None

    if usuario is None:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.ACCESS_DENIED,
            exitoso=False,
            usuario_id=payload.get("sub"),
            email=payload.get("email"),
            detalle="USER_NOT_FOUND",
            request=request,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "codigo": "USER_NOT_FOUND",
                "mensaje": "El usuario asociado al token no existe.",
            },
        )

    request.state.usuario_autenticado = SimpleNamespace(
        id=usuario.id, email=usuario.email, rol=usuario.rol,
    )

    if not usuario.activo:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.ACCESS_DENIED,
            exitoso=False,
            usuario_id=usuario.id,
            email=usuario.email,
            detalle="USER_INACTIVE",
            request=request,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "USER_INACTIVE",
                "mensaje": "El usuario se encuentra inactivo.",
            },
        )

    if payload.get("sid") and not RepositorioSesionesPostgres(db).registrar_actividad(
        payload["sid"],
        str(usuario.id),
    ):
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.ACCESS_DENIED,
            exitoso=False,
            usuario_id=usuario.id,
            detalle="SESSION_EXPIRED_OR_REVOKED",
            request=request,
        )
        raise HTTPException(
            status_code=401,
            detail={"codigo": "SESSION_EXPIRED", "mensaje": "La sesión expiró. Inicie sesión."},
        )
    return usuario


def requiere_roles(*roles_permitidos: str):
    def verificar(
        request: Request,
        usuario=Depends(get_current_user),
    ):
        if usuario.rol not in roles_permitidos:
            registrar_evento_auth(
                tipo_evento=TipoEventoAuth.ACCESS_DENIED,
                exitoso=False,
                usuario_id=usuario.id,
                email=usuario.email,
                detalle=f"ROLE_DENIED:{usuario.rol}",
                request=request,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "codigo": "ACCESS_DENIED",
                    "mensaje": "El usuario no tiene permisos para realizar esta operación.",
                },
            )

        return usuario

    return verificar


def rol_actual(
    usuario=Depends(get_current_user),
) -> Rol:
    try:
        return Rol(usuario.rol)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "ROLE_INVALID",
                "mensaje": "El usuario tiene un rol no reconocido.",
            },
        ) from error


def verificar_propietario(cliente_id: str, usuario) -> None:
    """El cliente asegurado solo puede operar sobre su propio identificador."""
    if usuario.rol == Rol.CLIENTE and str(usuario.id) != cliente_id:
        raise HTTPException(
            status_code=403,
            detail={"codigo": "ACCESS_DENIED", "mensaje": "No tiene acceso a este cliente."},
        )

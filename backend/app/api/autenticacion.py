"""Endpoints de registro y autenticación de usuarios."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.seguridad import get_current_user, requiere_roles
from app.identidad.auditoria import TipoEventoAuth, registrar_evento_auth
from app.identidad.config import get_identity_verification_provider
from app.identidad.modelos import (
    RespuestaLogin,
    RespuestaPerfil,
    RespuestaRegistro,
    Rol,
    SolicitudCreacionUsuarioAdministrativa,
    SolicitudLogin,
    SolicitudRefresh,
    SolicitudRegistro,
)
from app.identidad.puertos import IdentityVerificationProvider
from app.identidad.repositorio import RepositorioSesionesPostgres, RepositorioUsuariosPostgres
from app.identidad.servicio import (
    ConsentimientoRequeridoError,
    CredencialesInvalidasError,
    DocumentoYaExisteError,
    KYCPendienteError,
    KYCRechazadoError,
    ServicioIdentidad,
    SesionInvalidaError,
    SesionReutilizadaError,
    UsuarioInactivoError,
    UsuarioYaExisteError,
)
from app.identidad.tokens import TokenExpiradoError, TokenInvalidoError
from app.infraestructura.database import get_db

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Autenticación"],
)

manager_actual = requiere_roles(Rol.SERVICIO_INTERNO.value)


@router.post(
    "/register",
    response_model=RespuestaRegistro,
    status_code=status.HTTP_201_CREATED,
)
def registrar_usuario(
    solicitud: SolicitudRegistro,
    request: Request,
    db: Session = Depends(get_db),
    provider: IdentityVerificationProvider = Depends(get_identity_verification_provider),
) -> RespuestaRegistro:
    return _crear_usuario(solicitud, request, db, provider)


@router.post(
    "/users",
    response_model=RespuestaRegistro,
    status_code=status.HTTP_201_CREATED,
    summary="Crea un usuario con un rol definido; exclusivo de SERVICIO_INTERNO",
)
def crear_usuario_administrativo(
    solicitud: SolicitudCreacionUsuarioAdministrativa,
    request: Request,
    _manager=Depends(manager_actual),
    db: Session = Depends(get_db),
    provider: IdentityVerificationProvider = Depends(get_identity_verification_provider),
) -> RespuestaRegistro:
    return _crear_usuario(solicitud, request, db, provider, manager=_manager)


def _crear_usuario(solicitud, request, db, provider, manager=None) -> RespuestaRegistro:
    repositorio = RepositorioUsuariosPostgres(db)
    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=provider,
    )

    try:
        if manager is None:
            resultado = servicio.registrar_usuario(solicitud)
        else:
            resultado = servicio.crear_usuario_administrativo(solicitud)
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.USER_REGISTERED,
            exitoso=True,
            usuario_id=str(resultado.id),
            email=str(resultado.email),
            detalle=(
                "Registro exitoso." if manager is None
                else f"Creado por manager:{manager.id};rol:{resultado.rol.value}"
            ),
            request=request,
        )
        return resultado

    except UsuarioYaExisteError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REGISTRATION_REJECTED,
            exitoso=False,
            email=str(solicitud.email),
            detalle="USER_ALREADY_EXISTS",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"codigo": "EMAIL_ALREADY_EXISTS", "mensaje": str(error)},
        ) from error

    except DocumentoYaExisteError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REGISTRATION_REJECTED,
            exitoso=False,
            email=str(solicitud.email),
            detalle="DOCUMENT_ALREADY_EXISTS",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"codigo": "DOCUMENT_ALREADY_EXISTS", "mensaje": str(error)},
        ) from error

    except ConsentimientoRequeridoError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REGISTRATION_REJECTED,
            exitoso=False,
            email=str(solicitud.email),
            detalle="CONSENT_REQUIRED",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"codigo": "CONSENT_REQUIRED", "mensaje": str(error)},
        ) from error

    except KYCRechazadoError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REGISTRATION_REJECTED,
            exitoso=False,
            email=str(solicitud.email),
            detalle="KYC_REJECTED",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"codigo": "KYC_REJECTED", "mensaje": str(error)},
        ) from error

    except KYCPendienteError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REGISTRATION_REJECTED,
            exitoso=False,
            email=str(solicitud.email),
            detalle="KYC_PENDING",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail={"codigo": "KYC_PENDING", "mensaje": str(error)},
        ) from error

    except httpx.HTTPError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REGISTRATION_REJECTED,
            exitoso=False,
            email=str(solicitud.email),
            detalle="KYC_PROVIDER_UNAVAILABLE",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "codigo": "KYC_PROVIDER_UNAVAILABLE",
                "mensaje": "El servicio de validación de identidad no está disponible.",
            },
        ) from error


@router.get(
    "/users",
    response_model=list[RespuestaRegistro],
    status_code=status.HTTP_200_OK,
)
def listar_usuarios(
    _manager=Depends(manager_actual),
    db: Session = Depends(get_db),
) -> list[RespuestaRegistro]:
    repositorio = RepositorioUsuariosPostgres(db)
    servicio = ServicioIdentidad(
        repositorio=repositorio,
    )

    return servicio.listar_usuarios()


@router.post(
    "/login",
    response_model=RespuestaLogin,
    status_code=status.HTTP_200_OK,
)
def login(
    solicitud: SolicitudLogin,
    request: Request,
    db: Session = Depends(get_db),
) -> RespuestaLogin:
    repositorio = RepositorioUsuariosPostgres(db)
    servicio = ServicioIdentidad(
        repositorio=repositorio,
        repositorio_sesiones=RepositorioSesionesPostgres(db),
    )

    try:
        resultado = servicio.autenticar_usuario(
            email=str(solicitud.email),
            password=solicitud.password,
        )

        usuario = repositorio.buscar_por_email(str(solicitud.email))
        if usuario is not None:
            registrar_evento_auth(
                tipo_evento=TipoEventoAuth.LOGIN_SUCCESS,
                exitoso=True,
                usuario_id=str(usuario.id),
                email=usuario.email,
                detalle="Inicio de sesión exitoso.",
                request=request,
            )

        return resultado

    except CredencialesInvalidasError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.LOGIN_FAILED,
            exitoso=False,
            email=str(solicitud.email),
            detalle="INVALID_CREDENTIALS",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "codigo": "INVALID_CREDENTIALS",
                "mensaje": str(error),
            },
        ) from error

    except UsuarioInactivoError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.LOGIN_FAILED,
            exitoso=False,
            email=str(solicitud.email),
            detalle="USER_INACTIVE",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "USER_INACTIVE",
                "mensaje": str(error),
            },
        ) from error


MENSAJE_SESION_EXPIRADA = "La sesión expiró. Inicie sesión de nuevo."
MENSAJE_SESION_INVALIDA = "La sesión no es válida. Inicie sesión de nuevo."


def _error_sesion(codigo: str, mensaje: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"codigo": codigo, "mensaje": mensaje},
    )


@router.post(
    "/refresh",
    response_model=RespuestaLogin,
    status_code=status.HTTP_200_OK,
)
def renovar_sesion(
    solicitud: SolicitudRefresh,
    request: Request,
    db: Session = Depends(get_db),
) -> RespuestaLogin:
    """Cambia un refresh token vigente por un par nuevo (rotación).

    La app Android lo usa después de validar la biometría del usuario (HU02).
    """

    servicio = ServicioIdentidad(
        repositorio=RepositorioUsuariosPostgres(db),
        repositorio_sesiones=RepositorioSesionesPostgres(db),
    )

    try:
        resultado = servicio.renovar_sesion(solicitud.refresh_token)

    except TokenExpiradoError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REFRESH_FAILED,
            exitoso=False,
            detalle="REFRESH_EXPIRED",
            request=request,
        )
        raise _error_sesion("REFRESH_EXPIRED", MENSAJE_SESION_EXPIRADA) from error

    except (TokenInvalidoError, SesionInvalidaError) as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REFRESH_FAILED,
            exitoso=False,
            detalle="REFRESH_INVALID",
            request=request,
        )
        raise _error_sesion("REFRESH_INVALID", MENSAJE_SESION_INVALIDA) from error

    except SesionReutilizadaError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REFRESH_REUSE_DETECTED,
            exitoso=False,
            usuario_id=error.usuario_id,
            detalle="REFRESH_REUSED",
            request=request,
        )
        raise _error_sesion("REFRESH_REUSED", str(error)) from error

    except UsuarioInactivoError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REFRESH_FAILED,
            exitoso=False,
            detalle="USER_INACTIVE",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"codigo": "USER_INACTIVE", "mensaje": str(error)},
        ) from error

    registrar_evento_auth(
        tipo_evento=TipoEventoAuth.TOKEN_REFRESHED,
        exitoso=True,
        detalle="Sesión renovada.",
        request=request,
    )
    return resultado


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def cerrar_sesion(
    solicitud: SolicitudRefresh,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Revoca el refresh token. Responde 204 aunque la sesión ya estuviera cerrada."""

    servicio = ServicioIdentidad(
        repositorio=RepositorioUsuariosPostgres(db),
        repositorio_sesiones=RepositorioSesionesPostgres(db),
    )

    try:
        usuario_id = servicio.cerrar_sesion(solicitud.refresh_token)
    except TokenInvalidoError as error:
        raise _error_sesion("REFRESH_INVALID", "La sesión no es válida.") from error

    registrar_evento_auth(
        tipo_evento=TipoEventoAuth.LOGOUT,
        exitoso=True,
        usuario_id=usuario_id,
        detalle="Cierre de sesión.",
        request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=RespuestaPerfil,
    status_code=status.HTTP_200_OK,
)
def perfil_actual(usuario=Depends(get_current_user)) -> RespuestaPerfil:
    """Datos del usuario dueño del token. Sin token válido responde 401 (HU02, EC08)."""

    return ServicioIdentidad(repositorio=None).obtener_perfil(usuario)

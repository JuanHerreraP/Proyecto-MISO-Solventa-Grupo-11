"""Endpoints de registro y autenticación de usuarios."""

import httpx

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.identidad.config import get_identity_verification_provider
from app.identidad.modelos import RespuestaRegistro, SolicitudRegistro, SolicitudLogin, RespuestaLogin
from app.identidad.puertos import IdentityVerificationProvider
from app.identidad.repositorio import RepositorioUsuariosPostgres
from app.identidad.servicio import (
    ConsentimientoRequeridoError,
    KYCRechazadoError,
    KYCPendienteError,
    ServicioIdentidad,
    UsuarioYaExisteError,
    CredencialesInvalidasError,
    UsuarioInactivoError,
)
from app.infraestructura.database import get_db
from app.identidad.auditoria import (
    TipoEventoAuth,
    registrar_evento_auth,
)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Autenticación"],
)


@router.post(
    "/register",
    response_model=RespuestaRegistro,
    status_code=status.HTTP_201_CREATED,
)
def registrar_usuario(
    solicitud: SolicitudRegistro,
    db: Session = Depends(get_db),
    provider: IdentityVerificationProvider = Depends(
        get_identity_verification_provider
    ),
) -> RespuestaRegistro:

    repositorio = RepositorioUsuariosPostgres(db)

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=provider,
    )

    try:
        resultado = servicio.registrar_usuario(solicitud)
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.USER_REGISTERED,
            exitoso=True,
            request=Request
        )
        return resultado

    except UsuarioYaExisteError as error:
        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REGISTRATION_REJECTED,
            exitoso=False,
            request=Request
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    except ConsentimientoRequeridoError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    except KYCRechazadoError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    except KYCRechazadoError as error:

        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.REGISTRATION_REJECTED,
            exitoso=False,
            email=str(solicitud.email),
            detalle="KYC_REJECTED",
            request=Request
        )

    except KYCPendienteError as error:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=str(error),
        ) from error

    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de validación de identidad no está disponible.",
        ) from error

@router.get(
    "/users",
    response_model=list[RespuestaRegistro],
    status_code=status.HTTP_200_OK,
)
def listar_usuarios(
    db: Session = Depends(get_db),
) -> list[RespuestaRegistro]:

    repositorio = RepositorioUsuariosPostgres(db)

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=get_identity_verification_provider(),
    )

    return servicio.listar_usuarios()

@router.post(
    "/login",
    response_model=RespuestaLogin,
    status_code=status.HTTP_200_OK,
)
def login(
        solicitud: SolicitudLogin,
        db: Session = Depends(get_db),
    ) -> RespuestaLogin:

    repositorio = RepositorioUsuariosPostgres(
        db
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio
    )

    try:
        resultado = servicio.autenticar_usuario(
            email=str(solicitud.email),
            password=solicitud.password,
        )

        usuario = repositorio.buscar_por_email(
            str(solicitud.email)
        )

        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.LOGIN_SUCCESS,
            exitoso=True,
            usuario_id=usuario.id,
            email=usuario.email,
            detalle="Inicio de sesión exitoso.",
            request=Request,
        )

        return resultado

    except CredencialesInvalidasError as error:

        registrar_evento_auth(
            tipo_evento=TipoEventoAuth.LOGIN_FAILED,
            exitoso=False,
            email=str(solicitud.email),
            detalle="INVALID_CREDENTIALS",
            request=Request,
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
            request=Request,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "USER_INACTIVE",
                "mensaje": str(error),
            },
        ) from error
        
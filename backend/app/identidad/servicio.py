from datetime import date

from pwdlib import PasswordHash

from app.identidad.modelos import (
    RespuestaRegistro,
    Rol,
    SolicitudRegistro,
    VerificationRequest,
    VerificationStatus,
    RespuestaLogin,
)
from app.identidad.modelos_db import UsuarioDB
from app.identidad.puertos import IdentityVerificationProvider
from app.identidad.tokens import crear_access_token, ACCESS_TOKEN_MINUTES, REFRESH_TOKEN_DAYS, crear_refresh_token


class UsuarioYaExisteError(Exception):
    pass


class ConsentimientoRequeridoError(Exception):
    pass


class KYCRechazadoError(Exception):
    pass


class KYCPendienteError(Exception):
    pass

class CredencialesInvalidasError(Exception):
    pass


class UsuarioInactivoError(Exception):
    pass


class ServicioIdentidad:

    def __init__(
        self,
        repositorio,
        provider: IdentityVerificationProvider |  None = None,
    ):
        self.repositorio = repositorio
        self.provider = provider
        self.password_hash = PasswordHash.recommended()

    def registrar_usuario(
        self,
        solicitud: SolicitudRegistro,
    ) -> RespuestaRegistro:

        if not solicitud.acepta_validacion_identidad:
            raise ConsentimientoRequeridoError(
                "Se requiere autorización para validar la identidad."
            )

        existente = self.repositorio.buscar_por_email(
            str(solicitud.email)
        )

        if existente is not None:
            raise UsuarioYaExisteError(
                "Ya existe un usuario registrado con este correo."
            )

        resultado_kyc = self.provider.verify(
            VerificationRequest(
                customer_id=str(solicitud.email),
                consent_id=f"registro-{solicitud.numero_documento}",
                document_type=solicitud.tipo_documento,
                document_number=solicitud.numero_documento,
                full_name=f"{solicitud.nombre} {solicitud.apellido}",
                birth_date=solicitud.fecha_nacimiento
            )
        )

        if resultado_kyc.status == VerificationStatus.REJECTED:
            raise KYCRechazadoError(
                "No fue posible completar el registro porque la validación de identidad no fue aprobada. Verifique que la información ingresada sea correcta o comuníquese con soporte si considera que se trata de un error."
            )

        if resultado_kyc.status == VerificationStatus.IN_REVIEW:
            raise KYCPendienteError(
                "No fue posible completar el registro de forma inmediata porque la validación de identidad requiere una revisión adicional. "
                "El proceso quedará pendiente hasta que la verificación sea completada."
            )

        usuario = UsuarioDB(
            nombre=solicitud.nombre,
            apellido=solicitud.apellido,
            email=str(solicitud.email).lower(),
            password_hash=self.password_hash.hash(
                solicitud.password
            ),
            rol=Rol.CLIENTE.value,
            activo=True,
            tipo_documento=solicitud.tipo_documento,
            numero_documento=solicitud.numero_documento,
            fecha_nacimiento=solicitud.fecha_nacimiento,
            kyc_validado=True,
            referencia_kyc=resultado_kyc.verification_id,
            consentimiento_kyc=solicitud.acepta_validacion_identidad,
        )

        usuario = self.repositorio.guardar(usuario)

        return RespuestaRegistro(
            id=str(usuario.id),
            nombre=usuario.nombre,
            apellido=usuario.apellido,
            email=usuario.email,
            rol=Rol(usuario.rol),
            kyc_validado=usuario.kyc_validado,
            fecha_creacion=usuario.fecha_creacion,
        )

    def listar_usuarios(
        self,
    ) -> list[RespuestaRegistro]:

        usuarios = self.repositorio.listar_todos()

        return [
            RespuestaRegistro(
                id=str(usuario.id),
                nombre=usuario.nombre,
                apellido=usuario.apellido,
                email=usuario.email,
                rol=Rol(usuario.rol),
                kyc_validado=usuario.kyc_validado,
                fecha_creacion=usuario.fecha_creacion,
            )
            for usuario in usuarios
        ]


    def autenticar_usuario(
        self,
        email: str,
        password: str,
        ) -> RespuestaLogin:

        usuario = self.repositorio.buscar_por_email(
            email
        )

        if usuario is None:
            raise CredencialesInvalidasError(
                "El correo electrónico o la contraseña son incorrectos."
            )

        password_correcta = self.password_hash.verify(
            password,
            usuario.password_hash,
        )

        if not password_correcta:
            raise CredencialesInvalidasError(
                "El correo electrónico o la contraseña son incorrectos."
            )

        if not usuario.activo:
            raise UsuarioInactivoError(
                "El usuario se encuentra inactivo y no puede iniciar sesión."
            )

        access_token = crear_access_token(
            usuario_id=str(usuario.id),
            email=usuario.email,
            rol=usuario.rol,
        )

        refresh_token = crear_refresh_token(
            usuario_id=str(usuario.id),
            email=usuario.email,
            rol=usuario.rol,
        )

        return RespuestaLogin(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_MINUTES * 60,
            refresh_expires_in=REFRESH_TOKEN_DAYS * 86400,
        )

        
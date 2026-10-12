from pwdlib import PasswordHash

from app.identidad.modelos import (
    RespuestaLogin,
    RespuestaPerfil,
    RespuestaRegistro,
    Rol,
    SolicitudRegistro,
    VerificationRequest,
    VerificationStatus,
)
from app.identidad.modelos_db import SesionRefreshDB, UsuarioDB
from app.identidad.puertos import IdentityVerificationProvider
from app.identidad.tokens import (
    ACCESS_TOKEN_MINUTES,
    REFRESH_TOKEN_DAYS,
    TokenExpiradoError,
    crear_access_token,
    emitir_refresh_token,
    validar_refresh_token,
)

MOTIVO_ROTACION = "ROTACION"


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


class SesionInvalidaError(Exception):
    """El refresh token no corresponde a una sesión emitida por Solventa."""


class SesionReutilizadaError(Exception):
    """Se presentó un refresh token ya rotado o revocado: posible robo de sesión."""

    def __init__(self, mensaje: str, usuario_id: str):
        super().__init__(mensaje)
        self.usuario_id = usuario_id


class ServicioIdentidad:
    def __init__(
        self,
        repositorio,
        provider: IdentityVerificationProvider | None = None,
        repositorio_sesiones=None,
    ):
        self.repositorio = repositorio
        self.provider = provider
        self.repositorio_sesiones = repositorio_sesiones
        self.password_hash = PasswordHash.recommended()

    def registrar_usuario(
        self,
        solicitud: SolicitudRegistro,
    ) -> RespuestaRegistro:
        if not solicitud.acepta_validacion_identidad:
            raise ConsentimientoRequeridoError(
                "Se requiere autorización para validar la identidad."
            )

        existente = self.repositorio.buscar_por_email(str(solicitud.email))
        if existente is not None:
            raise UsuarioYaExisteError("Ya existe un usuario registrado con este correo.")

        if self.provider is None:
            raise RuntimeError("Se requiere un proveedor KYC para registrar usuarios.")

        resultado_kyc = self.provider.verify(
            VerificationRequest(
                customer_id=str(solicitud.email),
                consent_id=f"registro-{solicitud.numero_documento}",
                document_type=solicitud.tipo_documento,
                document_number=solicitud.numero_documento,
                full_name=f"{solicitud.nombre} {solicitud.apellido}",
                birth_date=solicitud.fecha_nacimiento,
            )
        )

        if resultado_kyc.status == VerificationStatus.REJECTED:
            raise KYCRechazadoError(
                "No fue posible completar el registro porque la validación de "
                "identidad no fue aprobada. Verifique que la información "
                "ingresada sea correcta o comuníquese con soporte si considera "
                "que se trata de un error."
            )

        if resultado_kyc.status == VerificationStatus.IN_REVIEW:
            raise KYCPendienteError(
                "No fue posible completar el registro de forma inmediata porque "
                "la validación de identidad requiere una revisión adicional. El "
                "proceso quedará pendiente hasta que la verificación sea "
                "completada."
            )

        usuario = UsuarioDB(
            nombre=solicitud.nombre,
            apellido=solicitud.apellido,
            email=str(solicitud.email).lower(),
            password_hash=self.password_hash.hash(solicitud.password),
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

    def listar_usuarios(self) -> list[RespuestaRegistro]:
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
        usuario = self.repositorio.buscar_por_email(email)

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

        respuesta, _ = self._emitir_tokens(usuario)
        return respuesta

    def renovar_sesion(self, refresh_token: str) -> RespuestaLogin:
        """Cambia un refresh token vigente por un par nuevo y revoca el anterior.

        Si el token ya había sido rotado o revocado, se interpreta como un posible
        robo de sesión: se revocan todas las sesiones del usuario.
        """

        if self.repositorio_sesiones is None:
            raise RuntimeError("Se requiere un repositorio de sesiones para renovar.")

        payload = validar_refresh_token(refresh_token)
        jti = payload.get("jti")
        usuario_id = payload.get("sub")

        sesion = self.repositorio_sesiones.buscar(jti) if jti else None
        if sesion is None or str(sesion.usuario_id) != str(usuario_id):
            raise SesionInvalidaError("La sesión no es válida. Inicie sesión de nuevo.")

        if sesion.revocada and sesion.motivo_revocacion != MOTIVO_ROTACION:
            # Cerrada por logout o por el sistema: no es un ataque, solo ya no sirve.
            raise SesionInvalidaError("La sesión fue cerrada. Inicie sesión de nuevo.")

        if sesion.revocada:
            # Un token ya rotado se volvió a presentar: alguien más pudo copiarlo.
            self.repositorio_sesiones.revocar_todas_de_usuario(
                usuario_id, motivo="REUTILIZACION_DETECTADA"
            )
            raise SesionReutilizadaError(
                "La sesión fue cerrada por seguridad. Inicie sesión de nuevo.",
                usuario_id=str(usuario_id),
            )

        usuario = self.repositorio.buscar_por_id(str(usuario_id))
        if usuario is None:
            raise SesionInvalidaError("La sesión no es válida. Inicie sesión de nuevo.")

        if not usuario.activo:
            self.repositorio_sesiones.revocar(jti, motivo="USUARIO_INACTIVO")
            raise UsuarioInactivoError(
                "El usuario se encuentra inactivo y no puede iniciar sesión."
            )

        respuesta, nuevo_jti = self._emitir_tokens(usuario)
        self.repositorio_sesiones.revocar(jti, motivo=MOTIVO_ROTACION, reemplazada_por=nuevo_jti)
        return respuesta

    def cerrar_sesion(self, refresh_token: str) -> str | None:
        """Revoca la sesión del refresh token. Es idempotente.

        Devuelve el id del usuario cuando la sesión existía, para auditoría.
        Un token expirado no necesita revocarse: ya no sirve para renovar.
        """

        if self.repositorio_sesiones is None:
            raise RuntimeError("Se requiere un repositorio de sesiones para cerrar sesión.")

        try:
            payload = validar_refresh_token(refresh_token)
        except TokenExpiradoError:
            return None

        jti = payload.get("jti")
        if jti:
            self.repositorio_sesiones.revocar(jti, motivo="LOGOUT")

        return payload.get("sub")

    def obtener_perfil(self, usuario) -> RespuestaPerfil:
        return RespuestaPerfil(
            id=str(usuario.id),
            nombre=usuario.nombre,
            apellido=usuario.apellido,
            email=usuario.email,
            rol=Rol(usuario.rol),
        )

    def _emitir_tokens(self, usuario) -> tuple[RespuestaLogin, str]:
        access_token = crear_access_token(
            usuario_id=str(usuario.id),
            email=usuario.email,
            rol=usuario.rol,
        )

        refresh = emitir_refresh_token(
            usuario_id=str(usuario.id),
            email=usuario.email,
            rol=usuario.rol,
        )

        if self.repositorio_sesiones is not None:
            self.repositorio_sesiones.guardar(
                SesionRefreshDB(
                    jti=refresh.jti,
                    usuario_id=usuario.id,
                    fecha_expiracion=refresh.expira_en,
                    revocada=False,
                )
            )

        respuesta = RespuestaLogin(
            access_token=access_token,
            refresh_token=refresh.token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_MINUTES * 60,
            refresh_expires_in=REFRESH_TOKEN_DAYS * 86400,
        )
        return respuesta, refresh.jti

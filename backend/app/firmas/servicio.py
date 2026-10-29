"""Caso de uso de la firma electrónica del contrato (HU14 / BPM-60).

Flujo: el pago de la cotización queda APROBADO (HU13) -> se presenta el contrato
prellenado -> se envía un OTP por SMS o correo -> el cliente firma con el código ->
el proveedor sella la firma y quedan sus metadatos. HU12 emite la póliza a partir de un
proceso FIRMADO.
"""

import hashlib
import hmac
import logging
import os
import secrets
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from app.cotizaciones.repositorio import RepositorioCotizaciones
from app.firmas.contrato import (
    VERSION_PLANTILLA,
    CoberturaContrato,
    ContratoSeguro,
    clausulas_de,
    nombre_ramo_de,
)
from app.firmas.modelos import (
    MAX_ENVIOS,
    MAX_INTENTOS_POR_CODIGO,
    VIGENCIA_OTP,
    CanalOtp,
    EstadoFirma,
    ProcesoFirma,
    enmascarar,
)
from app.firmas.puertos import (
    ProveedorFirmaElectronica,
    RepositorioFirmas,
    RepositorioTitulares,
    SolicitudEnvioOtp,
    SolicitudSello,
)
from app.pagos.puertos import RepositorioPagos

logger = logging.getLogger(__name__)


class FirmaNoDisponible(Exception):
    """No se puede presentar el contrato: falta la cotización, el pago o los datos."""

    def __init__(self, codigo: str):
        super().__init__(codigo)
        self.codigo = codigo


class OtpRechazado(Exception):
    def __init__(self, codigo: str, proceso: ProcesoFirma):
        super().__init__(codigo)
        self.codigo = codigo
        self.proceso = proceso


class ReenvioNoPermitido(Exception):
    def __init__(self, codigo: str, proceso: ProcesoFirma):
        super().__init__(codigo)
        self.codigo = codigo
        self.proceso = proceso


class FirmaBloqueada(Exception):
    pass


class DocumentoAlterado(Exception):
    """La huella aceptada por el cliente no es la del contrato guardado."""


class FirmaNoEncontrada(Exception):
    pass


_SECRETO_EFIMERO = secrets.token_bytes(32)
_aviso_secreto_emitido = False


def secreto_otp() -> bytes:
    """Llave del HMAC de los OTP. En AWS debe venir de FIRMA_OTP_SECRET.

    Sin ella se usa una llave aleatoria del proceso: sirve en local, pero con varias tareas
    ECS un OTP emitido por una tarea no se podría validar en otra.
    """
    global _aviso_secreto_emitido
    secreto = os.getenv("FIRMA_OTP_SECRET")
    if secreto:
        return secreto.encode()
    if not _aviso_secreto_emitido:
        logger.warning("FIRMA_OTP_SECRET no está configurado; se usa un secreto efímero.")
        _aviso_secreto_emitido = True
    return _SECRETO_EFIMERO


def generar_codigo_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


class ServicioFirmas:
    def __init__(
        self,
        firmas: RepositorioFirmas,
        cotizaciones: RepositorioCotizaciones,
        pagos: RepositorioPagos,
        titulares: RepositorioTitulares,
        proveedor: ProveedorFirmaElectronica,
        secreto: bytes | None = None,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = lambda: f"FIR-{uuid.uuid4()}",
        generar_codigo: Callable[[], str] = generar_codigo_otp,
    ):
        self._firmas = firmas
        self._cotizaciones = cotizaciones
        self._pagos = pagos
        self._titulares = titulares
        self._proveedor = proveedor
        self._secreto = secreto if secreto is not None else secreto_otp()
        self._reloj = reloj
        self._generar_id = generar_id
        self._generar_codigo = generar_codigo

    # --- Presentación del contrato -------------------------------------------------

    def presentar(self, cliente_id: str, cotizacion_id: str) -> ProcesoFirma:
        """Devuelve el proceso de firma de la cotización, creándolo tras el pago aprobado."""

        existente = self._firmas.obtener_por_cotizacion(cotizacion_id)
        if existente is not None:
            if existente.cliente_id != cliente_id:
                raise FirmaNoDisponible("COTIZACION_NO_ENCONTRADA")
            return existente

        cotizacion = self._cotizaciones.obtener(cotizacion_id)
        if cotizacion is None or cotizacion.cliente_id != cliente_id:
            raise FirmaNoDisponible("COTIZACION_NO_ENCONTRADA")
        pago = self._pagos.obtener_aprobado_de_cotizacion(cotizacion_id)
        if pago is None or pago.cliente_id != cliente_id:
            raise FirmaNoDisponible("PAGO_NO_APROBADO")
        if cotizacion.cobertura_principal is None:
            raise FirmaNoDisponible("COTIZACION_INCOMPLETA")
        titular = self._titulares.obtener(cliente_id)
        if titular is None:
            raise FirmaNoDisponible("TITULAR_SIN_DATOS")

        cobertura = cotizacion.cobertura_principal
        contrato = ContratoSeguro(
            version_plantilla=VERSION_PLANTILLA,
            cotizacion_id=cotizacion.cotizacion_id,
            ramo=cotizacion.ramo,
            nombre_ramo=nombre_ramo_de(cotizacion.ramo, cotizacion.datos_riesgo),
            titular=titular,
            cobertura_principal=CoberturaContrato(
                codigo=cobertura.codigo,
                nombre=cobertura.nombre,
                suma_asegurada=cobertura.suma_asegurada,
                descripcion=cobertura.descripcion,
            ),
            datos_riesgo=cotizacion.datos_riesgo,
            # Lo pactado es lo efectivamente cobrado.
            prima_total=pago.monto,
            moneda=pago.moneda,
            pago_id=pago.pago_id,
            referencia_pago=pago.referencia_pasarela,
            fecha_pago=pago.actualizado_en,
            clausulas=clausulas_de(cotizacion.ramo, cotizacion.datos_riesgo),
        )
        ahora = self._reloj()
        proceso = ProcesoFirma(
            firma_id=self._generar_id(),
            cotizacion_id=cotizacion_id,
            pago_id=pago.pago_id,
            cliente_id=cliente_id,
            contrato=contrato,
            huella_documento=contrato.huella(),
            creado_en=ahora,
            actualizado_en=ahora,
        )
        if not self._firmas.crear(proceso):
            # Otra petición creó el proceso al mismo tiempo: se usa el que quedó guardado.
            return self.presentar(cliente_id, cotizacion_id)
        return proceso

    def consultar(self, cliente_id: str, cotizacion_id: str) -> ProcesoFirma:
        proceso = self._firmas.obtener_por_cotizacion(cotizacion_id)
        if proceso is None or proceso.cliente_id != cliente_id:
            raise FirmaNoEncontrada(cotizacion_id)
        return proceso

    # --- OTP ------------------------------------------------------------------------

    def solicitar_otp(self, cliente_id: str, cotizacion_id: str, canal: CanalOtp) -> ProcesoFirma:
        proceso = self.presentar(cliente_id, cotizacion_id)
        self._exigir_pendiente(proceso)

        ahora = self._reloj()
        if proceso.envios >= MAX_ENVIOS:
            raise ReenvioNoPermitido("ENVIOS_AGOTADOS", proceso)
        disponible_en = proceso.reenvio_disponible_en()
        if disponible_en is not None and ahora < disponible_en:
            raise ReenvioNoPermitido("ESPERA_REENVIO", proceso)

        titular = proceso.contrato.titular
        destino = titular.celular if canal is CanalOtp.SMS else str(titular.email)
        if not destino:
            raise FirmaNoDisponible("DESTINO_NO_DISPONIBLE")

        codigo = self._generar_codigo()
        # Si el proveedor falla, la excepción sube sin consumir un envío.
        referencia = self._proveedor.enviar_otp(
            SolicitudEnvioOtp(
                referencia_proceso=proceso.firma_id,
                canal=canal,
                destino=destino,
                codigo=codigo,
            )
        )
        actualizado = proceso.model_copy(
            update={
                "otp_hash": self._hash_otp(proceso.firma_id, codigo),
                "otp_canal": canal,
                "otp_destino": enmascarar(destino, canal),
                "otp_emitido_en": ahora,
                "otp_expira_en": ahora + VIGENCIA_OTP,
                "intentos_fallidos": 0,
                "envios": proceso.envios + 1,
                "referencia_envio": referencia,
                "actualizado_en": ahora,
            }
        )
        self._firmas.guardar(actualizado)
        return actualizado

    # --- Firma ----------------------------------------------------------------------

    def firmar(
        self,
        cliente_id: str,
        cotizacion_id: str,
        codigo: str,
        huella_aceptada: str,
        ip: str | None,
        user_agent: str | None,
    ) -> ProcesoFirma:
        proceso = self.consultar(cliente_id, cotizacion_id)
        if not hmac.compare_digest(proceso.huella_documento, huella_aceptada):
            raise DocumentoAlterado()
        if proceso.estado is EstadoFirma.FIRMADA:
            # Reintento tras una respuesta perdida: la firma ya existe.
            return proceso
        self._exigir_pendiente(proceso)
        if not proceso.documento_integro():
            logger.error("El contrato del proceso %s no coincide con su huella", proceso.firma_id)
            raise DocumentoAlterado()
        if self._pagos.obtener_aprobado_de_cotizacion(cotizacion_id) is None:
            raise FirmaNoDisponible("PAGO_NO_APROBADO")

        ahora = self._reloj()
        if proceso.otp_hash is None:
            raise OtpRechazado("OTP_NO_EMITIDO", proceso)
        if proceso.intentos_fallidos >= MAX_INTENTOS_POR_CODIGO:
            raise OtpRechazado("OTP_INTENTOS_AGOTADOS", proceso)
        if proceso.otp_expira_en is None or ahora >= proceso.otp_expira_en:
            raise OtpRechazado("OTP_VENCIDO", proceso)

        esperado = self._hash_otp(proceso.firma_id, codigo)
        if not hmac.compare_digest(proceso.otp_hash, esperado):
            self._registrar_fallo(proceso, ahora)

        sello = self._proveedor.sellar(
            SolicitudSello(
                referencia_proceso=proceso.firma_id,
                huella_documento=proceso.huella_documento,
                firmante_id=cliente_id,
                firmado_en=ahora,
                ip_firmante=ip,
            )
        )
        firmado = proceso.model_copy(
            update={
                "estado": EstadoFirma.FIRMADA,
                "otp_hash": None,
                "firmado_en": ahora,
                "firmante_id": cliente_id,
                "ip_firmante": ip,
                "user_agent": (user_agent or "")[:300] or None,
                "referencia_proveedor": sello.referencia_proveedor,
                "sello_proveedor": sello.sello,
                "actualizado_en": ahora,
            }
        )
        self._firmas.guardar(firmado)
        logger.info("Contrato %s firmado por %s", proceso.firma_id, cliente_id)
        return firmado

    # --- Auxiliares -----------------------------------------------------------------

    def _registrar_fallo(self, proceso: ProcesoFirma, ahora: datetime) -> None:
        intentos = proceso.intentos_fallidos + 1
        agotado = intentos >= MAX_INTENTOS_POR_CODIGO
        bloquear = agotado and proceso.envios >= MAX_ENVIOS
        actualizado = proceso.model_copy(
            update={
                "intentos_fallidos": intentos,
                "estado": EstadoFirma.BLOQUEADA if bloquear else proceso.estado,
                "actualizado_en": ahora,
            }
        )
        self._firmas.guardar(actualizado)
        if bloquear:
            logger.warning("Proceso de firma %s bloqueado por intentos", proceso.firma_id)
            raise FirmaBloqueada()
        raise OtpRechazado("OTP_INCORRECTO", actualizado)

    @staticmethod
    def _exigir_pendiente(proceso: ProcesoFirma) -> None:
        if proceso.estado is EstadoFirma.BLOQUEADA:
            raise FirmaBloqueada()
        if proceso.estado is EstadoFirma.FIRMADA:
            raise ReenvioNoPermitido("YA_FIRMADO", proceso)

    def _hash_otp(self, firma_id: str, codigo: str) -> str:
        return hmac.new(self._secreto, f"{firma_id}:{codigo}".encode(), hashlib.sha256).hexdigest()

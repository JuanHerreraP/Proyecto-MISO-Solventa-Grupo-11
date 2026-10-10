"""Casos de uso para administrar socios de distribución."""

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from app.socios.dominio.auditoria import (
    AccionAuditoria,
    RegistroAuditoriaSocio,
    RepositorioAuditoriaSocios,
)
from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.modelos import (
    EstadoSocio,
    SocioDistribucion,
    SolicitudActualizacionSocio,
    SolicitudAltaSocio,
)
from app.socios.dominio.tenant import AprovisionadorTenants
from app.socios.repositorio import RepositorioSocios


class NitDuplicado(Exception):
    """Ya existe un socio registrado con el mismo NIT."""


class SocioNoEncontrado(Exception):
    """No existe un socio con el identificador solicitado."""


class CredencialesSocioInvalidas(Exception):
    """El socio o el tenant presentado no corresponde a una configuración válida."""


class SocioInactivo(Exception):
    """El socio existe, pero no está habilitado para consumir las APIs."""


class EndpointNoAutorizado(Exception):
    """El socio no tiene autorización para consumir el endpoint solicitado."""


def generar_socio_id() -> str:
    return f"SOCIO-{uuid.uuid4()}"


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class ServicioSocios:
    def __init__(
        self,
        repositorio: RepositorioSocios,
        tenants: AprovisionadorTenants,
        auditoria: RepositorioAuditoriaSocios,
        generar_id: Callable[[], str] = generar_socio_id,
        reloj: Callable[[], datetime] = ahora_utc,
    ):
        self._repositorio = repositorio
        self._tenants = tenants
        self._auditoria = auditoria
        self._generar_id = generar_id
        self._reloj = reloj

    def dar_de_alta(self, solicitud: SolicitudAltaSocio, actor_id: str) -> SocioDistribucion:
        if self._repositorio.obtener_por_nit(solicitud.nit) is not None:
            raise NitDuplicado(solicitud.nit)

        socio_id = self._generar_id()
        fecha = self._reloj()
        tenant = self._tenants.aprovisionar(socio_id, fecha)
        socio = SocioDistribucion(
            **solicitud.model_dump(),
            socio_id=socio_id,
            tenant_id=tenant.tenant_id,
            estado=EstadoSocio.ACTIVO,
            creado_en=fecha,
            actualizado_en=fecha,
        )
        self._repositorio.guardar(socio)
        self._registrar_auditoria(
            socio_id=socio.socio_id,
            actor_id=actor_id,
            accion=AccionAuditoria.ALTA,
            campos=list(SolicitudAltaSocio.model_fields) + ["estado", "tenant_id"],
            fecha=fecha,
        )
        return socio

    def consultar(self, socio_id: str) -> SocioDistribucion:
        socio = self._repositorio.obtener(socio_id)
        if socio is None:
            raise SocioNoEncontrado(socio_id)
        return socio

    def actualizar(
        self,
        socio_id: str,
        solicitud: SolicitudActualizacionSocio,
        actor_id: str,
    ) -> SocioDistribucion:
        socio = self.consultar(socio_id)
        cambios = solicitud.model_dump(exclude_unset=True)
        fecha = self._reloj()
        actualizado = SocioDistribucion.model_validate(
            {
                **socio.model_dump(),
                **cambios,
                "actualizado_en": fecha,
            }
        )
        self._repositorio.guardar(actualizado)
        self._registrar_auditoria(
            socio_id=socio_id,
            actor_id=actor_id,
            accion=AccionAuditoria.MODIFICACION,
            campos=list(cambios),
            fecha=fecha,
        )
        return actualizado

    def consultar_auditoria(self, socio_id: str) -> list[RegistroAuditoriaSocio]:
        self.consultar(socio_id)
        return self._auditoria.listar_por_socio(socio_id)

    def autorizar_consumo(
        self,
        socio_id: str,
        tenant_id: str,
        endpoint: CodigoEndpoint,
    ) -> SocioDistribucion:
        socio = self._repositorio.obtener(socio_id)
        if socio is None or socio.tenant_id != tenant_id:
            raise CredencialesSocioInvalidas(socio_id)
        if socio.estado is not EstadoSocio.ACTIVO:
            raise SocioInactivo(socio_id)
        if endpoint not in socio.endpoints_autorizados:
            raise EndpointNoAutorizado(endpoint)
        return socio

    def _registrar_auditoria(
        self,
        socio_id: str,
        actor_id: str,
        accion: AccionAuditoria,
        campos: list[str],
        fecha: datetime,
    ) -> None:
        registro = RegistroAuditoriaSocio(
            auditoria_id=f"AUD-{uuid.uuid4()}",
            socio_id=socio_id,
            actor_id=actor_id,
            accion=accion,
            campos_modificados=sorted(campos),
            fecha=fecha,
        )
        self._auditoria.registrar(registro)

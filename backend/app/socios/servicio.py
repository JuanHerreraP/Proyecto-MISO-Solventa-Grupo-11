"""Caso de uso para dar de alta socios de distribución (BPM-143/BPM-146)."""

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from app.socios.dominio.modelos import (
    EstadoSocio,
    SocioDistribucion,
    SolicitudAltaSocio,
)
from app.socios.dominio.tenant import AprovisionadorTenants
from app.socios.repositorio import RepositorioSocios


class NitDuplicado(Exception):
    """Ya existe un socio registrado con el mismo NIT."""


def generar_socio_id() -> str:
    return f"SOCIO-{uuid.uuid4()}"


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class ServicioSocios:
    def __init__(
        self,
        repositorio: RepositorioSocios,
        tenants: AprovisionadorTenants,
        generar_id: Callable[[], str] = generar_socio_id,
        reloj: Callable[[], datetime] = ahora_utc,
    ):
        self._repositorio = repositorio
        self._tenants = tenants
        self._generar_id = generar_id
        self._reloj = reloj

    def dar_de_alta(self, solicitud: SolicitudAltaSocio) -> SocioDistribucion:
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
        return socio

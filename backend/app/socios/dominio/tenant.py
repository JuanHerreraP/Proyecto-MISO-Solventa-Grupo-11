"""Aprovisionamiento lógico de tenants para socios (BPM-146)."""

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class TenantSocio(BaseModel):
    """Espacio lógico que aísla la configuración de un socio."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: str = Field(min_length=1, max_length=50)
    socio_id: str = Field(min_length=1, max_length=50)
    creado_en: datetime


class AprovisionadorTenants(Protocol):
    def aprovisionar(self, socio_id: str, creado_en: datetime) -> TenantSocio: ...


def generar_tenant_id() -> str:
    return f"TENANT-{uuid.uuid4()}"


class AprovisionadorTenantsEnMemoria:
    """Adaptador local; conserva un tenant independiente por socio."""

    def __init__(self, generar_id: Callable[[], str] = generar_tenant_id):
        self._generar_id = generar_id
        self._por_socio: dict[str, TenantSocio] = {}

    def aprovisionar(self, socio_id: str, creado_en: datetime) -> TenantSocio:
        existente = self._por_socio.get(socio_id)
        if existente is not None:
            return existente

        tenant = TenantSocio(
            tenant_id=self._generar_id(),
            socio_id=socio_id,
            creado_en=creado_en,
        )
        self._por_socio[socio_id] = tenant
        return tenant

    def obtener_por_socio(self, socio_id: str) -> TenantSocio | None:
        return self._por_socio.get(socio_id)

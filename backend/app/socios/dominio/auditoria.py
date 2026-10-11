"""Auditoría del alta y las modificaciones de socios (BPM-149)."""

from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class AccionAuditoria(str, Enum):
    ALTA = "ALTA"
    MODIFICACION = "MODIFICACION"


class RegistroAuditoriaSocio(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    auditoria_id: str = Field(min_length=1, max_length=50)
    socio_id: str = Field(min_length=1, max_length=50)
    actor_id: str = Field(min_length=1, max_length=120)
    accion: AccionAuditoria
    campos_modificados: list[str] = Field(min_length=1)
    fecha: datetime


class RepositorioAuditoriaSocios(Protocol):
    def registrar(self, registro: RegistroAuditoriaSocio) -> None: ...

    def listar_por_socio(self, socio_id: str) -> list[RegistroAuditoriaSocio]: ...


class RepositorioAuditoriaSociosEnMemoria:
    def __init__(self):
        self._registros: list[RegistroAuditoriaSocio] = []

    def registrar(self, registro: RegistroAuditoriaSocio) -> None:
        self._registros.append(registro)

    def listar_por_socio(self, socio_id: str) -> list[RegistroAuditoriaSocio]:
        return [registro for registro in self._registros if registro.socio_id == socio_id]

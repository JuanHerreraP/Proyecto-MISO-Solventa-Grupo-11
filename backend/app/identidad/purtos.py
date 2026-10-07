"""Puertos utilizados por el servicio de identidad."""

from typing import Protocol
from abc import ABC, abstractmethod

from app.identidad.modelos import ResultadoKYC, SolicitudKYC, Usuario


class ProveedorKYC(Protocol):
    @abstractmethod
    async def verificar_identidad(
        self,
        solicitud: SolicitudKYC,
    ) -> ResultadoKYC:
        ...


class RepositorioUsuarios(Protocol):
    def guardar(self, usuario: Usuario) -> Usuario:
        ...

    def buscar_por_email(self, email: str) -> Usuario | None:
        ...

    def buscar_por_id(self, usuario_id: str) -> Usuario | None:
        ...
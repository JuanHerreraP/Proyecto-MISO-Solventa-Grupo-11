"""Correo del cliente para los avisos de la renovación automática (HU17).

Se toma del módulo de identidad en el momento del envío: si el cliente cambió su correo después
de contratar, el aviso llega al correo actual y no al que quedó en el contrato.
"""

from sqlalchemy.orm import Session

from app.firmas.repositorio import RepositorioTitularesPostgres


class DirectorioCorreosIdentidad:
    def __init__(self, db: Session):
        self._titulares = RepositorioTitularesPostgres(db)

    def correo_de(self, cliente_id: str) -> str | None:
        titular = self._titulares.obtener(cliente_id)
        return str(titular.email) if titular is not None else None


class DirectorioCorreosEnMemoria:
    def __init__(self, correos: dict[str, str] | None = None):
        self.correos = dict(correos or {})

    def correo_de(self, cliente_id: str) -> str | None:
        return self.correos.get(cliente_id)

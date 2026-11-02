"""Persistencia del registro del documento de la póliza (HU12)."""

from datetime import UTC, datetime
from typing import Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.polizas.modelos_db import DocumentoPolizaDB


class DocumentoPoliza(BaseModel):
    model_config = ConfigDict(extra="forbid")

    poliza_id: str = Field(min_length=1, max_length=50)
    clave_almacenamiento: str = Field(min_length=1, max_length=200)
    huella_sha256: str = Field(min_length=64, max_length=64)
    tamano_bytes: int = Field(gt=0)
    creado_en: AwareDatetime
    bienvenida_enviada_en: AwareDatetime | None = None
    notificada_en: AwareDatetime | None = None


class RepositorioDocumentos(Protocol):
    def guardar(self, documento: DocumentoPoliza) -> None: ...

    def obtener(self, poliza_id: str) -> DocumentoPoliza | None: ...


class RepositorioDocumentosEnMemoria:
    def __init__(self):
        self._por_poliza: dict[str, DocumentoPoliza] = {}

    def guardar(self, documento: DocumentoPoliza) -> None:
        self._por_poliza[documento.poliza_id] = documento.model_copy()

    def obtener(self, poliza_id: str) -> DocumentoPoliza | None:
        documento = self._por_poliza.get(poliza_id)
        return documento.model_copy() if documento is not None else None


class RepositorioDocumentosPostgres:
    def __init__(self, db: Session):
        self._db = db

    def guardar(self, documento: DocumentoPoliza) -> None:
        datos = documento.model_dump()
        persistido = self._db.get(DocumentoPolizaDB, documento.poliza_id)
        if persistido is None:
            self._db.add(DocumentoPolizaDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(persistido, campo, valor)
        self._db.commit()

    def obtener(self, poliza_id: str) -> DocumentoPoliza | None:
        registro = self._db.get(DocumentoPolizaDB, poliza_id)
        if registro is None:
            return None
        return DocumentoPoliza(
            poliza_id=registro.poliza_id,
            clave_almacenamiento=registro.clave_almacenamiento,
            huella_sha256=registro.huella_sha256,
            tamano_bytes=registro.tamano_bytes,
            creado_en=_con_zona(registro.creado_en),
            bienvenida_enviada_en=_con_zona(registro.bienvenida_enviada_en),
            notificada_en=_con_zona(registro.notificada_en),
        )


def _con_zona(fecha: datetime | None) -> datetime | None:
    """SQLite devuelve las fechas sin zona horaria; se guardan siempre en UTC."""
    if fecha is not None and fecha.tzinfo is None:
        return fecha.replace(tzinfo=UTC)
    return fecha

"""Almacenamiento del PDF de la póliza (HU12).

El PDF se escribe una sola vez y no se modifica. Cambiar el destino (disco local en
desarrollo, S3 en AWS) es escribir otro adaptador de `AlmacenDocumentos`; la emisión no cambia.
"""

import hmac
import os
from pathlib import Path
from typing import Protocol

DIRECTORIO_POR_DEFECTO = "./documentos_polizas"


class AlmacenNoDisponible(Exception):
    """No se pudo escribir o leer el documento."""


class DocumentoInmutable(Exception):
    """Ya existe un documento distinto bajo esa clave; los documentos no se sobrescriben."""


class AlmacenDocumentos(Protocol):
    def guardar(self, clave: str, contenido: bytes) -> None:
        """Escribe el documento. Repetir con el mismo contenido es inocuo."""
        ...

    def leer(self, clave: str) -> bytes | None: ...


class AlmacenEnMemoria:
    def __init__(self):
        self._por_clave: dict[str, bytes] = {}

    def guardar(self, clave: str, contenido: bytes) -> None:
        existente = self._por_clave.get(clave)
        if existente is not None and not hmac.compare_digest(existente, contenido):
            raise DocumentoInmutable(clave)
        self._por_clave[clave] = contenido

    def leer(self, clave: str) -> bytes | None:
        return self._por_clave.get(clave)


class AlmacenEnDisco:
    def __init__(self, directorio: str | os.PathLike[str] | None = None):
        base = directorio or os.getenv("POLIZAS_DOCUMENTOS_DIR") or DIRECTORIO_POR_DEFECTO
        self._base = Path(base).resolve()

    def guardar(self, clave: str, contenido: bytes) -> None:
        ruta = self._ruta(clave)
        try:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            with ruta.open("xb") as archivo:
                archivo.write(contenido)
        except FileExistsError:
            if not hmac.compare_digest(ruta.read_bytes(), contenido):
                raise DocumentoInmutable(clave) from None
        except OSError as error:
            raise AlmacenNoDisponible(str(error)) from None

    def leer(self, clave: str) -> bytes | None:
        ruta = self._ruta(clave)
        try:
            return ruta.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as error:
            raise AlmacenNoDisponible(str(error)) from None

    def _ruta(self, clave: str) -> Path:
        ruta = (self._base / clave).resolve()
        if not ruta.is_relative_to(self._base):
            raise AlmacenNoDisponible("Clave fuera del directorio de documentos.")
        return ruta

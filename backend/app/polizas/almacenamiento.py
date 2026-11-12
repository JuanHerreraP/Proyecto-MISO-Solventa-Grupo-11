"""Almacenamiento del PDF de la póliza (HU12) y de las evidencias de siniestro (HU04).

Cada documento se escribe una sola vez y no se modifica. Hay tres adaptadores de
`AlmacenDocumentos`:

- `AlmacenEnDisco`: carpeta local. Sirve para desarrollo y es el respaldo.
- `AlmacenS3`: bucket de S3, el destino previsto en AWS.
- `AlmacenConRespaldo`: intenta S3 primero y, si S3 no está disponible, usa el disco. Con él
  la aplicación corre igual sin nube (sin bucket configurado, sin credenciales o sin red) y,
  cuando S3 esté disponible, lo usa sin cambiar el código de la emisión.

`crear_almacen()` elige según las variables de entorno.
"""

import hmac
import logging
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)

DIRECTORIO_POR_DEFECTO = "./documentos_polizas"
SEGUNDOS_CONEXION_S3 = 1
SEGUNDOS_LECTURA_S3 = 5
INTENTOS_S3 = 2
PAUSA_TRAS_FALLO_SEGUNDOS = 30
TIPO_PDF = "application/pdf"


class AlmacenNoDisponible(Exception):
    """No se pudo escribir o leer el documento."""


class DocumentoInmutable(Exception):
    """Ya existe un documento distinto bajo esa clave; los documentos no se sobrescriben."""


class AlmacenDocumentos(Protocol):
    def guardar(self, clave: str, contenido: bytes, tipo_contenido: str = TIPO_PDF) -> None:
        """Escribe el documento. Repetir con el mismo contenido es inocuo."""
        ...

    def leer(self, clave: str) -> bytes | None:
        """Devuelve el documento, o None si no existe."""
        ...


class AlmacenEnMemoria:
    def __init__(self):
        self._por_clave: dict[str, bytes] = {}

    def guardar(self, clave: str, contenido: bytes, tipo_contenido: str = TIPO_PDF) -> None:
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

    def guardar(self, clave: str, contenido: bytes, tipo_contenido: str = TIPO_PDF) -> None:
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


_CODIGOS_NO_ENCONTRADO = {"404", "NoSuchKey", "NotFound"}


class AlmacenS3:
    """Guarda los PDF en un bucket de S3.

    Las credenciales y la región salen de la cadena estándar de AWS (rol de la tarea en ECS,
    variables de entorno o perfil). Todo fallo de conexión, de credenciales o de permisos se
    informa como `AlmacenNoDisponible`, para que el respaldo pueda actuar.
    """

    def __init__(
        self,
        bucket: str,
        prefijo: str = "",
        endpoint_url: str | None = None,
        cliente: Any = None,
    ):
        self._bucket = bucket
        self._prefijo = prefijo.strip("/")
        self._cliente = cliente or self._crear_cliente(endpoint_url)

    @staticmethod
    def _crear_cliente(endpoint_url: str | None) -> Any:
        import boto3
        from botocore.config import Config

        # Tiempos cortos: sin nube, el respaldo debe entrar en segundos, no en minutos.
        configuracion = Config(
            connect_timeout=SEGUNDOS_CONEXION_S3,
            read_timeout=SEGUNDOS_LECTURA_S3,
            retries={"max_attempts": INTENTOS_S3, "mode": "standard"},
        )
        return boto3.client("s3", endpoint_url=endpoint_url, config=configuracion)

    def guardar(self, clave: str, contenido: bytes, tipo_contenido: str = TIPO_PDF) -> None:
        objeto = self._objeto(clave)
        existente = self._obtener(objeto)
        if existente is not None:
            if not hmac.compare_digest(existente, contenido):
                raise DocumentoInmutable(clave)
            return
        self._llamar(
            self._cliente.put_object,
            Bucket=self._bucket,
            Key=objeto,
            Body=contenido,
            ContentType=tipo_contenido,
            ServerSideEncryption="AES256",
        )

    def leer(self, clave: str) -> bytes | None:
        return self._obtener(self._objeto(clave))

    def _obtener(self, objeto: str) -> bytes | None:
        try:
            respuesta = self._cliente.get_object(Bucket=self._bucket, Key=objeto)
            return respuesta["Body"].read()
        except Exception as error:
            if _es_no_encontrado(error):
                return None
            raise AlmacenNoDisponible(_describir(error)) from None

    @staticmethod
    def _llamar(operacion, **argumentos) -> Any:
        try:
            return operacion(**argumentos)
        except Exception as error:
            raise AlmacenNoDisponible(_describir(error)) from None

    def _objeto(self, clave: str) -> str:
        if ".." in Path(clave).parts or clave.startswith(("/", "\\")):
            raise AlmacenNoDisponible("Clave no válida.")
        return f"{self._prefijo}/{clave}" if self._prefijo else clave


def _es_no_encontrado(error: Exception) -> bool:
    respuesta = getattr(error, "response", None)
    if not isinstance(respuesta, dict):
        return False
    return str(respuesta.get("Error", {}).get("Code", "")) in _CODIGOS_NO_ENCONTRADO


def _describir(error: Exception) -> str:
    """Resumen sin datos sensibles: el tipo de fallo y, si existe, el código de AWS."""
    respuesta = getattr(error, "response", None)
    codigo = respuesta.get("Error", {}).get("Code") if isinstance(respuesta, dict) else None
    return f"{type(error).__name__}{f' ({codigo})' if codigo else ''}"


class AlmacenConRespaldo:
    """Usa el almacén principal y, si no está disponible, el de respaldo.

    - Guardar: intenta el principal; si no responde, guarda en el respaldo.
    - Leer: busca en el principal; si no está o no responde, busca en el respaldo. Así se
      encuentran también los documentos guardados en disco mientras S3 no estaba disponible.
    - Tras un fallo, el principal se omite durante `pausa_segundos`: sin nube, cada petición
      no tiene que esperar de nuevo los tiempos de conexión antes de usar el disco.

    Un documento distinto bajo la misma clave sigue siendo un error (`DocumentoInmutable`),
    sin importar en cuál de los dos almacenes esté.
    """

    def __init__(
        self,
        principal: AlmacenDocumentos,
        respaldo: AlmacenDocumentos,
        pausa_segundos: float = PAUSA_TRAS_FALLO_SEGUNDOS,
        reloj: Callable[[], float] = time.monotonic,
    ):
        self._principal = principal
        self._respaldo = respaldo
        self._pausa = pausa_segundos
        self._reloj = reloj
        self._omitir_hasta = 0.0

    def guardar(self, clave: str, contenido: bytes, tipo_contenido: str = TIPO_PDF) -> None:
        if self._principal_disponible():
            try:
                self._principal.guardar(clave, contenido, tipo_contenido)
                return
            except AlmacenNoDisponible as error:
                self._registrar_fallo(error, "se guarda en el respaldo")
        self._respaldo.guardar(clave, contenido, tipo_contenido)

    def leer(self, clave: str) -> bytes | None:
        if self._principal_disponible():
            try:
                contenido = self._principal.leer(clave)
            except AlmacenNoDisponible as error:
                self._registrar_fallo(error, "se lee del respaldo")
            else:
                if contenido is not None:
                    return contenido
        return self._respaldo.leer(clave)

    def _principal_disponible(self) -> bool:
        return self._reloj() >= self._omitir_hasta

    def _registrar_fallo(self, error: Exception, accion: str) -> None:
        self._omitir_hasta = self._reloj() + self._pausa
        logger.warning("Almacén principal no disponible (%s); %s", error, accion)


def crear_almacen() -> AlmacenDocumentos:
    """Disco si no hay bucket configurado; si lo hay, S3 con el disco como respaldo.

    Variables: `POLIZAS_S3_BUCKET` (activa S3), `POLIZAS_S3_PREFIJO` (carpeta dentro del
    bucket), `POLIZAS_S3_ENDPOINT_URL` (S3 compatible, como MinIO o LocalStack) y
    `POLIZAS_DOCUMENTOS_DIR` (carpeta del disco).
    """

    disco = AlmacenEnDisco()
    bucket = os.getenv("POLIZAS_S3_BUCKET")
    if not bucket:
        return disco
    try:
        s3 = AlmacenS3(
            bucket,
            prefijo=os.getenv("POLIZAS_S3_PREFIJO", ""),
            endpoint_url=os.getenv("POLIZAS_S3_ENDPOINT_URL") or None,
        )
    except Exception as error:
        logger.warning("No se pudo preparar S3 (%s); se usa solo el disco", _describir(error))
        return disco
    return AlmacenConRespaldo(principal=s3, respaldo=disco)

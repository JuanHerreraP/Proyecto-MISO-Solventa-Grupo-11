"""Evidencias del siniestro: fotos y videos con ubicación (HU04) e integridad (EC10).

Reglas:

- Solo el cliente titular adjunta evidencias, y solo mientras el siniestro está abierto
  (REGISTRADO o EN_EVALUACION).
- Se aceptan fotos JPEG o PNG (hasta 10 MB) y videos MP4 o 3GP (hasta 50 MB), máximo 10 por
  siniestro. El contenido debe corresponder al tipo declarado.
- La huella SHA-256 se calcula en el servidor. Si la app declara la suya y no coincide, el
  archivo se alteró en el camino y se rechaza.
- Reenviar el mismo archivo para el mismo siniestro devuelve la evidencia ya registrada: la
  app reintenta un borrador sin duplicar evidencias.
- La ubicación (latitud y longitud, juntas) y la fecha/hora de captura son opcionales: sin
  permiso de ubicación la evidencia se acepta sin geoetiqueta.
- Las evidencias son inmutables: no hay forma de modificarlas ni borrarlas. El archivo se
  guarda bajo una clave derivada de su huella y en cada lectura se vuelve a calcular la huella;
  si no coincide, la evidencia se reporta como alterada.
- Cada carga, consulta, descarga y falla de integridad queda en la bitácora de auditoría con
  el autor, su rol, la IP y la fecha.
"""

import hashlib
import hmac
import logging
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, computed_field, model_validator

from app.identidad.modelos import Rol
from app.polizas.almacenamiento import (
    AlmacenConRespaldo,
    AlmacenDocumentos,
    AlmacenEnDisco,
    AlmacenS3,
)
from app.siniestros.modelos import EstadoSiniestro, Siniestro
from app.siniestros.repositorio import RepositorioSiniestros

if TYPE_CHECKING:
    from app.siniestros.repositorio_evidencias import (
        RepositorioAuditoriaEvidencias,
        RepositorioEvidencias,
    )

logger = logging.getLogger(__name__)

DIRECTORIO_EVIDENCIAS = "./evidencias_siniestros"
PREFIJO_CLAVE = "evidencias-siniestros"
MEGABYTE = 1024 * 1024
LIMITE_FOTO_BYTES = 10 * MEGABYTE
LIMITE_VIDEO_BYTES = 50 * MEGABYTE
LIMITE_LECTURA_BYTES = LIMITE_VIDEO_BYTES
MAXIMO_EVIDENCIAS = 10
# Tolerancia para relojes de celular adelantados.
TOLERANCIA_RELOJ = timedelta(minutes=5)

ESTADOS_ABIERTOS = (EstadoSiniestro.REGISTRADO, EstadoSiniestro.EN_EVALUACION)
ROLES_REVISION = (Rol.OPERACIONES_SINIESTROS.value, Rol.ANALISTA_CUMPLIMIENTO.value)


class TipoEvidencia(str, Enum):
    FOTO = "FOTO"
    VIDEO = "VIDEO"


@dataclass(frozen=True)
class FormatoEvidencia:
    tipo: TipoEvidencia
    extension: str
    limite_bytes: int


FORMATOS: dict[str, FormatoEvidencia] = {
    "image/jpeg": FormatoEvidencia(TipoEvidencia.FOTO, "jpg", LIMITE_FOTO_BYTES),
    "image/png": FormatoEvidencia(TipoEvidencia.FOTO, "png", LIMITE_FOTO_BYTES),
    "video/mp4": FormatoEvidencia(TipoEvidencia.VIDEO, "mp4", LIMITE_VIDEO_BYTES),
    "video/3gpp": FormatoEvidencia(TipoEvidencia.VIDEO, "3gp", LIMITE_VIDEO_BYTES),
}


class AccionEvidencia(str, Enum):
    CARGA = "CARGA"
    CONSULTA = "CONSULTA"
    DESCARGA = "DESCARGA"
    INTEGRIDAD_FALLIDA = "INTEGRIDAD_FALLIDA"
    CONSULTA_AUDITORIA = "CONSULTA_AUDITORIA"


class EvidenciaSiniestro(BaseModel):
    """Metadatos de una foto o video adjunto a un siniestro."""

    model_config = ConfigDict(extra="forbid")

    evidencia_id: str = Field(min_length=1, max_length=50)
    siniestro_id: str = Field(min_length=1, max_length=50)
    cliente_id: str = Field(min_length=1, max_length=50)
    tipo: TipoEvidencia
    tipo_contenido: str = Field(min_length=1, max_length=50)
    nombre_archivo: str | None = Field(default=None, max_length=120)
    tamano_bytes: int = Field(gt=0)
    huella_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    capturada_en: AwareDatetime | None = None
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    precision_metros: float | None = Field(default=None, ge=0)
    subida_por: str = Field(min_length=1, max_length=50)
    subida_en: AwareDatetime
    # Ubicación interna del archivo: no sale en la respuesta.
    clave_almacenamiento: str = Field(min_length=1, max_length=200, exclude=True)

    @computed_field
    @property
    def geoetiquetada(self) -> bool:
        return self.latitud is not None and self.longitud is not None


class DatosCaptura(BaseModel):
    """Lo que la app sabe de la captura. Todo es opcional."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    capturada_en: AwareDatetime | None = None
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    precision_metros: float | None = Field(default=None, ge=0, le=100_000)
    nombre_archivo: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def _ubicacion_completa(self) -> "DatosCaptura":
        if self.capturada_en is not None:
            # Se guarda en UTC: la base no conserva el desfase horario del celular.
            self.capturada_en = self.capturada_en.astimezone(UTC)
        if (self.latitud is None) != (self.longitud is None):
            raise ValueError("La ubicación necesita latitud y longitud juntas.")
        if self.precision_metros is not None and self.latitud is None:
            raise ValueError("La precisión solo aplica con una ubicación.")
        return self


class AccesoEvidencia(BaseModel):
    """Una fila de la bitácora de auditoría de evidencias (EC10)."""

    model_config = ConfigDict(extra="forbid")

    siniestro_id: str
    evidencia_id: str | None = None
    accion: AccionEvidencia
    actor_id: str
    rol: str
    ip: str | None = None
    user_agent: str | None = None
    detalle: str | None = None
    ocurrido_en: AwareDatetime


@dataclass(frozen=True)
class Actor:
    """Quién hace la operación, para autorizar y para la bitácora."""

    id: str
    rol: str
    ip: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class ResultadoCarga:
    """`creada` es False cuando el mismo archivo ya estaba adjunto al siniestro."""

    evidencia: EvidenciaSiniestro
    creada: bool


class ErrorEvidencia(Exception):
    """Error de negocio con un código estable para la API."""

    codigo = "EVIDENCIA_INVALIDA"
    mensaje = "La evidencia no es válida."

    def __init__(self, mensaje: str | None = None):
        super().__init__(mensaje or self.mensaje)
        if mensaje is not None:
            self.mensaje = mensaje


class SiniestroNoEncontrado(ErrorEvidencia):
    codigo = "SINIESTRO_NO_ENCONTRADO"
    mensaje = "El siniestro no existe."


class EvidenciaNoEncontrada(ErrorEvidencia):
    codigo = "EVIDENCIA_NO_ENCONTRADA"
    mensaje = "La evidencia no existe."


class AccesoDenegado(ErrorEvidencia):
    codigo = "ACCESS_DENIED"
    mensaje = "No tiene permisos sobre las evidencias de este siniestro."


class SiniestroCerrado(ErrorEvidencia):
    codigo = "SINIESTRO_CERRADO"
    mensaje = "El siniestro ya fue evaluado y no admite nuevas evidencias."


class LimiteEvidencias(ErrorEvidencia):
    codigo = "LIMITE_EVIDENCIAS"
    mensaje = f"El siniestro ya tiene {MAXIMO_EVIDENCIAS} evidencias, el máximo permitido."


class TipoNoPermitido(ErrorEvidencia):
    codigo = "TIPO_NO_PERMITIDO"
    mensaje = "Solo se aceptan fotos JPEG o PNG y videos MP4 o 3GP."


class ArchivoVacio(ErrorEvidencia):
    codigo = "ARCHIVO_VACIO"
    mensaje = "El archivo está vacío."


class ArchivoDemasiadoGrande(ErrorEvidencia):
    codigo = "ARCHIVO_DEMASIADO_GRANDE"
    mensaje = "La foto puede pesar hasta 10 MB y el video hasta 50 MB."


class ContenidoNoCoincide(ErrorEvidencia):
    codigo = "CONTENIDO_NO_COINCIDE"
    mensaje = "El contenido del archivo no corresponde al tipo declarado."


class HuellaNoCoincide(ErrorEvidencia):
    codigo = "HUELLA_NO_COINCIDE"
    mensaje = "El archivo recibido no coincide con la huella enviada por la app."


class FechaCapturaInvalida(ErrorEvidencia):
    codigo = "FECHA_CAPTURA_INVALIDA"
    mensaje = "La fecha de captura no puede estar en el futuro."


class EvidenciaAlterada(ErrorEvidencia):
    codigo = "EVIDENCIA_ALTERADA"
    mensaje = "El archivo almacenado no coincide con la huella registrada."


class EvidenciaDuplicada(Exception):
    """Otro envío simultáneo ya registró el mismo archivo para el siniestro."""


def huella_sha256(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def normalizar_tipo(tipo_contenido: str | None) -> str | None:
    """Content-Type admitido, sin parámetros y en minúsculas; None si no se admite."""
    if not tipo_contenido:
        return None
    tipo = tipo_contenido.split(";", 1)[0].strip().lower()
    return tipo if tipo in FORMATOS else None


def contenido_corresponde(tipo_contenido: str, contenido: bytes) -> bool:
    """Revisa la firma del archivo: el Content-Type lo declara el cliente y no basta."""
    if tipo_contenido == "image/jpeg":
        return contenido.startswith(b"\xff\xd8\xff")
    if tipo_contenido == "image/png":
        return contenido.startswith(b"\x89PNG\r\n\x1a\n")
    if tipo_contenido in ("video/mp4", "video/3gpp"):
        return len(contenido) >= 12 and contenido[4:8] == b"ftyp"
    return False


def nombre_seguro(nombre: str | None) -> str | None:
    """Solo el nombre del archivo, sin rutas, recortado. Es informativo."""
    if not nombre:
        return None
    base = os.path.basename(nombre.replace("\\", "/")).strip()
    return base[:120] or None


class ServicioEvidencias:
    def __init__(
        self,
        siniestros: RepositorioSiniestros,
        evidencias: "RepositorioEvidencias",
        auditoria: "RepositorioAuditoriaEvidencias",
        almacen: AlmacenDocumentos,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = lambda: f"EVI-{uuid.uuid4()}",
    ):
        self._siniestros = siniestros
        self._evidencias = evidencias
        self._auditoria = auditoria
        self._almacen = almacen
        self._reloj = reloj
        self._generar_id = generar_id

    def adjuntar(
        self,
        actor: Actor,
        siniestro_id: str,
        contenido: bytes,
        tipo_contenido: str | None,
        datos: DatosCaptura,
        huella_declarada: str | None = None,
    ) -> ResultadoCarga:
        siniestro = self._siniestro_del_titular(actor, siniestro_id)
        if siniestro.estado not in ESTADOS_ABIERTOS:
            raise SiniestroCerrado()

        tipo_normalizado = normalizar_tipo(tipo_contenido)
        if tipo_normalizado is None:
            raise TipoNoPermitido()
        formato = FORMATOS[tipo_normalizado]
        if not contenido:
            raise ArchivoVacio()
        if len(contenido) > formato.limite_bytes:
            raise ArchivoDemasiadoGrande()
        if not contenido_corresponde(tipo_normalizado, contenido):
            raise ContenidoNoCoincide()

        huella = huella_sha256(contenido)
        if huella_declarada is not None and not hmac.compare_digest(
            huella, huella_declarada.strip().lower()
        ):
            raise HuellaNoCoincide()

        ahora = self._reloj()
        if datos.capturada_en is not None and datos.capturada_en > ahora + TOLERANCIA_RELOJ:
            raise FechaCapturaInvalida()

        # El mismo archivo ya adjunto: es un reintento, no una evidencia nueva.
        previa = self._evidencias.obtener_por_huella(siniestro_id, huella)
        if previa is not None:
            return ResultadoCarga(evidencia=previa, creada=False)
        if self._evidencias.contar(siniestro_id) >= MAXIMO_EVIDENCIAS:
            raise LimiteEvidencias()

        clave = f"{PREFIJO_CLAVE}/{siniestro_id}/{huella}.{formato.extension}"
        # Clave derivada del contenido: escribirla otra vez con lo mismo es inocuo.
        self._almacen.guardar(clave, contenido, tipo_normalizado)

        evidencia = EvidenciaSiniestro(
            evidencia_id=self._generar_id(),
            siniestro_id=siniestro_id,
            cliente_id=siniestro.cliente_id,
            tipo=formato.tipo,
            tipo_contenido=tipo_normalizado,
            nombre_archivo=nombre_seguro(datos.nombre_archivo),
            tamano_bytes=len(contenido),
            huella_sha256=huella,
            capturada_en=datos.capturada_en,
            latitud=datos.latitud,
            longitud=datos.longitud,
            precision_metros=datos.precision_metros,
            subida_por=actor.id,
            subida_en=ahora,
            clave_almacenamiento=clave,
        )
        try:
            self._evidencias.guardar(evidencia)
        except EvidenciaDuplicada:
            previa = self._evidencias.obtener_por_huella(siniestro_id, huella)
            if previa is None:
                raise
            return ResultadoCarga(evidencia=previa, creada=False)

        detalle = f"{evidencia.tipo.value};{evidencia.tamano_bytes} bytes;sha256:{huella}"
        if not evidencia.geoetiquetada:
            detalle += ";sin ubicación"
        self._auditar(actor, siniestro_id, AccionEvidencia.CARGA, evidencia.evidencia_id, detalle)
        return ResultadoCarga(evidencia=evidencia, creada=True)

    def listar(self, actor: Actor, siniestro_id: str) -> list[EvidenciaSiniestro]:
        self._siniestro_visible(actor, siniestro_id)
        evidencias = self._evidencias.listar_por_siniestro(siniestro_id)
        self._auditar(
            actor, siniestro_id, AccionEvidencia.CONSULTA, None, f"{len(evidencias)} evidencias"
        )
        return evidencias

    def leer(
        self, actor: Actor, siniestro_id: str, evidencia_id: str
    ) -> tuple[EvidenciaSiniestro, bytes]:
        """Devuelve el archivo solo si su huella coincide con la registrada al cargarlo."""
        self._siniestro_visible(actor, siniestro_id)
        evidencia = self._evidencias.obtener(evidencia_id)
        if evidencia is None or evidencia.siniestro_id != siniestro_id:
            raise EvidenciaNoEncontrada()

        contenido = self._almacen.leer(evidencia.clave_almacenamiento)
        if contenido is None:
            self._falla_integridad(actor, evidencia, "archivo ausente en el almacén")
        elif not hmac.compare_digest(huella_sha256(contenido), evidencia.huella_sha256):
            self._falla_integridad(actor, evidencia, "la huella del archivo no coincide")

        self._auditar(
            actor, siniestro_id, AccionEvidencia.DESCARGA, evidencia_id, "huella verificada"
        )
        return evidencia, contenido

    def auditoria(self, actor: Actor, siniestro_id: str) -> list[AccesoEvidencia]:
        if actor.rol not in ROLES_REVISION:
            raise AccesoDenegado()
        if self._siniestros.obtener(siniestro_id) is None:
            raise SiniestroNoEncontrado()
        registros = self._auditoria.listar_por_siniestro(siniestro_id)
        self._auditar(actor, siniestro_id, AccionEvidencia.CONSULTA_AUDITORIA, None, None)
        return registros

    def _siniestro_del_titular(self, actor: Actor, siniestro_id: str) -> Siniestro:
        if actor.rol != Rol.CLIENTE.value:
            raise AccesoDenegado("Solo el cliente asegurado puede adjuntar evidencias.")
        siniestro = self._siniestros.obtener(siniestro_id)
        # Uno ajeno responde igual que uno inexistente: no se revela que existe.
        if siniestro is None or siniestro.cliente_id != actor.id:
            raise SiniestroNoEncontrado()
        return siniestro

    def _siniestro_visible(self, actor: Actor, siniestro_id: str) -> Siniestro:
        if actor.rol == Rol.CLIENTE.value:
            return self._siniestro_del_titular(actor, siniestro_id)
        if actor.rol not in ROLES_REVISION:
            raise AccesoDenegado()
        siniestro = self._siniestros.obtener(siniestro_id)
        if siniestro is None:
            raise SiniestroNoEncontrado()
        return siniestro

    def _falla_integridad(self, actor: Actor, evidencia: EvidenciaSiniestro, motivo: str) -> None:
        logger.error(
            "Evidencia %s del siniestro %s alterada: %s",
            evidencia.evidencia_id,
            evidencia.siniestro_id,
            motivo,
        )
        self._auditar(
            actor,
            evidencia.siniestro_id,
            AccionEvidencia.INTEGRIDAD_FALLIDA,
            evidencia.evidencia_id,
            motivo,
        )
        raise EvidenciaAlterada()

    def _auditar(
        self,
        actor: Actor,
        siniestro_id: str,
        accion: AccionEvidencia,
        evidencia_id: str | None,
        detalle: str | None,
    ) -> None:
        self._auditoria.registrar(
            AccesoEvidencia(
                siniestro_id=siniestro_id,
                evidencia_id=evidencia_id,
                accion=accion,
                actor_id=actor.id,
                rol=actor.rol,
                ip=actor.ip,
                user_agent=actor.user_agent[:300] if actor.user_agent else None,
                detalle=detalle,
                ocurrido_en=self._reloj(),
            )
        )


def crear_almacen_evidencias() -> AlmacenDocumentos:
    """Disco si no hay bucket; si lo hay, el bucket de pólizas con el disco como respaldo.

    Variables: `SINIESTROS_EVIDENCIAS_DIR` (carpeta del disco) y las mismas de S3 que el PDF de
    la póliza (`POLIZAS_S3_BUCKET`, `POLIZAS_S3_PREFIJO`, `POLIZAS_S3_ENDPOINT_URL`). Las
    evidencias quedan bajo `evidencias-siniestros/` dentro del bucket.
    """
    disco = AlmacenEnDisco(os.getenv("SINIESTROS_EVIDENCIAS_DIR") or DIRECTORIO_EVIDENCIAS)
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
        logger.warning(
            "No se pudo preparar S3 (%s); evidencias solo en disco", type(error).__name__
        )
        return disco
    return AlmacenConRespaldo(principal=s3, respaldo=disco)

"""Datos de prueba para las evidencias de siniestro (HU04 / EC10)."""

import hashlib
from datetime import UTC, datetime, time
from decimal import Decimal

from app.polizas.almacenamiento import AlmacenEnMemoria
from app.siniestros.evidencias import Actor, ServicioEvidencias
from app.siniestros.modelos import EstadoSiniestro, OrigenSiniestro, Siniestro
from app.siniestros.repositorio import RepositorioSiniestrosEnMemoria
from app.siniestros.repositorio_evidencias import (
    RepositorioAuditoriaEvidenciasEnMemoria,
    RepositorioEvidenciasEnMemoria,
)

AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)
CLIENTE = Actor(id="CLI-001", rol="CLIENTE", ip="10.0.0.5", user_agent="okhttp/4.12.0")
OTRO_CLIENTE = Actor(id="CLI-999", rol="CLIENTE")
OPERADOR = Actor(id="OPS-1", rol="OPERACIONES_SINIESTROS", ip="10.0.0.9")
AUDITOR = Actor(id="AUD-1", rol="ANALISTA_CUMPLIMIENTO")
ASESOR = Actor(id="ASE-1", rol="ASESOR_VENTAS")

# Firmas mínimas válidas de cada formato.
JPEG = b"\xff\xd8\xff\xe0" + b"foto-del-siniestro" * 10
PNG = b"\x89PNG\r\n\x1a\n" + b"captura" * 10
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"video" * 20
GP3 = b"\x00\x00\x00\x14ftyp3gp4" + b"video" * 20


def sha(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def siniestro(**cambios) -> Siniestro:
    datos = {
        "siniestro_id": "SIN-1",
        "cliente_id": "CLI-001",
        "poliza_id": "POL-1",
        "origen": OrigenSiniestro.MANUAL,
        "estado": EstadoSiniestro.REGISTRADO,
        "fecha_evento": datetime(2026, 10, 20).date(),
        "hora_evento": time(18, 30),
        "lugar": "Aeropuerto El Dorado",
        "descripcion": "Se rompió la pantalla del celular en el aeropuerto.",
        "estimacion_danos": Decimal("850000"),
        "registrado_por": "CLI-001",
        "registrado_en": AHORA,
    }
    datos.update(cambios)
    return Siniestro(**datos)


class Entorno:
    """Servicio de evidencias con repositorios y almacén en memoria."""

    def __init__(self):
        self.siniestros = RepositorioSiniestrosEnMemoria()
        self.siniestros.guardar(siniestro())
        self.evidencias = RepositorioEvidenciasEnMemoria()
        self.auditoria = RepositorioAuditoriaEvidenciasEnMemoria()
        self.almacen = AlmacenEnMemoria()
        self._consecutivo = 0
        self.servicio = ServicioEvidencias(
            self.siniestros,
            self.evidencias,
            self.auditoria,
            self.almacen,
            reloj=lambda: AHORA,
            generar_id=self._siguiente_id,
        )

    def _siguiente_id(self) -> str:
        self._consecutivo += 1
        return f"EVI-{self._consecutivo}"

    def acciones(self) -> list[str]:
        return [r.accion.value for r in self.auditoria.registros]

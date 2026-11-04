"""Casos de uso del endoso de la póliza (HU16 / BPM-68).

- El cliente modifica solo sus pólizas. Una póliza ajena se trata como inexistente (EC08).
- El asesor de ventas puede asistir al cliente solo en pólizas de ventas en las que participó.
- Simular calcula la propuesta sin guardar nada; confirmar la vuelve a calcular en el
  servidor, emite el PDF del endoso, y guarda endoso y póliza en una sola transacción.
- Confirmar es idempotente con la clave `Idempotency-Key`: repetir la misma solicitud
  (doble clic, respuesta perdida) devuelve el mismo endoso; reutilizar la clave con otra
  solicitud se rechaza.
- Cada endoso registra quién lo pidió, desde qué IP, la huella de la solicitud y la del PDF:
  todo cambio a una póliza emitida queda atribuible a un autor (EC10).
"""

import hashlib
import hmac
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.cotizaciones.repositorio import RepositorioCotizaciones
from app.identidad.modelos import Rol
from app.polizas.almacenamiento import AlmacenDocumentos, DocumentoInmutable
from app.polizas.dominio.endosos import (
    Endoso,
    PropuestaEndoso,
    SolicitudModificacion,
    endoso_id_de,
    proponer_endoso,
)
from app.polizas.dominio.modelos import Poliza, hoy_en_colombia
from app.polizas.emision import (
    AccesoDenegado,
    DocumentoAlterado,
    DocumentoDescargable,
    DocumentoNoDisponible,
)
from app.polizas.pdf import generar_pdf_endoso
from app.polizas.repositorio import RepositorioPolizas
from app.polizas.repositorio_endosos import EndosoConcurrente, RepositorioEndosos
from app.polizas.servicio import PolizaNoEncontrada

logger = logging.getLogger(__name__)

ROLES_QUE_MODIFICAN = frozenset({Rol.CLIENTE, Rol.ASESOR_VENTAS})
_HUELLA_PROVISIONAL = "0" * 64


class EndosoNoEncontrado(Exception):
    pass


class ClaveIdempotenciaReutilizada(Exception):
    """La misma clave llegó con una solicitud distinta a la que ya se confirmó."""


@dataclass(frozen=True)
class Solicitante:
    actor_id: str
    rol: Rol
    ip: str | None = None
    user_agent: str | None = None


def huella_de_solicitud(poliza_id: str, solicitud: SolicitudModificacion) -> str:
    canonica = json.dumps(
        {"poliza_id": poliza_id, "solicitud": solicitud.model_dump(mode="json")},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonica.encode("utf-8")).hexdigest()


def _recortar(valor: str | None, largo: int) -> str | None:
    return valor[:largo] if valor else None


class ServicioEndosos:
    def __init__(
        self,
        polizas: RepositorioPolizas,
        endosos: RepositorioEndosos,
        cotizaciones: RepositorioCotizaciones,
        almacen: AlmacenDocumentos,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self._polizas = polizas
        self._endosos = endosos
        self._cotizaciones = cotizaciones
        self._almacen = almacen
        self._reloj = reloj

    # --- Consulta -----------------------------------------------------------------------

    def poliza(self, solicitante: Solicitante, poliza_id: str) -> Poliza:
        """La póliza, si el solicitante puede verla y modificarla."""
        if solicitante.rol is Rol.CLIENTE:
            poliza = self._polizas.obtener_del_cliente(poliza_id, solicitante.actor_id)
            if poliza is None:
                raise PolizaNoEncontrada(poliza_id)
            return poliza
        if solicitante.rol is Rol.ASESOR_VENTAS:
            poliza = self._polizas.obtener(poliza_id)
            if poliza is None:
                raise PolizaNoEncontrada(poliza_id)
            cotizacion = (
                self._cotizaciones.obtener(poliza.cotizacion_id) if poliza.cotizacion_id else None
            )
            if cotizacion is None or cotizacion.asesor_id != solicitante.actor_id:
                raise AccesoDenegado(poliza_id)
            return poliza
        raise AccesoDenegado(poliza_id)

    def listar(self, solicitante: Solicitante, poliza_id: str) -> list[Endoso]:
        poliza = self.poliza(solicitante, poliza_id)
        return self._endosos.listar_por_poliza(poliza.poliza_id)

    # --- Simulación y confirmación ------------------------------------------------------

    def simular(
        self, solicitante: Solicitante, poliza_id: str, solicitud: SolicitudModificacion
    ) -> PropuestaEndoso:
        poliza = self.poliza(solicitante, poliza_id)
        return proponer_endoso(poliza, solicitud, hoy_en_colombia(self._reloj()))

    def confirmar(
        self,
        solicitante: Solicitante,
        poliza_id: str,
        solicitud: SolicitudModificacion,
        clave_idempotencia: str | None = None,
    ) -> tuple[Endoso, bool]:
        """Registra el endoso. Devuelve el endoso y si se creó en esta llamada."""

        poliza = self.poliza(solicitante, poliza_id)
        huella = huella_de_solicitud(poliza.poliza_id, solicitud)

        if clave_idempotencia:
            previo = self._endosos.por_clave(poliza.poliza_id, clave_idempotencia)
            if previo is not None:
                if not hmac.compare_digest(previo.huella_solicitud, huella):
                    raise ClaveIdempotenciaReutilizada(clave_idempotencia)
                return previo, False

        ahora = self._reloj()
        propuesta = proponer_endoso(poliza, solicitud, hoy_en_colombia(ahora))
        numero = len(self._endosos.listar_por_poliza(poliza.poliza_id)) + 1
        endoso_id = endoso_id_de(poliza.poliza_id, numero)
        # La clave lleva la huella de la solicitud y el instante: si un intento anterior dejó
        # un PDF sin alcanzar a registrar el endoso, no bloquea los siguientes.
        clave_documento = (
            f"endosos/{poliza.poliza_id}/{endoso_id}-{huella[:12]}-"
            f"{int(ahora.timestamp() * 1000)}.pdf"
        )

        borrador = Endoso(
            endoso_id=endoso_id,
            poliza_id=poliza.poliza_id,
            numero_endoso=numero,
            tipo=propuesta.tipo,
            solicitado_por=solicitante.actor_id,
            rol_solicitante=solicitante.rol.value,
            clave_idempotencia=clave_idempotencia or None,
            huella_solicitud=huella,
            ip_solicitante=_recortar(solicitante.ip, 64),
            user_agent=_recortar(solicitante.user_agent, 300),
            fecha_efecto=propuesta.fecha_efecto,
            dias_vigencia=propuesta.dias_vigencia,
            dias_restantes=propuesta.dias_restantes,
            prima_anterior=propuesta.prima_anterior,
            ajuste_prima=propuesta.ajuste_prima,
            prima_nueva=propuesta.prima_nueva,
            moneda=propuesta.moneda,
            cambios=propuesta.cambios,
            coberturas_opcionales=propuesta.coberturas_opcionales,
            beneficiarios=propuesta.beneficiarios,
            clave_documento=clave_documento,
            huella_documento=_HUELLA_PROVISIONAL,
            tamano_documento=1,
            creado_en=ahora,
        )
        contenido = generar_pdf_endoso(poliza, borrador)
        try:
            self._almacen.guardar(clave_documento, contenido)
        except DocumentoInmutable:
            # Ya hay un PDF distinto con ese número: otra confirmación ganó la carrera.
            raise EndosoConcurrente(poliza.poliza_id) from None

        endoso = borrador.model_copy(
            update={
                "huella_documento": hashlib.sha256(contenido).hexdigest(),
                "tamano_documento": len(contenido),
            }
        )
        actualizada = poliza.model_copy(
            update={
                "coberturas_opcionales": propuesta.coberturas_opcionales,
                "beneficiarios": propuesta.beneficiarios,
                "prima_total": propuesta.prima_nueva,
            }
        )
        self._endosos.registrar(endoso, actualizada)
        logger.info(
            "Endoso %s registrado sobre %s por %s (%s)",
            endoso.endoso_id,
            poliza.poliza_id,
            solicitante.actor_id,
            solicitante.rol.value,
        )
        return endoso, True

    # --- Documento ----------------------------------------------------------------------

    def documento(
        self, solicitante: Solicitante, poliza_id: str, endoso_id: str
    ) -> DocumentoDescargable:
        poliza = self.poliza(solicitante, poliza_id)
        endoso = self._endosos.obtener(poliza.poliza_id, endoso_id)
        if endoso is None:
            raise EndosoNoEncontrado(endoso_id)
        contenido = self._almacen.leer(endoso.clave_documento)
        if contenido is None:
            raise DocumentoNoDisponible(endoso_id)
        if not hmac.compare_digest(hashlib.sha256(contenido).hexdigest(), endoso.huella_documento):
            logger.error("El documento del endoso %s no coincide con su huella", endoso_id)
            raise DocumentoAlterado(endoso_id)
        return DocumentoDescargable(
            nombre_archivo=f"endoso-{poliza.numero_poliza}-{endoso.numero_endoso:03d}.pdf",
            contenido=contenido,
            huella_sha256=endoso.huella_documento,
        )

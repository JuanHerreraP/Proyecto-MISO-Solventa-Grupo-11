"""Casos de uso de la billetera digital de pólizas (HU07 / BPM-31).

- El cliente solo ve las pólizas cuyo titular es él (EC08). Una póliza ajena se trata igual
  que una inexistente, para no revelar que existe.
- Las pólizas vencidas o canceladas se marcan como inactivas y van después de las vigentes.
- Compartir genera un enlace temporal. El token tiene 256 bits de azar y en la base solo se
  guarda su huella SHA-256: quien lea la base no puede reconstruir enlaces válidos.
"""

import hashlib
import os
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.polizas.dominio.modelos import EnlaceCertificado, hoy_en_colombia
from app.polizas.repositorio import RepositorioEnlaces, RepositorioPolizas
from app.polizas.vistas import (
    Billetera,
    CertificadoCompartido,
    CertificadoPoliza,
    EnlaceCompartido,
    a_certificado,
    a_certificado_compartido,
    a_poliza_en_billetera,
)

HORAS_ENLACE_POR_DEFECTO = 24
RUTA_CERTIFICADO_COMPARTIDO = "/api/v1/certificados-compartidos"


class PolizaNoEncontrada(Exception):
    pass


class EnlaceNoEncontrado(Exception):
    pass


class EnlaceVencido(Exception):
    pass


def horas_vigencia_enlace() -> int:
    valor = os.getenv("BILLETERA_ENLACE_HORAS", str(HORAS_ENLACE_POR_DEFECTO))
    try:
        horas = int(valor)
    except ValueError:
        return HORAS_ENLACE_POR_DEFECTO
    return horas if 1 <= horas <= 168 else HORAS_ENLACE_POR_DEFECTO


def huella(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ServicioBilletera:
    def __init__(
        self,
        polizas: RepositorioPolizas,
        enlaces: RepositorioEnlaces,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        horas_enlace: int | None = None,
        generar_token: Callable[[], str] = lambda: secrets.token_urlsafe(32),
    ):
        self._polizas = polizas
        self._enlaces = enlaces
        self._reloj = reloj
        self._horas_enlace = horas_enlace if horas_enlace is not None else horas_vigencia_enlace()
        self._generar_token = generar_token

    def billetera(self, cliente_id: str) -> Billetera:
        hoy = hoy_en_colombia(self._reloj())
        vistas = [
            a_poliza_en_billetera(p, hoy) for p in self._polizas.listar_por_cliente(cliente_id)
        ]
        # Vigentes primero (las que vencen antes arriba); luego inactivas, la más reciente arriba.
        vigentes = sorted(
            (v for v in vistas if v.activa), key=lambda v: (v.fecha_fin, v.numero_poliza)
        )
        inactivas = sorted(
            (v for v in vistas if not v.activa),
            key=lambda v: (v.fecha_fin, v.numero_poliza),
            reverse=True,
        )
        return Billetera(
            polizas=[*vigentes, *inactivas],
            total_vigentes=len(vigentes),
            total_inactivas=len(inactivas),
        )

    def certificado(self, cliente_id: str, poliza_id: str) -> CertificadoPoliza:
        poliza = self._polizas.obtener_del_cliente(poliza_id, cliente_id)
        if poliza is None:
            raise PolizaNoEncontrada(poliza_id)
        return a_certificado(poliza, hoy_en_colombia(self._reloj()))

    def compartir(self, cliente_id: str, poliza_id: str, url_base: str) -> EnlaceCompartido:
        poliza = self._polizas.obtener_del_cliente(poliza_id, cliente_id)
        if poliza is None:
            raise PolizaNoEncontrada(poliza_id)

        ahora = self._reloj()
        token = self._generar_token()
        enlace = EnlaceCertificado(
            huella_token=huella(token),
            poliza_id=poliza.poliza_id,
            cliente_id=cliente_id,
            creado_en=ahora,
            expira_en=ahora + timedelta(hours=self._horas_enlace),
        )
        self._enlaces.guardar(enlace)
        return EnlaceCompartido(
            url=f"{url_base.rstrip('/')}{RUTA_CERTIFICADO_COMPARTIDO}/{token}",
            expira_en=enlace.expira_en,
        )

    def certificado_compartido(self, token: str) -> CertificadoCompartido:
        enlace = self._enlaces.obtener(huella(token))
        if enlace is None:
            raise EnlaceNoEncontrado()

        ahora = self._reloj()
        if not enlace.vigente_en(ahora):
            raise EnlaceVencido()

        poliza = self._polizas.obtener(enlace.poliza_id)
        # La póliza debe seguir siendo del mismo titular que generó el enlace.
        if poliza is None or poliza.cliente_id != enlace.cliente_id:
            raise EnlaceNoEncontrado()
        return a_certificado_compartido(poliza, hoy_en_colombia(ahora), enlace.expira_en)

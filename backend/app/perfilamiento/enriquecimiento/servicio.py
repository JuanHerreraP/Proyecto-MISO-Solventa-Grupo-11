"""Caso de uso: enriquecer el perfil del cliente con las fuentes externas autorizadas."""

import asyncio
import logging
import time
from collections.abc import Callable, Sequence
from datetime import datetime, timezone

from app.perfilamiento.dominio.modelos import OrigenSenales, SenalesPerfilamiento
from app.perfilamiento.enriquecimiento.modelos import (
    OrigenDato,
    ResultadoEnriquecimiento,
    TipoFuente,
    TrazaFuente,
)
from app.perfilamiento.enriquecimiento.puertos import (
    CacheSenales,
    FuenteExterna,
    FuenteNoDisponible,
    RepositorioConsentimientos,
    SenalesFuente,
)

auditoria = logging.getLogger("solventa.auditoria.enriquecimiento")

TIPOS_REQUERIDOS = (TipoFuente.OPEN_FINANCE, TipoFuente.OPEN_DATA)


class SinConsentimientoVigente(Exception):
    """El cliente no ha dado un consentimiento vigente para consultar sus datos."""


class EnriquecimientoNoDisponible(Exception):
    """Una fuente falló y no hay un dato vigente en caché para reemplazarla."""

    def __init__(self, tipo: TipoFuente, motivo: str):
        super().__init__(f"{tipo.value}: {motivo}")
        self.tipo = tipo
        self.motivo = motivo


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class ServicioEnriquecimiento:
    def __init__(
        self,
        fuentes: Sequence[FuenteExterna],
        cache: CacheSenales,
        consentimientos: RepositorioConsentimientos,
        *,
        tiempo_limite: float,
        reloj: Callable[[], datetime] = _ahora,
    ):
        por_tipo = {fuente.tipo: fuente for fuente in fuentes}
        faltantes = [tipo.value for tipo in TIPOS_REQUERIDOS if tipo not in por_tipo]
        if faltantes:
            raise ValueError(f"Faltan fuentes para: {', '.join(faltantes)}")
        self._fuentes = por_tipo
        self._cache = cache
        self._consentimientos = consentimientos
        self._tiempo_limite = tiempo_limite
        self._reloj = reloj
        self._ultimos: dict[str, ResultadoEnriquecimiento] = {}

    async def enriquecer(self, cliente_id: str, cotizacion_id: str) -> ResultadoEnriquecimiento:
        ahora = self._reloj()
        consentimiento = self._consentimientos.vigente(cliente_id, ahora)
        if consentimiento is None:
            raise SinConsentimientoVigente(cliente_id)

        # Las fuentes se consultan en paralelo: la latencia total es la de la más lenta.
        obtenidos = await asyncio.gather(
            *(self._consultar(cliente_id, tipo) for tipo in TIPOS_REQUERIDOS)
        )
        senales_por_tipo = {
            tipo: senales for tipo, (senales, _) in zip(TIPOS_REQUERIDOS, obtenidos, strict=True)
        }
        trazas = [traza for _, traza in obtenidos]
        desde_cache = any(traza.origen is OrigenDato.CACHE for traza in trazas)

        resultado = ResultadoEnriquecimiento(
            cotizacion_id=cotizacion_id,
            senales=SenalesPerfilamiento(
                cliente_id=cliente_id,
                consentimiento_id=consentimiento.consentimiento_id,
                consentimiento_vigente=True,
                open_finance=senales_por_tipo[TipoFuente.OPEN_FINANCE],
                open_data=senales_por_tipo[TipoFuente.OPEN_DATA],
                origen=OrigenSenales.CACHE if desde_cache else OrigenSenales.FUENTES_EXTERNAS,
            ),
            fuentes=trazas,
            fecha=ahora,
        )
        self._ultimos[cliente_id] = resultado
        return resultado

    def ultimo(self, cliente_id: str) -> ResultadoEnriquecimiento | None:
        return self._ultimos.get(cliente_id)

    async def _consultar(
        self, cliente_id: str, tipo: TipoFuente
    ) -> tuple[SenalesFuente, TrazaFuente]:
        fuente = self._fuentes[tipo]
        inicio = time.perf_counter()
        try:
            senales = await asyncio.wait_for(fuente.consultar(cliente_id), self._tiempo_limite)
        except asyncio.TimeoutError:
            return self._desde_cache(cliente_id, fuente, "tiempo de espera agotado")
        except FuenteNoDisponible as error:
            return self._desde_cache(cliente_id, fuente, error.motivo)

        obtenido_en = self._reloj()
        self._cache.guardar(cliente_id, tipo, senales, obtenido_en)
        traza = TrazaFuente(
            tipo=tipo,
            proveedor=fuente.proveedor,
            origen=OrigenDato.FUENTE_EXTERNA,
            obtenido_en=obtenido_en,
            latencia_ms=round((time.perf_counter() - inicio) * 1000, 3),
        )
        return senales, traza

    def _desde_cache(
        self, cliente_id: str, fuente: FuenteExterna, motivo: str
    ) -> tuple[SenalesFuente, TrazaFuente]:
        """Degradación elegante (EC12): usa el último dato vigente y deja registro."""
        guardado = self._cache.obtener(cliente_id, fuente.tipo)
        if guardado is None:
            auditoria.warning(
                "fuente_no_disponible_sin_cache cliente=%s fuente=%s proveedor=%s motivo=%s",
                cliente_id,
                fuente.tipo.value,
                fuente.proveedor,
                motivo,
            )
            raise EnriquecimientoNoDisponible(fuente.tipo, motivo)

        senales, obtenido_en = guardado
        auditoria.warning(
            "uso_de_cache cliente=%s fuente=%s proveedor=%s motivo=%s dato_del=%s",
            cliente_id,
            fuente.tipo.value,
            fuente.proveedor,
            motivo,
            obtenido_en.isoformat(),
        )
        traza = TrazaFuente(
            tipo=fuente.tipo,
            proveedor=fuente.proveedor,
            origen=OrigenDato.CACHE,
            obtenido_en=obtenido_en,
            motivo_cache=motivo,
        )
        return senales, traza

"""Personalización de la prima con un perfil y consentimiento vigentes (BPM-155)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from app.cotizaciones.dominio.modelos import CoberturaPrincipal
from app.cotizaciones.dominio.rating import (
    PRECISION_MONEDA,
    PRIMA_MINIMA,
    ResultadoTarifaBase,
)
from app.perfilamiento.dominio.modelos import Dictamen, PerfilRiesgo
from app.perfilamiento.enriquecimiento.puertos import RepositorioConsentimientos
from app.perfilamiento.repositorio import RepositorioPerfiles


class RiesgoNoAsegurableError(Exception):
    """El perfil vigente fue rechazado y no permite ofrecer una cotización."""


class PerfilRiesgoInvalidoError(Exception):
    """El perfil no contiene un factor de riesgo válido para personalizar la prima."""


@dataclass(frozen=True)
class ResultadoPrecioCotizacion:
    """Precio final y trazabilidad de la personalización aplicada.

    ``prima_total`` representa el costo total de la cobertura. La periodicidad y
    las cuotas de cobro se definirán al emitir la póliza, sin alterar este cálculo.
    """

    prima_base: Decimal
    prima_total: Decimal
    cobertura_principal: CoberturaPrincipal
    personalizada: bool
    factor_riesgo: Decimal
    perfil_riesgo_id: str | None
    consentimiento_id: str | None
    version_tarifas: str
    version_reglas: str | None


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class ServicioPersonalizacionCotizacion:
    """Aplica el perfil únicamente cuando corresponde al consentimiento vigente."""

    def __init__(
        self,
        perfiles: RepositorioPerfiles,
        consentimientos: RepositorioConsentimientos,
        reloj: Callable[[], datetime] = _ahora,
    ):
        self._perfiles = perfiles
        self._consentimientos = consentimientos
        self._reloj = reloj

    def personalizar(
        self,
        cliente_id: str,
        tarifa_base: ResultadoTarifaBase,
    ) -> ResultadoPrecioCotizacion:
        consentimiento = self._consentimientos.vigente(cliente_id, self._reloj())
        perfil = self._perfiles.obtener(cliente_id)

        if (
            consentimiento is None
            or perfil is None
            or perfil.consentimiento_id != consentimiento.consentimiento_id
        ):
            return self._sin_personalizacion(tarifa_base)

        return self._con_perfil(tarifa_base, perfil)

    @staticmethod
    def _sin_personalizacion(
        tarifa_base: ResultadoTarifaBase,
    ) -> ResultadoPrecioCotizacion:
        return ResultadoPrecioCotizacion(
            prima_base=tarifa_base.prima_total,
            prima_total=tarifa_base.prima_total,
            cobertura_principal=tarifa_base.cobertura_principal,
            personalizada=False,
            factor_riesgo=Decimal("1"),
            perfil_riesgo_id=None,
            consentimiento_id=None,
            version_tarifas=tarifa_base.version_tarifas,
            version_reglas=None,
        )

    @staticmethod
    def _con_perfil(
        tarifa_base: ResultadoTarifaBase,
        perfil: PerfilRiesgo,
    ) -> ResultadoPrecioCotizacion:
        if perfil.dictamen is Dictamen.RECHAZADO:
            raise RiesgoNoAsegurableError(perfil.perfil_id)

        if perfil.factor_riesgo is None or perfil.factor_riesgo <= 0:
            raise PerfilRiesgoInvalidoError(perfil.perfil_id)

        factor = Decimal(str(perfil.factor_riesgo))
        prima_personalizada = max(
            tarifa_base.prima_total * factor,
            PRIMA_MINIMA,
        ).quantize(PRECISION_MONEDA, rounding=ROUND_HALF_UP)

        return ResultadoPrecioCotizacion(
            prima_base=tarifa_base.prima_total,
            prima_total=prima_personalizada,
            cobertura_principal=tarifa_base.cobertura_principal,
            personalizada=True,
            factor_riesgo=factor,
            perfil_riesgo_id=perfil.perfil_id,
            consentimiento_id=perfil.consentimiento_id,
            version_tarifas=tarifa_base.version_tarifas,
            version_reglas=perfil.version_reglas,
        )

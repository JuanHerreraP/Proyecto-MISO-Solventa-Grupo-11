"""Arma el servicio de enriquecimiento a partir de variables de entorno.

Si no hay URL configurada para una fuente se usa su simulador en proceso, para poder correr
el backend en local sin proveedores reales.

| Variable                        | Uso                                                     |
|---------------------------------|---------------------------------------------------------|
| OPEN_FINANCE_URL / _TOKEN       | Agregador de Open Finance                               |
| OPEN_DATA_URL / _TOKEN          | Fuente de Open Data                                     |
| FUENTES_TIEMPO_LIMITE_SEGUNDOS  | Tiempo límite por fuente (por defecto 0.25)             |
| FUENTES_PERMITIR_HTTP           | "true" permite http:// (solo desarrollo local)          |
"""

import os
from collections.abc import Mapping

from app.perfilamiento.enriquecimiento.adaptadores import (
    AdaptadorOpenData,
    AdaptadorOpenFinance,
    FuenteSimuladaOpenData,
    FuenteSimuladaOpenFinance,
)
from app.perfilamiento.enriquecimiento.cliente_http import TIEMPO_LIMITE_SEGUNDOS, crear_cliente
from app.perfilamiento.enriquecimiento.memoria import (
    CacheSenalesEnMemoria,
    RepositorioConsentimientosEnMemoria,
)
from app.perfilamiento.enriquecimiento.puertos import FuenteExterna, RepositorioConsentimientos
from app.perfilamiento.enriquecimiento.servicio import ServicioEnriquecimiento


def crear_fuentes(entorno: Mapping[str, str], tiempo_limite: float) -> list[FuenteExterna]:
    permitir_http = entorno.get("FUENTES_PERMITIR_HTTP", "").lower() == "true"

    def cliente(prefijo: str):
        return crear_cliente(
            entorno[f"{prefijo}_URL"],
            entorno.get(f"{prefijo}_TOKEN", ""),
            tiempo_limite=tiempo_limite,
            permitir_http=permitir_http,
        )

    open_finance: FuenteExterna = (
        AdaptadorOpenFinance(cliente("OPEN_FINANCE"))
        if entorno.get("OPEN_FINANCE_URL")
        else FuenteSimuladaOpenFinance()
    )
    open_data: FuenteExterna = (
        AdaptadorOpenData(cliente("OPEN_DATA"))
        if entorno.get("OPEN_DATA_URL")
        else FuenteSimuladaOpenData()
    )
    return [open_finance, open_data]


def crear_servicio(
    consentimientos: RepositorioConsentimientos | None = None,
    entorno: Mapping[str, str] | None = None,
) -> ServicioEnriquecimiento:
    entorno = os.environ if entorno is None else entorno
    tiempo_limite = float(entorno.get("FUENTES_TIEMPO_LIMITE_SEGUNDOS", TIEMPO_LIMITE_SEGUNDOS))
    return ServicioEnriquecimiento(
        fuentes=crear_fuentes(entorno, tiempo_limite),
        cache=CacheSenalesEnMemoria(),
        consentimientos=consentimientos or RepositorioConsentimientosEnMemoria(),
        tiempo_limite=tiempo_limite,
    )

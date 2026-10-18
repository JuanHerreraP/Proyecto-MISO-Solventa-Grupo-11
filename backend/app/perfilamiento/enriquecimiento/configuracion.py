"""Arma el servicio de enriquecimiento a partir de variables de entorno.

Si no hay URL configurada para una fuente se usa su simulador en proceso, para poder correr
el backend en local sin proveedores reales.

| Variable                        | Uso                                                     |
|---------------------------------|---------------------------------------------------------|
| OPEN_FINANCE_URL / _AUDIENCE    | Agregador de Open Finance                               |
| OPEN_DATA_URL / _AUDIENCE       | Fuente de Open Data                                     |
| FUENTES_JWT_PRIVATE_KEY_PATH     | Llave para autenticar a Solventa ante los proveedores  |
| FUENTES_JWT_ISSUER               | Emisor del token firmado (por defecto `solventa`)       |
| FUENTES_TIEMPO_LIMITE_SEGUNDOS  | Tiempo límite por fuente (por defecto 0.25)             |
| FUENTES_PERMITIR_HTTP           | "true" permite http:// (solo desarrollo local)          |
"""

import os
from collections.abc import Mapping
from pathlib import Path

from app.perfilamiento.enriquecimiento.adaptadores import (
    AdaptadorOpenData,
    AdaptadorOpenFinance,
    FuenteSimuladaOpenData,
    FuenteSimuladaOpenFinance,
)
from app.perfilamiento.enriquecimiento.cliente_http import (
    TIEMPO_LIMITE_SEGUNDOS,
    ConfiguracionInsegura,
    crear_cliente,
)
from app.perfilamiento.enriquecimiento.memoria import (
    CacheSenalesEnMemoria,
    RepositorioConsentimientosEnMemoria,
)
from app.perfilamiento.enriquecimiento.puertos import FuenteExterna, RepositorioConsentimientos
from app.perfilamiento.enriquecimiento.servicio import ServicioEnriquecimiento
from app.perfilamiento.enriquecimiento.tokens_proveedores import AutenticacionProveedor


def crear_fuentes(entorno: Mapping[str, str], tiempo_limite: float) -> list[FuenteExterna]:
    permitir_http = entorno.get("FUENTES_PERMITIR_HTTP", "").lower() == "true"

    def cliente(prefijo: str):
        ruta_llave = entorno.get("FUENTES_JWT_PRIVATE_KEY_PATH", "")
        audiencia = entorno.get(f"{prefijo}_AUDIENCE", "")
        if not ruta_llave or not audiencia:
            raise ConfiguracionInsegura(
                "La integración requiere una llave privada y una audiencia configuradas."
            )
        try:
            llave_privada = Path(ruta_llave).read_text()
        except OSError as error:
            raise ConfiguracionInsegura("No fue posible leer la llave de proveedores.") from error

        return crear_cliente(
            entorno[f"{prefijo}_URL"],
            autenticacion=AutenticacionProveedor(
                llave_privada=llave_privada,
                emisor=entorno.get("FUENTES_JWT_ISSUER", "solventa"),
                audiencia=audiencia,
            ),
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

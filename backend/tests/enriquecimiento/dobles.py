"""Dobles de prueba para el enriquecimiento."""

import asyncio
from datetime import datetime, timedelta, timezone

from app.perfilamiento.dominio.modelos import SenalesOpenData, SenalesOpenFinance
from app.perfilamiento.enriquecimiento.memoria import (
    CacheSenalesEnMemoria,
    RepositorioConsentimientosEnMemoria,
)
from app.perfilamiento.enriquecimiento.modelos import Consentimiento, TipoFuente
from app.perfilamiento.enriquecimiento.puertos import FuenteNoDisponible
from app.perfilamiento.enriquecimiento.servicio import ServicioEnriquecimiento

INICIO = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
FINANZAS = SenalesOpenFinance(comportamiento_pago=0.9, nivel_endeudamiento=0.2)
ENTORNO = SenalesOpenData(estabilidad=0.9, riesgo_zona="BAJO")


class Reloj:
    def __init__(self):
        self.ahora = INICIO

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **delta):
        self.ahora += timedelta(**delta)


class FuenteDoble:
    """Fuente controlable: responde, falla o tarda según se le indique."""

    def __init__(self, tipo: TipoFuente, senales, proveedor: str | None = None):
        self.tipo = tipo
        self.proveedor = proveedor or f"doble-{tipo.value.lower()}"
        self.senales = senales
        self.falla: str | None = None
        self.demora = 0.0
        self.consultas = 0

    async def consultar(self, cliente_id: str):
        self.consultas += 1
        if self.demora:
            await asyncio.sleep(self.demora)
        if self.falla:
            raise FuenteNoDisponible(self.proveedor, self.falla)
        return self.senales


class Escenario:
    def __init__(self, tiempo_limite: float = 0.2):
        self.reloj = Reloj()
        self.open_finance = FuenteDoble(TipoFuente.OPEN_FINANCE, FINANZAS)
        self.open_data = FuenteDoble(TipoFuente.OPEN_DATA, ENTORNO)
        self.cache = CacheSenalesEnMemoria(reloj=self.reloj)
        self.consentimientos = RepositorioConsentimientosEnMemoria()
        self.servicio = ServicioEnriquecimiento(
            fuentes=[self.open_finance, self.open_data],
            cache=self.cache,
            consentimientos=self.consentimientos,
            tiempo_limite=tiempo_limite,
            reloj=self.reloj,
        )

    def con_consentimiento(self, cliente_id: str = "CLI-001", dias: int = 30) -> "Escenario":
        self.consentimientos.registrar(
            Consentimiento(
                consentimiento_id="CONS-001",
                cliente_id=cliente_id,
                vence_en=self.reloj.ahora + timedelta(days=dias),
            )
        )
        return self

    def enriquecer(self, cliente_id: str = "CLI-001"):
        return asyncio.run(self.servicio.enriquecer(cliente_id, "COT-001"))

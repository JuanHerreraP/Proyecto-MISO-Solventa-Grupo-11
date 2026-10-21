"""Caso de uso para crear y consultar cotizaciones (HU03)."""

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from app.cotizaciones.dominio.modelos import Cotizacion, EstadoCotizacion, RamoSeguro
from app.cotizaciones.dominio.rating import calcular_prima_y_cobertura
from app.cotizaciones.repositorio import RepositorioCotizaciones
from app.cotizaciones.servicio_personalizacion import ServicioPersonalizacionCotizacion

VIGENCIA_COTIZACION = timedelta(days=7)


class CotizacionNoEncontrada(Exception):
    """No existe una cotización con el identificador solicitado."""


def generar_cotizacion_id() -> str:
    return f"COT-{uuid.uuid4()}"


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


class ServicioCotizaciones:
    def __init__(
        self,
        repositorio: RepositorioCotizaciones,
        personalizador: ServicioPersonalizacionCotizacion,
        generar_id: Callable[[], str] = generar_cotizacion_id,
        reloj: Callable[[], datetime] = ahora_utc,
    ):
        self._repositorio = repositorio
        self._personalizador = personalizador
        self._generar_id = generar_id
        self._reloj = reloj

    def cotizar(
        self,
        cliente_id: str,
        ramo: RamoSeguro,
        datos_riesgo: dict[str, object],
        asesor_id: str | None = None,
        socio_id: str | None = None,
        tenant_id: str | None = None,
    ) -> Cotizacion:
        tarifa_base = calcular_prima_y_cobertura(ramo, datos_riesgo)
        precio = self._personalizador.personalizar(cliente_id, tarifa_base)
        fecha = self._reloj()

        cotizacion = Cotizacion(
            cotizacion_id=self._generar_id(),
            cliente_id=cliente_id,
            ramo=ramo,
            datos_riesgo=datos_riesgo,
            estado=EstadoCotizacion.VIGENTE,
            prima_total=precio.prima_total,
            cobertura_principal=precio.cobertura_principal,
            perfil_riesgo_id=precio.perfil_riesgo_id,
            asesor_id=asesor_id,
            socio_id=socio_id,
            tenant_id=tenant_id,
            creada_en=fecha,
            vigente_hasta=fecha + VIGENCIA_COTIZACION,
        )
        self._repositorio.guardar(cotizacion)
        return cotizacion

    def consultar(self, cotizacion_id: str) -> Cotizacion:
        cotizacion = self._repositorio.obtener(cotizacion_id)
        if cotizacion is None:
            raise CotizacionNoEncontrada(cotizacion_id)
        return cotizacion

    def listar_por_cliente(self, cliente_id: str) -> list[Cotizacion]:
        return self._repositorio.listar_por_cliente(cliente_id)

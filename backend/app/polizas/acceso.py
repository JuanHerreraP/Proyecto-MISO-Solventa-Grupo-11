"""Quién puede gestionar una póliza: su cliente titular o el asesor de la venta asistida (HU22).

Una póliza ajena se trata como inexistente para el cliente (EC08). El asesor solo accede a las
pólizas de cotizaciones que él originó; las demás se le deniegan.
"""

from app.cotizaciones.repositorio import RepositorioCotizaciones
from app.identidad.modelos import Rol
from app.polizas.dominio.modelos import Poliza
from app.polizas.emision import AccesoDenegado
from app.polizas.endosos import Solicitante
from app.polizas.repositorio import RepositorioPolizas
from app.polizas.servicio import PolizaNoEncontrada


def poliza_del_solicitante(
    polizas: RepositorioPolizas,
    cotizaciones: RepositorioCotizaciones,
    solicitante: Solicitante,
    poliza_id: str,
) -> Poliza:
    if solicitante.rol is Rol.CLIENTE:
        poliza = polizas.obtener_del_cliente(poliza_id, solicitante.actor_id)
        if poliza is None:
            raise PolizaNoEncontrada(poliza_id)
        return poliza
    if solicitante.rol is Rol.ASESOR_VENTAS:
        poliza = polizas.obtener(poliza_id)
        if poliza is None:
            raise PolizaNoEncontrada(poliza_id)
        cotizacion = cotizaciones.obtener(poliza.cotizacion_id) if poliza.cotizacion_id else None
        if cotizacion is None or cotizacion.asesor_id != solicitante.actor_id:
            raise AccesoDenegado(poliza_id)
        return poliza
    raise AccesoDenegado(poliza_id)

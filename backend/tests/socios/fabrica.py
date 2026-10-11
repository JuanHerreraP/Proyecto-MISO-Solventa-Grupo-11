from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.modelos import SolicitudAltaSocio, TipoSeguro


def solicitud_alta(**cambios: object) -> SolicitudAltaSocio:
    datos = {
        "nit": "900123456-7",
        "razon_social": "Banco Andes S.A.",
        "contactos_tecnicos": [
            {
                "nombre": "María Torres",
                "correo": "maria.torres@bancoandes.com",
                "telefono": "+57 300 123 4567",
            }
        ],
        "pais_operacion": "CO",
        "tipos_seguros_autorizados": [TipoSeguro.MICROSEGURO_VIDA],
        "endpoints_autorizados": {CodigoEndpoint.COTIZACIONES_CREAR},
    }
    datos.update(cambios)
    return SolicitudAltaSocio.model_validate(datos)

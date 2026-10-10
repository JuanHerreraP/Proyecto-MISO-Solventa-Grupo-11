from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.socios.dominio.catalogo import CodigoEndpoint
from app.socios.dominio.modelos import ContactoTecnico, EstadoSocio, SocioDistribucion, TipoSeguro


def socio_valido(**cambios: object) -> SocioDistribucion:
    ahora = datetime.now(UTC)
    datos = {
        "socio_id": "SOCIO-001",
        "tenant_id": "TENANT-001",
        "nit": "900123456-7",
        "razon_social": "Banco Andes S.A.",
        "contactos_tecnicos": [
            {
                "nombre": "María Torres",
                "correo": "maria.torres@andes.com",
                "telefono": "+57 300 123 4567",
            }
        ],
        "pais_operacion": "CO",
        "tipos_seguros_autorizados": [
            TipoSeguro.VIAJE,
            TipoSeguro.PROTECCION_DISPOSITIVOS,
        ],
        "endpoints_autorizados": {
            CodigoEndpoint.COTIZACIONES_CREAR,
            CodigoEndpoint.POLIZAS_EMITIR,
        },
        "creado_en": ahora,
        "actualizado_en": ahora,
    }
    datos.update(cambios)
    return SocioDistribucion.model_validate(datos)


def test_crea_socio_pendiente_con_datos_validos() -> None:
    socio = socio_valido()

    assert socio.estado is EstadoSocio.PENDIENTE
    assert socio.pais_operacion == "CO"
    assert socio.contactos_tecnicos[0].correo == "maria.torres@andes.com"


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("nit", "900.123.456-7"),
        ("pais_operacion", "Colombia"),
        ("contactos_tecnicos", []),
        ("tipos_seguros_autorizados", []),
        ("endpoints_autorizados", []),
    ],
)
def test_rechaza_datos_obligatorios_invalidos(campo: str, valor: object) -> None:
    with pytest.raises(ValidationError):
        socio_valido(**{campo: valor})


def test_rechaza_correos_repetidos_en_contactos() -> None:
    contacto = ContactoTecnico(nombre="María Torres", correo="maria@andes.com")

    with pytest.raises(ValidationError, match="no pueden repetir el correo"):
        socio_valido(contactos_tecnicos=[contacto, contacto])


def test_rechaza_tipos_de_seguro_repetidos() -> None:
    with pytest.raises(ValidationError, match="no pueden repetirse"):
        socio_valido(tipos_seguros_autorizados=[TipoSeguro.VIAJE, TipoSeguro.VIAJE])


def test_asocia_al_socio_con_productos_y_endpoints_autorizados() -> None:
    socio = socio_valido(
        tipos_seguros_autorizados=[TipoSeguro.MICROSEGURO_VIDA],
        endpoints_autorizados={CodigoEndpoint.COTIZACIONES_CREAR},
    )

    assert socio.tipos_seguros_autorizados == [TipoSeguro.MICROSEGURO_VIDA]
    assert socio.endpoints_autorizados == {CodigoEndpoint.COTIZACIONES_CREAR}

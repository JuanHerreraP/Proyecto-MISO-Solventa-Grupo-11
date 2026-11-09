"""Casos de uso del endoso sobre repositorios en memoria (HU16)."""

import hashlib
from decimal import Decimal

import pytest

from app.identidad.modelos import Rol
from app.polizas.dominio.endosos import SolicitudModificacion, TipoEndoso
from app.polizas.emision import AccesoDenegado, DocumentoAlterado
from app.polizas.endosos import ClaveIdempotenciaReutilizada, EndosoNoEncontrado, Solicitante
from app.polizas.repositorio_endosos import EndosoConcurrente
from app.polizas.servicio import PolizaNoEncontrada
from tests.endosos.fabrica import CLIENTE, POLIZA, crear_entorno, dos_beneficiarios, solo_coberturas

TITULAR = Solicitante(CLIENTE, Rol.CLIENTE, ip="10.0.0.7", user_agent="pruebas")
OTRO_CLIENTE = Solicitante("CLI-999", Rol.CLIENTE)
ASESOR = Solicitante("ASE-1", Rol.ASESOR_VENTAS)


def test_simular_no_guarda_nada() -> None:
    e = crear_entorno()

    propuesta = e.servicio.simular(
        TITULAR, POLIZA, solo_coberturas(INCAPACIDAD_TOTAL_PERMANENTE="50000000")
    )

    assert propuesta.ajuste_prima == Decimal("36600.00")
    assert e.endosos.listar_por_poliza(POLIZA) == []
    assert e.polizas.obtener(POLIZA).coberturas_opcionales == []


def test_confirmar_aplica_el_cambio_a_la_poliza_y_emite_el_endoso() -> None:
    e = crear_entorno()

    endoso, creado = e.servicio.confirmar(
        TITULAR, POLIZA, solo_coberturas(INCAPACIDAD_TOTAL_PERMANENTE="50000000")
    )

    assert creado is True
    assert endoso.endoso_id == "END-VIDA-1-001"
    assert endoso.numero_endoso == 1
    assert endoso.tipo is TipoEndoso.COBERTURAS
    assert endoso.ajuste_prima == Decimal("36600.00")
    poliza = e.polizas.obtener(POLIZA)
    assert poliza.prima_total == Decimal("186600.00")
    assert [c.codigo for c in poliza.coberturas_opcionales] == ["INCAPACIDAD_TOTAL_PERMANENTE"]
    contenido = e.almacen.leer(endoso.clave_documento)
    assert contenido.startswith(b"%PDF")
    assert endoso.huella_documento == hashlib.sha256(contenido).hexdigest()


def test_el_endoso_queda_atribuido_a_su_autor() -> None:
    e = crear_entorno()

    endoso, _ = e.servicio.confirmar(
        TITULAR, POLIZA, SolicitudModificacion(beneficiarios=dos_beneficiarios())
    )

    assert endoso.solicitado_por == CLIENTE
    assert endoso.rol_solicitante == "CLIENTE"
    assert endoso.ip_solicitante == "10.0.0.7"
    assert endoso.user_agent == "pruebas"
    assert len(endoso.huella_solicitud) == 64


def test_los_endosos_se_numeran_en_orden() -> None:
    e = crear_entorno()
    e.servicio.confirmar(TITULAR, POLIZA, SolicitudModificacion(beneficiarios=dos_beneficiarios()))

    segundo, _ = e.servicio.confirmar(TITULAR, POLIZA, solo_coberturas(AUXILIO_FUNERARIO="5000000"))

    assert segundo.numero_endoso == 2
    assert [x.numero_endoso for x in e.servicio.listar(TITULAR, POLIZA)] == [1, 2]
    # El segundo endoso parte de la póliza ya modificada por el primero.
    assert len(segundo.beneficiarios) == 2


def test_repetir_con_la_misma_clave_devuelve_el_mismo_endoso() -> None:
    e = crear_entorno()
    solicitud = solo_coberturas(AUXILIO_FUNERARIO="5000000")
    primero, _ = e.servicio.confirmar(TITULAR, POLIZA, solicitud, "clave-1")

    repetido, creado = e.servicio.confirmar(TITULAR, POLIZA, solicitud, "clave-1")

    assert creado is False
    assert repetido.endoso_id == primero.endoso_id
    assert len(e.endosos.listar_por_poliza(POLIZA)) == 1
    assert e.polizas.obtener(POLIZA).prima_total == primero.prima_nueva


def test_reutilizar_la_clave_con_otros_cambios_se_rechaza() -> None:
    e = crear_entorno()
    e.servicio.confirmar(TITULAR, POLIZA, solo_coberturas(AUXILIO_FUNERARIO="5000000"), "clave-1")

    with pytest.raises(ClaveIdempotenciaReutilizada):
        e.servicio.confirmar(
            TITULAR, POLIZA, solo_coberturas(AUXILIO_FUNERARIO="6000000"), "clave-1"
        )


def test_dos_confirmaciones_simultaneas_no_duplican_el_numero() -> None:
    e = crear_entorno()
    # Simula que otra petición registró el endoso 1 entre la lectura y el registro.
    listar_original = e.endosos.listar_por_poliza
    e.endosos.listar_por_poliza = lambda poliza_id: []
    e.servicio.confirmar(TITULAR, POLIZA, SolicitudModificacion(beneficiarios=dos_beneficiarios()))

    with pytest.raises(EndosoConcurrente):
        e.servicio.confirmar(TITULAR, POLIZA, solo_coberturas(AUXILIO_FUNERARIO="5000000"))

    e.endosos.listar_por_poliza = listar_original
    assert len(e.endosos.listar_por_poliza(POLIZA)) == 1


def test_un_cliente_no_modifica_ni_consulta_la_poliza_de_otro() -> None:
    e = crear_entorno()
    solicitud = solo_coberturas(AUXILIO_FUNERARIO="5000000")

    with pytest.raises(PolizaNoEncontrada):
        e.servicio.simular(OTRO_CLIENTE, POLIZA, solicitud)
    with pytest.raises(PolizaNoEncontrada):
        e.servicio.confirmar(OTRO_CLIENTE, POLIZA, solicitud)
    with pytest.raises(PolizaNoEncontrada):
        e.servicio.listar(OTRO_CLIENTE, POLIZA)


def test_el_asesor_modifica_solo_si_participo_en_la_venta() -> None:
    sin_asesor = crear_entorno()
    with pytest.raises(AccesoDenegado):
        sin_asesor.servicio.simular(ASESOR, POLIZA, solo_coberturas(AUXILIO_FUNERARIO="5000000"))

    asistida = crear_entorno(asesor_id="ASE-1")
    endoso, _ = asistida.servicio.confirmar(
        ASESOR, POLIZA, solo_coberturas(AUXILIO_FUNERARIO="5000000")
    )
    assert endoso.rol_solicitante == "ASESOR_VENTAS"
    assert endoso.solicitado_por == "ASE-1"


def test_otros_roles_no_modifican_polizas() -> None:
    e = crear_entorno()

    with pytest.raises(AccesoDenegado):
        e.servicio.poliza(Solicitante("ANA-1", Rol.ANALISTA_RIESGOS), POLIZA)


def test_descargar_el_documento_verifica_su_huella() -> None:
    e = crear_entorno()
    endoso, _ = e.servicio.confirmar(TITULAR, POLIZA, solo_coberturas(AUXILIO_FUNERARIO="5000000"))

    documento = e.servicio.documento(TITULAR, POLIZA, endoso.endoso_id)

    assert documento.nombre_archivo == "endoso-SOL-2026-VIDA0001-001.pdf"
    assert documento.contenido.startswith(b"%PDF")

    e.almacen._por_clave[endoso.clave_documento] = b"%PDF alterado"
    with pytest.raises(DocumentoAlterado):
        e.servicio.documento(TITULAR, POLIZA, endoso.endoso_id)


def test_un_endoso_inexistente_no_se_descarga() -> None:
    e = crear_entorno()

    with pytest.raises(EndosoNoEncontrado):
        e.servicio.documento(TITULAR, POLIZA, "END-NADA")

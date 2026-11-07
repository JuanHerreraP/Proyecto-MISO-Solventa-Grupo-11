import hashlib
from datetime import date

import pytest

from app.polizas.almacenamiento import AlmacenEnDisco, AlmacenNoDisponible, DocumentoInmutable
from app.polizas.comunicaciones import ComunicacionNoDisponible
from app.polizas.dominio.modelos import RamoPoliza
from app.polizas.emision import (
    AccesoDenegado,
    DocumentoAlterado,
    DocumentoNoDisponible,
    EmisionNoDisponible,
    _sumar_meses,
    _vigencia,
    poliza_id_de,
)
from app.polizas.servicio import PolizaNoEncontrada
from tests.emision.fabrica import crear_entorno
from tests.firmas.fabrica import AHORA, CLIENTE, COTIZACION

POLIZA = poliza_id_de(COTIZACION)


def test_la_firma_emite_la_poliza_con_lo_contratado_y_lo_cobrado() -> None:
    e = crear_entorno()

    e.firmar()

    poliza = e.polizas.obtener(POLIZA)
    assert poliza is not None
    assert poliza.cliente_id == CLIENTE
    assert poliza.cotizacion_id == COTIZACION
    assert poliza.ramo is RamoPoliza.VIDA
    assert poliza.titular_nombre == "Laura Gómez"
    assert str(poliza.prima_total) == "94500.00"
    assert poliza.cobertura_principal.codigo == "VIDA_DEUDORES"
    assert any(
        "suicidio" in exclusion for exclusion in poliza.cobertura_principal.exclusiones_principales
    )
    assert poliza.numero_poliza.startswith("SOL-2027-")
    assert poliza.codigo_verificacion == "abcdef0123456789"
    # plazo_meses=240 contados desde la firma (1 de enero de 2027, hora de Colombia)
    assert (poliza.fecha_inicio, poliza.fecha_fin) == (date(2027, 1, 1), date(2046, 12, 31))


def test_guarda_el_pdf_una_sola_vez_con_su_huella() -> None:
    e = crear_entorno()

    e.firmar()

    documento = e.documentos.obtener(POLIZA)
    contenido = e.almacen.leer(documento.clave_almacenamiento)
    assert contenido.startswith(b"%PDF")
    assert documento.huella_sha256 == hashlib.sha256(contenido).hexdigest()
    assert documento.tamano_bytes == len(contenido)
    assert e.firmas_servicio.poliza_emitida(COTIZACION) == POLIZA


def test_el_pdf_compila_asegurado_cobertura_tarifa_y_sellos() -> None:
    e = crear_entorno()
    proceso = e.firmar()
    contenido = e.almacen.leer(e.documentos.obtener(POLIZA).clave_almacenamiento)

    for esperado in (
        e.polizas.obtener(POLIZA).numero_poliza,
        "1020304050",
        "Seguro de vida hipotecario",
        "Vida deudores hipotecario",
        "COP 94.500,00",
        "COP 250.000.000,00",
        "EXCLUSIONES PRINCIPALES",
        "suicidio ocurrido durante el primer a",
        proceso.referencia_proveedor,
        proceso.sello_proveedor,
        proceso.huella_documento,
        "abcdef0123456789",
    ):
        assert esperado.encode("latin-1") in contenido, esperado


def test_la_emision_es_idempotente() -> None:
    e = crear_entorno()
    e.firmar()
    primera = e.polizas.obtener(POLIZA)
    huella = e.documentos.obtener(POLIZA).huella_sha256
    huella_contrato = e.firmas.obtener_por_cotizacion(COTIZACION).huella_documento

    segunda = e.emision.emitir(COTIZACION)
    # Reintento de la firma tras una respuesta perdida.
    reintento = e.firmas_servicio.firmar(
        CLIENTE, COTIZACION, "000000", huella_contrato, ip=None, user_agent=None
    )

    assert reintento.estado.value == "FIRMADA"
    assert segunda == primera
    assert e.polizas.obtener(POLIZA) == primera
    assert e.documentos.obtener(POLIZA).huella_sha256 == huella
    assert len(e.polizas.listar_por_cliente(CLIENTE)) == 1


def test_no_se_emite_sin_firma_completada() -> None:
    e = crear_entorno()
    e.firmas_servicio.presentar(CLIENTE, COTIZACION)

    with pytest.raises(EmisionNoDisponible):
        e.emision.emitir(COTIZACION)
    assert e.polizas.obtener(POLIZA) is None
    assert e.firmas_servicio.poliza_emitida(COTIZACION) is None


class EmisorQueFalla:
    def __init__(self, real):
        self.real = real
        self.falla = True

    def emitir(self, cotizacion_id):
        if self.falla:
            raise RuntimeError("almacén caído")
        return self.real.emitir(cotizacion_id)

    def poliza_emitida(self, cotizacion_id):
        return self.real.poliza_emitida(cotizacion_id)


def test_si_la_emision_falla_la_firma_se_conserva_y_el_reintento_la_completa() -> None:
    e = crear_entorno()
    emisor = EmisorQueFalla(e.emision)
    e.firmas_servicio._emisor = emisor

    firmado = e.firmar()

    assert firmado.estado.value == "FIRMADA"
    assert e.firmas_servicio.poliza_emitida(COTIZACION) is None
    emisor.falla = False
    # Consultar el contrato ya firmado completa la emisión pendiente.
    e.firmas_servicio.presentar(CLIENTE, COTIZACION)
    assert e.firmas_servicio.poliza_emitida(COTIZACION) == POLIZA


def test_descarga_del_cliente_propio_y_no_de_uno_ajeno() -> None:
    e = crear_entorno()
    e.firmar()

    documento = e.emision.documento_del_cliente(CLIENTE, POLIZA)

    assert documento.contenido.startswith(b"%PDF")
    assert documento.nombre_archivo.startswith("poliza-SOL-2027-")
    with pytest.raises(PolizaNoEncontrada):
        e.emision.documento_del_cliente("CLI-999", POLIZA)


def test_el_asesor_solo_descarga_polizas_de_sus_ventas_asistidas() -> None:
    e = crear_entorno()
    asistida = e.cotizaciones.obtener(COTIZACION).model_copy(update={"asesor_id": "ASE-1"})
    e.cotizaciones.guardar(asistida)
    e.firmar()

    assert e.emision.documento_del_asesor("ASE-1", POLIZA).contenido.startswith(b"%PDF")
    with pytest.raises(AccesoDenegado):
        e.emision.documento_del_asesor("ASE-2", POLIZA)
    with pytest.raises(PolizaNoEncontrada):
        e.emision.documento_del_asesor("ASE-1", "POL-NO-EXISTE")


def test_una_venta_sin_asesor_no_es_visible_para_ningun_asesor() -> None:
    e = crear_entorno()
    e.firmar()

    with pytest.raises(AccesoDenegado):
        e.emision.documento_del_asesor("ASE-1", POLIZA)


def test_detecta_un_documento_alterado_o_ausente() -> None:
    e = crear_entorno()
    e.firmar()
    clave = e.documentos.obtener(POLIZA).clave_almacenamiento

    e.almacen._por_clave[clave] = b"%PDF-falso"
    with pytest.raises(DocumentoAlterado):
        e.emision.documento_del_cliente(CLIENTE, POLIZA)

    del e.almacen._por_clave[clave]
    with pytest.raises(DocumentoNoDisponible):
        e.emision.documento_del_cliente(CLIENTE, POLIZA)


def test_envia_correo_con_el_pdf_y_la_notificacion_una_sola_vez() -> None:
    e = crear_entorno()
    e.firmar()
    assert e.comunicaciones.correos == []  # nada se envía dentro de la petición

    e.emision.notificar(POLIZA)
    e.emision.notificar(POLIZA)

    assert len(e.comunicaciones.correos) == 1
    correo = e.comunicaciones.correos[0]
    assert correo.destinatario == "laura@example.com"
    assert correo.adjunto_pdf == e.emision.documento_del_cliente(CLIENTE, POLIZA).contenido
    assert len(e.comunicaciones.notificaciones) == 1
    assert e.comunicaciones.notificaciones[0].cliente_id == CLIENTE
    assert e.documentos.obtener(POLIZA).bienvenida_enviada_en is not None


def test_si_el_correo_falla_la_poliza_sigue_emitida_y_se_reintenta() -> None:
    e = crear_entorno()
    e.firmar()
    intentos = []

    class CorreoInestable:
        def enviar_bienvenida(self, correo):
            intentos.append(correo)
            if len(intentos) == 1:
                raise ComunicacionNoDisponible("canal caído")
            e.comunicaciones.enviar_bienvenida(correo)

    e.emision._correo = CorreoInestable()

    e.emision.notificar(POLIZA)
    assert e.documentos.obtener(POLIZA).bienvenida_enviada_en is None
    assert len(e.comunicaciones.notificaciones) == 1  # la confirmación no depende del correo

    e.emision.notificar(POLIZA)
    assert len(intentos) == 2
    assert e.documentos.obtener(POLIZA).bienvenida_enviada_en is not None
    assert len(e.comunicaciones.notificaciones) == 1


def test_notificar_una_poliza_inexistente_no_falla() -> None:
    crear_entorno().emision.notificar("POL-NO-EXISTE")


def test_vigencia_de_viaje_usa_las_fechas_declaradas() -> None:
    datos = {"fecha_inicio": "2027-03-01", "fecha_fin": "2027-03-10"}
    assert _vigencia(RamoPoliza.VIAJE, datos, AHORA) == (date(2027, 3, 1), date(2027, 3, 10))


def test_vigencia_por_meses_y_valor_por_defecto() -> None:
    assert _vigencia(RamoPoliza.VIDA, {"meses_cobertura": 12}, AHORA) == (
        date(2027, 1, 1),
        date(2027, 12, 31),
    )
    assert _vigencia(RamoPoliza.VIDA, {}, AHORA) == (date(2027, 1, 1), date(2028, 1, 1))
    # Fechas inválidas o invertidas caen al valor por defecto.
    invertidas = {"fecha_inicio": "2027-03-10", "fecha_fin": "2027-03-01"}
    assert _vigencia(RamoPoliza.VIAJE, invertidas, AHORA)[0] == date(2027, 1, 1)
    ilegibles = {"fecha_inicio": "x", "fecha_fin": "y"}
    assert _vigencia(RamoPoliza.VIAJE, ilegibles, AHORA)[0] == date(2027, 1, 1)


def test_sumar_meses_respeta_el_fin_de_mes() -> None:
    assert _sumar_meses(date(2027, 1, 31), 1) == date(2027, 2, 28)
    assert _sumar_meses(date(2027, 11, 15), 3) == date(2028, 2, 15)


def test_almacen_en_disco_no_sobrescribe_y_aisla_las_rutas(tmp_path) -> None:
    almacen = AlmacenEnDisco(tmp_path)

    almacen.guardar("polizas/POL-1.pdf", b"%PDF-uno")
    almacen.guardar("polizas/POL-1.pdf", b"%PDF-uno")  # mismo contenido: inocuo

    assert almacen.leer("polizas/POL-1.pdf") == b"%PDF-uno"
    assert almacen.leer("polizas/POL-2.pdf") is None
    with pytest.raises(DocumentoInmutable):
        almacen.guardar("polizas/POL-1.pdf", b"%PDF-otro")
    with pytest.raises(AlmacenNoDisponible):
        almacen.guardar("../fuera.pdf", b"x")
    with pytest.raises(AlmacenNoDisponible):
        almacen.leer("../../fuera.pdf")

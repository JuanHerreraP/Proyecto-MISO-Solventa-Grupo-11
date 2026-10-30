import pytest

from app.cotizaciones.dominio.modelos import RamoSeguro
from app.firmas.modelos import CanalOtp, EstadoFirma
from app.firmas.puertos import ProveedorFirmaNoDisponible
from app.firmas.servicio import (
    DocumentoAlterado,
    FirmaBloqueada,
    FirmaNoDisponible,
    FirmaNoEncontrada,
    OtpRechazado,
    ReenvioNoPermitido,
)
from app.pagos.modelos import EstadoPago
from tests.firmas.fabrica import AHORA, CLIENTE, COTIZACION, cotizacion, crear_entorno, pago


@pytest.fixture
def e():
    return crear_entorno()


def firmar(e, codigo=None, huella=None, cliente=CLIENTE):
    proceso = e.firmas.obtener_por_cotizacion(COTIZACION)
    return e.servicio.firmar(
        cliente,
        COTIZACION,
        codigo if codigo is not None else e.ultimo_codigo,
        huella or proceso.huella_documento,
        ip="190.24.1.10",
        user_agent="Mozilla/5.0 pruebas",
    )


# --- Contrato prellenado ---------------------------------------------------------------


def test_presenta_el_contrato_prellenado_tras_el_pago_aprobado(e):
    proceso = e.servicio.presentar(CLIENTE, COTIZACION)

    contrato = proceso.contrato
    assert proceso.estado is EstadoFirma.PENDIENTE
    assert contrato.nombre_ramo == "Seguro de vida hipotecario"
    assert contrato.titular.nombre_completo == "Laura Gómez"
    assert contrato.titular.numero_documento == "1020304050"
    assert str(contrato.prima_total) == "94500.00"
    assert contrato.pago_id == "PAG-COT-001"
    assert contrato.referencia_pago == "PSP-COT-001"
    assert contrato.datos_riesgo["valor_credito"] == 250000000
    assert any("hipotecario" in clausula for clausula in contrato.clausulas)
    assert proceso.huella_documento == contrato.huella()
    assert len(proceso.huella_documento) == 64


def test_microseguro_de_vida_usa_el_nombre_del_catalogo_y_sin_clausula_del_banco(e):
    e.cotizaciones.guardar(
        cotizacion().model_copy(
            update={"datos_riesgo": {"fecha_nacimiento": "1990-05-14", "meses_cobertura": 12}}
        )
    )

    contrato = e.servicio.presentar(CLIENTE, COTIZACION).contrato

    assert contrato.nombre_ramo == "Microseguro de vida"
    assert not any("entidad financiera" in clausula for clausula in contrato.clausulas)
    assert any("beneficiarios designados" in clausula for clausula in contrato.clausulas)


def test_otros_ramos_usan_el_nombre_del_catalogo(e):
    e.cotizaciones.guardar(
        cotizacion().model_copy(update={"ramo": RamoSeguro.VIAJE, "datos_riesgo": {}})
    )

    contrato = e.servicio.presentar(CLIENTE, COTIZACION).contrato

    assert contrato.nombre_ramo == "Seguro de viaje"
    assert any("fechas del viaje" in clausula for clausula in contrato.clausulas)


def test_presentar_dos_veces_devuelve_el_mismo_documento(e):
    primero = e.servicio.presentar(CLIENTE, COTIZACION)
    e.titulares.por_cliente[CLIENTE] = e.titulares.por_cliente[CLIENTE].model_copy(
        update={"nombre_completo": "Otro Nombre"}
    )

    segundo = e.servicio.presentar(CLIENTE, COTIZACION)

    assert segundo.huella_documento == primero.huella_documento
    assert segundo.contrato.titular.nombre_completo == "Laura Gómez"


def test_no_presenta_contrato_sin_pago_aprobado(e):
    e.pagos.guardar(pago(estado=EstadoPago.PENDIENTE))

    with pytest.raises(FirmaNoDisponible) as error:
        e.servicio.presentar(CLIENTE, COTIZACION)

    assert error.value.codigo == "PAGO_NO_APROBADO"


def test_no_presenta_contrato_de_otro_cliente(e):
    with pytest.raises(FirmaNoDisponible) as error:
        e.servicio.presentar("CLI-999", COTIZACION)
    assert error.value.codigo == "COTIZACION_NO_ENCONTRADA"

    e.servicio.presentar(CLIENTE, COTIZACION)
    with pytest.raises(FirmaNoDisponible):
        e.servicio.presentar("CLI-999", COTIZACION)


def test_no_presenta_contrato_si_falta_el_titular(e):
    e.titulares.por_cliente.clear()

    with pytest.raises(FirmaNoDisponible) as error:
        e.servicio.presentar(CLIENTE, COTIZACION)

    assert error.value.codigo == "TITULAR_SIN_DATOS"


def test_la_huella_cambia_si_cambia_una_condicion(e):
    proceso = e.servicio.presentar(CLIENTE, COTIZACION)
    alterado = proceso.contrato.model_copy(update={"prima_total": proceso.contrato.prima_total + 1})

    assert alterado.huella() != proceso.huella_documento


# --- OTP -------------------------------------------------------------------------------


def test_envia_el_otp_por_sms_sin_guardar_el_codigo(e):
    proceso = e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)

    assert e.proveedor.envios == 1
    assert proceso.otp_destino == "*** *** 4567"
    assert proceso.otp_expira_en == AHORA.replace(minute=5)
    assert proceso.envios == 1
    assert proceso.intentos_restantes == 3
    assert e.ultimo_codigo not in proceso.model_dump_json()


def test_envia_el_otp_por_correo(e):
    proceso = e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.EMAIL)

    assert proceso.otp_destino == "la***@example.com"
    assert proceso.otp_canal is CanalOtp.EMAIL


def test_rechaza_sms_si_no_hay_celular(e):
    e.titulares.por_cliente[CLIENTE] = e.titulares.por_cliente[CLIENTE].model_copy(
        update={"celular": None}
    )

    with pytest.raises(FirmaNoDisponible) as error:
        e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)

    assert error.value.codigo == "DESTINO_NO_DISPONIBLE"


def test_reenvio_exige_esperar_treinta_segundos(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    e.reloj.avanzar(seconds=10)

    with pytest.raises(ReenvioNoPermitido) as error:
        e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    assert error.value.codigo == "ESPERA_REENVIO"

    e.reloj.avanzar(seconds=20)
    proceso = e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    assert proceso.envios == 2


def test_reenvio_invalida_el_codigo_anterior(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    anterior = e.ultimo_codigo
    e.reloj.avanzar(seconds=30)
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)

    with pytest.raises(OtpRechazado) as error:
        firmar(e, codigo=anterior)
    assert error.value.codigo == "OTP_INCORRECTO"
    assert firmar(e).estado is EstadoFirma.FIRMADA


def test_limita_el_numero_de_envios(e):
    for _ in range(3):
        e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
        e.reloj.avanzar(seconds=31)

    with pytest.raises(ReenvioNoPermitido) as error:
        e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)

    assert error.value.codigo == "ENVIOS_AGOTADOS"


def test_proveedor_caido_no_consume_envios(e):
    e.proveedor.disponible = False

    with pytest.raises(ProveedorFirmaNoDisponible):
        e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)

    assert e.firmas.obtener_por_cotizacion(COTIZACION).envios == 0


# --- Firma -----------------------------------------------------------------------------


def test_firma_exitosa_registra_los_metadatos(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    e.reloj.avanzar(minutes=2)

    proceso = firmar(e)

    assert proceso.estado is EstadoFirma.FIRMADA
    assert proceso.firmado_en == AHORA.replace(minute=2)
    assert proceso.firmante_id == CLIENTE
    assert proceso.ip_firmante == "190.24.1.10"
    assert proceso.user_agent == "Mozilla/5.0 pruebas"
    assert proceso.referencia_proveedor.startswith("SIM-")
    assert len(proceso.sello_proveedor) == 64
    assert proceso.otp_hash is None
    assert proceso.documento_integro()
    assert e.firmas.obtener_por_cotizacion(COTIZACION) == proceso


def test_firma_repetida_devuelve_la_existente_sin_volver_a_sellar(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    primera = firmar(e)
    e.reloj.avanzar(minutes=1)

    segunda = firmar(e, codigo="000000")

    assert segunda == primera
    assert e.proveedor.sellos == 1


def test_otp_incorrecto_descuenta_intentos(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)

    with pytest.raises(OtpRechazado) as error:
        firmar(e, codigo="000000")

    assert error.value.codigo == "OTP_INCORRECTO"
    assert error.value.proceso.intentos_restantes == 2
    assert e.firmas.obtener_por_cotizacion(COTIZACION).estado is EstadoFirma.PENDIENTE


def test_tres_fallos_agotan_el_codigo(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    for _ in range(3):
        with pytest.raises(OtpRechazado):
            firmar(e, codigo="000000")

    with pytest.raises(OtpRechazado) as error:
        firmar(e)

    assert error.value.codigo == "OTP_INTENTOS_AGOTADOS"


def test_se_bloquea_al_agotar_intentos_y_envios(e):
    for envio in range(3):
        e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
        e.reloj.avanzar(seconds=31)
        for intento in range(3):
            ultimo = envio == 2 and intento == 2
            with pytest.raises(FirmaBloqueada if ultimo else OtpRechazado):
                firmar(e, codigo="000000")

    assert e.firmas.obtener_por_cotizacion(COTIZACION).estado is EstadoFirma.BLOQUEADA
    with pytest.raises(FirmaBloqueada):
        firmar(e)
    with pytest.raises(FirmaBloqueada):
        e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)


def test_otp_vencido(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    e.reloj.avanzar(minutes=5)

    with pytest.raises(OtpRechazado) as error:
        firmar(e)

    assert error.value.codigo == "OTP_VENCIDO"


def test_no_firma_sin_otp_emitido(e):
    e.servicio.presentar(CLIENTE, COTIZACION)

    with pytest.raises(OtpRechazado) as error:
        firmar(e, codigo="123456")

    assert error.value.codigo == "OTP_NO_EMITIDO"


def test_no_firma_si_la_huella_aceptada_no_coincide(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)

    with pytest.raises(DocumentoAlterado):
        firmar(e, huella="f" * 64)

    assert e.proveedor.sellos == 0


def test_no_firma_si_el_contrato_guardado_fue_alterado(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    proceso = e.firmas.obtener_por_cotizacion(COTIZACION)
    alterado = proceso.contrato.model_copy(update={"prima_total": proceso.contrato.prima_total / 2})
    e.firmas.guardar(proceso.model_copy(update={"contrato": alterado}))

    with pytest.raises(DocumentoAlterado):
        firmar(e)


def test_no_firma_si_el_pago_dejo_de_estar_aprobado(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    e.pagos.guardar(pago(estado=EstadoPago.RECHAZADO))

    with pytest.raises(FirmaNoDisponible) as error:
        firmar(e)

    assert error.value.codigo == "PAGO_NO_APROBADO"


def test_no_firma_el_contrato_de_otro_cliente(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)

    with pytest.raises(FirmaNoEncontrada):
        firmar(e, cliente="CLI-999")


def test_proveedor_caido_al_sellar_permite_reintentar_con_el_mismo_codigo(e):
    e.servicio.solicitar_otp(CLIENTE, COTIZACION, CanalOtp.SMS)
    e.proveedor.disponible = False

    with pytest.raises(ProveedorFirmaNoDisponible):
        firmar(e)
    assert e.firmas.obtener_por_cotizacion(COTIZACION).estado is EstadoFirma.PENDIENTE

    e.proveedor.disponible = True
    assert firmar(e).estado is EstadoFirma.FIRMADA

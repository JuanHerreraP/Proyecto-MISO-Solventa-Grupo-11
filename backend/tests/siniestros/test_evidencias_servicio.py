"""Reglas de las evidencias del siniestro (HU04) y su integridad y auditoría (EC10)."""

from datetime import timedelta

import pytest

from app.polizas.almacenamiento import AlmacenNoDisponible
from app.siniestros.evidencias import (
    LIMITE_FOTO_BYTES,
    LIMITE_VIDEO_BYTES,
    MAXIMO_EVIDENCIAS,
    AccesoDenegado,
    ArchivoDemasiadoGrande,
    ArchivoVacio,
    ContenidoNoCoincide,
    DatosCaptura,
    EvidenciaAlterada,
    EvidenciaNoEncontrada,
    FechaCapturaInvalida,
    HuellaNoCoincide,
    LimiteEvidencias,
    SiniestroCerrado,
    SiniestroNoEncontrado,
    TipoEvidencia,
    TipoNoPermitido,
    contenido_corresponde,
    nombre_seguro,
    normalizar_tipo,
)
from app.siniestros.modelos import EstadoSiniestro
from tests.siniestros.fabrica_evidencias import (
    AHORA,
    ASESOR,
    AUDITOR,
    CLIENTE,
    GP3,
    JPEG,
    MP4,
    OPERADOR,
    OTRO_CLIENTE,
    PNG,
    Entorno,
    sha,
    siniestro,
)

CON_UBICACION = DatosCaptura(
    capturada_en=AHORA - timedelta(minutes=10),
    latitud=4.7016,
    longitud=-74.1469,
    precision_metros=12.5,
    nombre_archivo="IMG_0001.jpg",
)
SIN_UBICACION = DatosCaptura(capturada_en=AHORA - timedelta(minutes=10))


@pytest.fixture
def entorno() -> Entorno:
    return Entorno()


def adjuntar(entorno: Entorno, contenido=JPEG, tipo="image/jpeg", datos=CON_UBICACION, **extra):
    return entorno.servicio.adjuntar(
        actor=extra.pop("actor", CLIENTE),
        siniestro_id=extra.pop("siniestro_id", "SIN-1"),
        contenido=contenido,
        tipo_contenido=tipo,
        datos=datos,
        **extra,
    )


# --- Carga -------------------------------------------------------------------------------


def test_adjunta_foto_con_ubicacion_huella_y_fecha(entorno) -> None:
    resultado = adjuntar(entorno, huella_declarada=sha(JPEG))

    evidencia = resultado.evidencia
    assert resultado.creada
    assert evidencia.tipo is TipoEvidencia.FOTO
    assert evidencia.huella_sha256 == sha(JPEG)
    assert evidencia.tamano_bytes == len(JPEG)
    assert evidencia.geoetiquetada
    assert (evidencia.latitud, evidencia.longitud) == (4.7016, -74.1469)
    assert evidencia.capturada_en == AHORA - timedelta(minutes=10)
    assert evidencia.subida_por == "CLI-001"
    assert evidencia.nombre_archivo == "IMG_0001.jpg"
    # El archivo queda bajo una clave derivada de su huella.
    assert evidencia.clave_almacenamiento == f"evidencias-siniestros/SIN-1/{sha(JPEG)}.jpg"
    assert entorno.almacen.leer(evidencia.clave_almacenamiento) == JPEG


def test_sin_permiso_de_ubicacion_se_acepta_sin_geoetiqueta(entorno) -> None:
    evidencia = adjuntar(entorno, datos=SIN_UBICACION).evidencia

    assert not evidencia.geoetiquetada
    assert evidencia.latitud is None and evidencia.longitud is None
    assert "sin ubicación" in entorno.auditoria.registros[-1].detalle


@pytest.mark.parametrize(
    ("contenido", "tipo", "esperado"),
    [
        (PNG, "image/png", TipoEvidencia.FOTO),
        (MP4, "video/mp4", TipoEvidencia.VIDEO),
        (GP3, "video/3gpp", TipoEvidencia.VIDEO),
        (JPEG, "IMAGE/JPEG; charset=binary", TipoEvidencia.FOTO),
    ],
)
def test_acepta_los_formatos_permitidos(entorno, contenido, tipo, esperado) -> None:
    evidencia = adjuntar(entorno, contenido=contenido, tipo=tipo).evidencia
    assert evidencia.tipo is esperado
    assert evidencia.tipo_contenido == normalizar_tipo(tipo)


def test_reenviar_el_mismo_archivo_no_duplica(entorno) -> None:
    primera = adjuntar(entorno)
    segunda = adjuntar(entorno)

    assert primera.creada and not segunda.creada
    assert segunda.evidencia.evidencia_id == primera.evidencia.evidencia_id
    assert entorno.evidencias.contar("SIN-1") == 1
    assert entorno.acciones() == ["CARGA"]


def test_el_mismo_archivo_en_otro_siniestro_es_otra_evidencia(entorno) -> None:
    entorno.siniestros.guardar(siniestro(siniestro_id="SIN-2"))
    adjuntar(entorno)
    otra = adjuntar(entorno, siniestro_id="SIN-2")

    assert otra.creada
    assert otra.evidencia.clave_almacenamiento.startswith("evidencias-siniestros/SIN-2/")


@pytest.mark.parametrize("tipo", ["application/pdf", "image/gif", "image/heic", None, ""])
def test_rechaza_tipos_no_permitidos(entorno, tipo) -> None:
    with pytest.raises(TipoNoPermitido):
        adjuntar(entorno, tipo=tipo)


def test_rechaza_contenido_que_no_corresponde_al_tipo(entorno) -> None:
    with pytest.raises(ContenidoNoCoincide):
        adjuntar(entorno, contenido=PNG, tipo="image/jpeg")
    with pytest.raises(ContenidoNoCoincide):
        adjuntar(entorno, contenido=b"MZ ejecutable disfrazado", tipo="video/mp4")


def test_rechaza_archivo_vacio(entorno) -> None:
    with pytest.raises(ArchivoVacio):
        adjuntar(entorno, contenido=b"")


def test_limite_de_tamano_por_tipo(entorno) -> None:
    foto_grande = JPEG + b"0" * (LIMITE_FOTO_BYTES - len(JPEG) + 1)
    with pytest.raises(ArchivoDemasiadoGrande):
        adjuntar(entorno, contenido=foto_grande)

    # Un video puede pesar más que el límite de las fotos.
    video = MP4 + b"0" * (LIMITE_FOTO_BYTES + 1)
    assert adjuntar(entorno, contenido=video, tipo="video/mp4").creada
    with pytest.raises(ArchivoDemasiadoGrande):
        adjuntar(entorno, contenido=MP4 + b"0" * LIMITE_VIDEO_BYTES, tipo="video/mp4")


def test_huella_declarada_distinta_indica_alteracion_en_transito(entorno) -> None:
    with pytest.raises(HuellaNoCoincide):
        adjuntar(entorno, huella_declarada=sha(b"otro archivo"))
    assert entorno.evidencias.contar("SIN-1") == 0


def test_huella_declarada_en_mayusculas_se_acepta(entorno) -> None:
    assert adjuntar(entorno, huella_declarada=sha(JPEG).upper()).creada


def test_fecha_de_captura_futura_se_rechaza(entorno) -> None:
    futura = DatosCaptura(capturada_en=AHORA + timedelta(hours=1))
    with pytest.raises(FechaCapturaInvalida):
        adjuntar(entorno, datos=futura)


def test_tolera_relojes_de_celular_levemente_adelantados(entorno) -> None:
    adelantada = DatosCaptura(capturada_en=AHORA + timedelta(minutes=3))
    assert adjuntar(entorno, datos=adelantada).creada


def test_maximo_de_evidencias_por_siniestro(entorno) -> None:
    for numero in range(MAXIMO_EVIDENCIAS):
        adjuntar(entorno, contenido=JPEG + bytes([numero]))
    with pytest.raises(LimiteEvidencias):
        adjuntar(entorno, contenido=JPEG + b"extra")
    # Un reintento de una ya cargada sigue respondiendo aunque se llegó al máximo.
    assert not adjuntar(entorno, contenido=JPEG + bytes([0])).creada


@pytest.mark.parametrize("estado", [EstadoSiniestro.APROBADO, EstadoSiniestro.RECHAZADO])
def test_siniestro_evaluado_no_admite_evidencias(entorno, estado) -> None:
    entorno.siniestros.guardar(siniestro(estado=estado))
    with pytest.raises(SiniestroCerrado):
        adjuntar(entorno)


def test_siniestro_en_evaluacion_si_admite_evidencias(entorno) -> None:
    entorno.siniestros.guardar(siniestro(estado=EstadoSiniestro.EN_EVALUACION))
    assert adjuntar(entorno).creada


def test_siniestro_ajeno_responde_como_inexistente(entorno) -> None:
    with pytest.raises(SiniestroNoEncontrado):
        adjuntar(entorno, actor=OTRO_CLIENTE)
    with pytest.raises(SiniestroNoEncontrado):
        adjuntar(entorno, siniestro_id="SIN-404")


@pytest.mark.parametrize("actor", [OPERADOR, AUDITOR, ASESOR])
def test_solo_el_cliente_adjunta(entorno, actor) -> None:
    with pytest.raises(AccesoDenegado):
        adjuntar(entorno, actor=actor)


def test_si_el_almacen_falla_no_se_registra_la_evidencia(entorno) -> None:
    class Caido:
        def guardar(self, clave, contenido, tipo_contenido="application/pdf"):
            raise AlmacenNoDisponible("sin red")

        def leer(self, clave):
            raise AlmacenNoDisponible("sin red")

    entorno.servicio._almacen = Caido()
    with pytest.raises(AlmacenNoDisponible):
        adjuntar(entorno)
    assert entorno.evidencias.contar("SIN-1") == 0
    assert entorno.acciones() == []


def test_ubicacion_incompleta_no_es_valida() -> None:
    with pytest.raises(ValueError):
        DatosCaptura(latitud=4.7)
    with pytest.raises(ValueError):
        DatosCaptura(precision_metros=10)
    with pytest.raises(ValueError):
        DatosCaptura(latitud=95, longitud=10)


# --- Consulta, descarga e integridad (EC10) ------------------------------------------------


def test_el_titular_lista_sus_evidencias_y_queda_auditado(entorno) -> None:
    adjuntar(entorno)
    adjuntar(entorno, contenido=MP4, tipo="video/mp4", datos=SIN_UBICACION)

    evidencias = entorno.servicio.listar(CLIENTE, "SIN-1")

    assert [e.tipo for e in evidencias] == [TipoEvidencia.FOTO, TipoEvidencia.VIDEO]
    assert entorno.acciones() == ["CARGA", "CARGA", "CONSULTA"]
    consulta = entorno.auditoria.registros[-1]
    assert (consulta.actor_id, consulta.rol, consulta.ip) == ("CLI-001", "CLIENTE", "10.0.0.5")


@pytest.mark.parametrize("actor", [OPERADOR, AUDITOR])
def test_operaciones_y_cumplimiento_consultan_cualquier_siniestro(entorno, actor) -> None:
    adjuntar(entorno)
    assert len(entorno.servicio.listar(actor, "SIN-1")) == 1


def test_otros_roles_y_clientes_ajenos_no_consultan(entorno) -> None:
    adjuntar(entorno)
    with pytest.raises(AccesoDenegado):
        entorno.servicio.listar(ASESOR, "SIN-1")
    with pytest.raises(SiniestroNoEncontrado):
        entorno.servicio.listar(OTRO_CLIENTE, "SIN-1")


def test_descarga_verifica_la_huella(entorno) -> None:
    cargada = adjuntar(entorno).evidencia

    evidencia, contenido = entorno.servicio.leer(OPERADOR, "SIN-1", cargada.evidencia_id)

    assert contenido == JPEG
    assert evidencia.huella_sha256 == sha(contenido)
    descarga = entorno.auditoria.registros[-1]
    assert descarga.accion.value == "DESCARGA"
    assert descarga.evidencia_id == cargada.evidencia_id


def test_archivo_alterado_en_el_almacen_se_detecta_y_audita(entorno) -> None:
    cargada = adjuntar(entorno).evidencia
    # Alguien reemplaza el archivo por fuera de la aplicación.
    entorno.almacen._por_clave[cargada.clave_almacenamiento] = JPEG + b"retocada"

    with pytest.raises(EvidenciaAlterada):
        entorno.servicio.leer(OPERADOR, "SIN-1", cargada.evidencia_id)

    falla = entorno.auditoria.registros[-1]
    assert falla.accion.value == "INTEGRIDAD_FALLIDA"
    assert falla.actor_id == "OPS-1"
    assert "huella" in falla.detalle


def test_archivo_borrado_del_almacen_se_reporta_como_alterado(entorno) -> None:
    cargada = adjuntar(entorno).evidencia
    del entorno.almacen._por_clave[cargada.clave_almacenamiento]

    with pytest.raises(EvidenciaAlterada):
        entorno.servicio.leer(CLIENTE, "SIN-1", cargada.evidencia_id)
    assert entorno.acciones()[-1] == "INTEGRIDAD_FALLIDA"


def test_evidencia_de_otro_siniestro_no_se_descarga(entorno) -> None:
    entorno.siniestros.guardar(siniestro(siniestro_id="SIN-2"))
    cargada = adjuntar(entorno, siniestro_id="SIN-2").evidencia

    with pytest.raises(EvidenciaNoEncontrada):
        entorno.servicio.leer(CLIENTE, "SIN-1", cargada.evidencia_id)
    with pytest.raises(EvidenciaNoEncontrada):
        entorno.servicio.leer(CLIENTE, "SIN-1", "EVI-404")


def test_bitacora_solo_para_operaciones_y_cumplimiento(entorno) -> None:
    cargada = adjuntar(entorno).evidencia
    entorno.servicio.leer(OPERADOR, "SIN-1", cargada.evidencia_id)

    bitacora = entorno.servicio.auditoria(AUDITOR, "SIN-1")

    assert [r.accion.value for r in bitacora] == ["CARGA", "DESCARGA"]
    # Consultar la bitácora también queda registrado.
    assert entorno.acciones()[-1] == "CONSULTA_AUDITORIA"
    with pytest.raises(AccesoDenegado):
        entorno.servicio.auditoria(CLIENTE, "SIN-1")
    with pytest.raises(SiniestroNoEncontrado):
        entorno.servicio.auditoria(OPERADOR, "SIN-404")


def test_todas_las_cargas_son_atribuibles_a_un_autor(entorno) -> None:
    adjuntar(entorno)
    adjuntar(entorno, contenido=PNG, tipo="image/png")

    cargas = [r for r in entorno.auditoria.registros if r.accion.value == "CARGA"]
    assert len(cargas) == 2
    assert all(r.actor_id == "CLI-001" and r.rol == "CLIENTE" for r in cargas)
    assert all(r.ocurrido_en == AHORA for r in cargas)


# --- Utilidades ----------------------------------------------------------------------------


def test_firmas_de_archivo() -> None:
    assert contenido_corresponde("image/jpeg", JPEG)
    assert contenido_corresponde("image/png", PNG)
    assert contenido_corresponde("video/mp4", MP4)
    assert not contenido_corresponde("video/mp4", b"\x00\x00ftyp")
    assert not contenido_corresponde("application/pdf", b"%PDF-1.7")


def test_nombre_de_archivo_sin_rutas() -> None:
    assert nombre_seguro("../../etc/passwd") == "passwd"
    assert nombre_seguro("C:\\Users\\ana\\foto.jpg") == "foto.jpg"
    assert nombre_seguro("") is None
    assert nombre_seguro("x" * 200) == "x" * 120


def test_dos_envios_simultaneos_del_mismo_archivo_devuelven_una_evidencia(entorno) -> None:
    from app.siniestros.evidencias import EvidenciaDuplicada

    repositorio = entorno.evidencias
    guardar_original = repositorio.guardar

    def guardar_tras_otro_envio(evidencia):
        # Otro envío gana la carrera justo antes de este.
        guardar_original(evidencia.model_copy(update={"evidencia_id": "EVI-GANADORA"}))
        raise EvidenciaDuplicada(evidencia.huella_sha256)

    repositorio.guardar = guardar_tras_otro_envio
    resultado = adjuntar(entorno)

    assert not resultado.creada
    assert resultado.evidencia.evidencia_id == "EVI-GANADORA"


def test_almacen_de_evidencias_en_disco_sin_bucket(monkeypatch, tmp_path) -> None:
    from app.polizas.almacenamiento import AlmacenEnDisco
    from app.siniestros.evidencias import crear_almacen_evidencias

    monkeypatch.delenv("POLIZAS_S3_BUCKET", raising=False)
    monkeypatch.setenv("SINIESTROS_EVIDENCIAS_DIR", str(tmp_path))

    almacen = crear_almacen_evidencias()
    almacen.guardar("evidencias-siniestros/SIN-1/a.jpg", JPEG, "image/jpeg")

    assert isinstance(almacen, AlmacenEnDisco)
    assert (tmp_path / "evidencias-siniestros" / "SIN-1" / "a.jpg").read_bytes() == JPEG


def test_almacen_de_evidencias_con_bucket_usa_s3_con_respaldo(monkeypatch, tmp_path) -> None:
    from app.polizas.almacenamiento import AlmacenConRespaldo
    from app.siniestros.evidencias import crear_almacen_evidencias

    monkeypatch.setenv("POLIZAS_S3_BUCKET", "solventa-polizas")
    monkeypatch.setenv("POLIZAS_S3_ENDPOINT_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("SINIESTROS_EVIDENCIAS_DIR", str(tmp_path))

    assert isinstance(crear_almacen_evidencias(), AlmacenConRespaldo)

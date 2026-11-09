import time

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app.polizas.almacenamiento import (
    AlmacenConRespaldo,
    AlmacenEnDisco,
    AlmacenEnMemoria,
    AlmacenNoDisponible,
    AlmacenS3,
    DocumentoInmutable,
    crear_almacen,
)
from tests.emision.fabrica import crear_entorno
from tests.firmas.fabrica import CLIENTE, COTIZACION

CLAVE = "polizas/POL-1.pdf"
PDF = b"%PDF-1.4 contenido"


def error_aws(codigo: str, operacion: str = "GetObject") -> ClientError:
    return ClientError({"Error": {"Code": codigo, "Message": "detalle interno"}}, operacion)


class CuerpoFalso:
    def __init__(self, contenido: bytes):
        self._contenido = contenido

    def read(self) -> bytes:
        return self._contenido


class ClienteS3Falso:
    """Reproduce lo que S3 responde: el objeto, NoSuchKey, o un fallo de acceso o de red."""

    def __init__(self):
        self.objetos: dict[tuple[str, str], bytes] = {}
        self.puestos: list[dict] = []
        self.falla: Exception | None = None
        self.llamadas = 0

    def get_object(self, Bucket, Key):
        self.llamadas += 1
        if self.falla:
            raise self.falla
        if (Bucket, Key) not in self.objetos:
            raise error_aws("NoSuchKey")
        return {"Body": CuerpoFalso(self.objetos[(Bucket, Key)])}

    def put_object(self, Bucket, Key, Body, **extra):
        self.llamadas += 1
        if self.falla:
            raise self.falla
        self.objetos[(Bucket, Key)] = Body
        self.puestos.append({"Bucket": Bucket, "Key": Key, **extra})


@pytest.fixture
def s3():
    return ClienteS3Falso()


# --- AlmacenS3 ---------------------------------------------------------------------------


def test_s3_guarda_y_lee_con_prefijo_y_cifrado(s3) -> None:
    almacen = AlmacenS3("bucket-polizas", prefijo="/produccion/", cliente=s3)

    almacen.guardar(CLAVE, PDF)

    assert almacen.leer(CLAVE) == PDF
    assert ("bucket-polizas", f"produccion/{CLAVE}") in s3.objetos
    assert s3.puestos[0]["ContentType"] == "application/pdf"
    assert s3.puestos[0]["ServerSideEncryption"] == "AES256"


def test_s3_un_objeto_inexistente_devuelve_none(s3) -> None:
    assert AlmacenS3("b", cliente=s3).leer(CLAVE) is None


def test_s3_repetir_el_mismo_contenido_no_vuelve_a_escribir(s3) -> None:
    almacen = AlmacenS3("b", cliente=s3)
    almacen.guardar(CLAVE, PDF)

    almacen.guardar(CLAVE, PDF)

    assert len(s3.puestos) == 1


def test_s3_no_sobrescribe_un_documento_distinto(s3) -> None:
    almacen = AlmacenS3("b", cliente=s3)
    almacen.guardar(CLAVE, PDF)

    with pytest.raises(DocumentoInmutable):
        almacen.guardar(CLAVE, b"%PDF-otro")
    assert almacen.leer(CLAVE) == PDF


@pytest.mark.parametrize(
    "fallo",
    [
        error_aws("AccessDenied"),
        error_aws("NoSuchBucket"),
        EndpointConnectionError(endpoint_url="http://s3.invalido"),
        RuntimeError("sin credenciales"),
    ],
)
def test_s3_traduce_fallos_a_almacen_no_disponible(s3, fallo) -> None:
    s3.falla = fallo
    almacen = AlmacenS3("b", cliente=s3)

    with pytest.raises(AlmacenNoDisponible):
        almacen.guardar(CLAVE, PDF)
    with pytest.raises(AlmacenNoDisponible):
        almacen.leer(CLAVE)


def test_s3_el_error_no_filtra_el_detalle_del_proveedor(s3) -> None:
    s3.falla = error_aws("AccessDenied")

    with pytest.raises(AlmacenNoDisponible) as capturado:
        AlmacenS3("b", cliente=s3).leer(CLAVE)

    assert "AccessDenied" in str(capturado.value)
    assert "detalle interno" not in str(capturado.value)


def test_s3_rechaza_claves_que_se_salen_del_prefijo(s3) -> None:
    almacen = AlmacenS3("b", prefijo="polizas", cliente=s3)

    for clave in ("../otro.pdf", "/absoluta.pdf", "a/../../b.pdf"):
        with pytest.raises(AlmacenNoDisponible):
            almacen.leer(clave)


# --- AlmacenConRespaldo ------------------------------------------------------------------


@pytest.fixture
def disco(tmp_path):
    return AlmacenEnDisco(tmp_path)


def test_con_s3_disponible_guarda_y_lee_de_s3_sin_tocar_el_disco(s3, disco, tmp_path) -> None:
    almacen = AlmacenConRespaldo(AlmacenS3("b", cliente=s3), disco)

    almacen.guardar(CLAVE, PDF)

    assert almacen.leer(CLAVE) == PDF
    assert ("b", CLAVE) in s3.objetos
    assert list(tmp_path.rglob("*.pdf")) == []


def test_sin_s3_guarda_en_disco_y_lo_encuentra(s3, disco, tmp_path) -> None:
    s3.falla = EndpointConnectionError(endpoint_url="http://s3.invalido")
    almacen = AlmacenConRespaldo(AlmacenS3("b", cliente=s3), disco)

    almacen.guardar(CLAVE, PDF)

    assert almacen.leer(CLAVE) == PDF
    assert [p.name for p in tmp_path.rglob("*.pdf")] == ["POL-1.pdf"]


def test_lee_del_disco_un_documento_guardado_mientras_s3_estaba_caido(s3, disco) -> None:
    disco.guardar(CLAVE, PDF)  # quedó en disco durante una caída de S3
    almacen = AlmacenConRespaldo(AlmacenS3("b", cliente=s3), disco)  # S3 ya responde, sin él

    assert almacen.leer(CLAVE) == PDF


def test_s3_tiene_prioridad_si_el_documento_esta_en_ambos(s3, disco) -> None:
    s3.objetos[("b", CLAVE)] = b"%PDF-de-s3"
    disco.guardar(CLAVE, b"%PDF-de-disco")

    assert AlmacenConRespaldo(AlmacenS3("b", cliente=s3), disco).leer(CLAVE) == b"%PDF-de-s3"


def test_un_documento_inexistente_devuelve_none(s3, disco) -> None:
    assert AlmacenConRespaldo(AlmacenS3("b", cliente=s3), disco).leer(CLAVE) is None


def test_el_documento_distinto_sigue_siendo_inmutable_y_no_cae_al_disco(s3, disco, tmp_path):
    almacen = AlmacenConRespaldo(AlmacenS3("b", cliente=s3), disco)
    almacen.guardar(CLAVE, PDF)

    with pytest.raises(DocumentoInmutable):
        almacen.guardar(CLAVE, b"%PDF-otro")
    assert list(tmp_path.rglob("*.pdf")) == []


def test_tras_un_fallo_omite_s3_durante_la_pausa_y_luego_reintenta(s3, disco) -> None:
    ahora = [100.0]
    s3.falla = EndpointConnectionError(endpoint_url="http://s3.invalido")
    almacen = AlmacenConRespaldo(
        AlmacenS3("b", cliente=s3), disco, pausa_segundos=30, reloj=lambda: ahora[0]
    )

    almacen.guardar("polizas/a.pdf", PDF)
    assert s3.llamadas == 1
    almacen.guardar("polizas/b.pdf", PDF)
    almacen.leer("polizas/a.pdf")
    assert s3.llamadas == 1  # no vuelve a esperar a S3 dentro de la pausa

    ahora[0] = 131.0
    s3.falla = None
    almacen.guardar("polizas/c.pdf", PDF)
    assert ("b", "polizas/c.pdf") in s3.objetos


def test_si_fallan_ambos_almacenes_el_error_sube() -> None:
    class Caido:
        def guardar(self, clave, contenido):
            raise AlmacenNoDisponible("caído")

        def leer(self, clave):
            raise AlmacenNoDisponible("caído")

    almacen = AlmacenConRespaldo(Caido(), Caido())

    with pytest.raises(AlmacenNoDisponible):
        almacen.guardar(CLAVE, PDF)
    with pytest.raises(AlmacenNoDisponible):
        almacen.leer(CLAVE)


# --- crear_almacen: con un cliente boto3 real y sin nube -----------------------------------


@pytest.fixture
def sin_nube(monkeypatch, tmp_path):
    """Un bucket configurado pero sin cuenta de AWS: nada responde en ese endpoint."""
    for variable in ("POLIZAS_S3_BUCKET", "POLIZAS_S3_PREFIJO", "POLIZAS_S3_ENDPOINT_URL"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("POLIZAS_DOCUMENTOS_DIR", str(tmp_path / "docs"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    return tmp_path / "docs"


def test_sin_bucket_configurado_usa_solo_el_disco(sin_nube) -> None:
    assert isinstance(crear_almacen(), AlmacenEnDisco)


def test_con_bucket_y_sin_credenciales_guarda_en_disco(sin_nube, monkeypatch) -> None:
    monkeypatch.setenv("POLIZAS_S3_BUCKET", "bucket-que-no-existe")
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(sin_nube / "no-existe"))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(sin_nube / "no-existe"))
    for variable in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.delenv(variable, raising=False)

    almacen = crear_almacen()
    assert isinstance(almacen, AlmacenConRespaldo)
    inicio = time.monotonic()
    almacen.guardar(CLAVE, PDF)

    assert almacen.leer(CLAVE) == PDF
    assert (sin_nube / CLAVE).read_bytes() == PDF
    assert time.monotonic() - inicio < 10


def test_con_bucket_y_sin_red_guarda_en_disco_y_responde_rapido(sin_nube, monkeypatch) -> None:
    monkeypatch.setenv("POLIZAS_S3_BUCKET", "bucket-que-no-existe")
    monkeypatch.setenv("POLIZAS_S3_ENDPOINT_URL", "http://127.0.0.1:9")  # puerto cerrado
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "prueba")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "prueba")

    almacen = crear_almacen()
    inicio = time.monotonic()
    almacen.guardar(CLAVE, PDF)
    primera = time.monotonic() - inicio
    inicio = time.monotonic()
    assert almacen.leer(CLAVE) == PDF
    segunda = time.monotonic() - inicio

    assert (sin_nube / CLAVE).read_bytes() == PDF
    assert primera < 15
    assert segunda < 1  # ya está en pausa: no vuelve a esperar a S3


# --- La emisión completa sobre el almacén con respaldo ---------------------------------------


def test_la_emision_y_la_descarga_funcionan_con_s3_caido(s3, disco, tmp_path) -> None:
    s3.falla = EndpointConnectionError(endpoint_url="http://s3.invalido")
    e = crear_entorno()
    e.emision._almacen = AlmacenConRespaldo(AlmacenS3("b", cliente=s3), disco)

    e.firmar()
    poliza_id = e.firmas_servicio.poliza_emitida(COTIZACION)

    documento = e.emision.documento_del_cliente(CLIENTE, poliza_id)
    assert documento.contenido.startswith(b"%PDF")
    assert [p.name for p in tmp_path.rglob("*.pdf")] == [f"{poliza_id}.pdf"]


def test_el_almacen_en_memoria_sigue_cumpliendo_el_mismo_contrato() -> None:
    almacen = AlmacenEnMemoria()
    almacen.guardar(CLAVE, PDF)

    assert almacen.leer(CLAVE) == PDF
    with pytest.raises(DocumentoInmutable):
        almacen.guardar(CLAVE, b"otro")

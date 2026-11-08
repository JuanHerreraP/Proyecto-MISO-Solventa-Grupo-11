"""Compilación de los documentos PDF de la póliza (HU12) y de sus endosos (HU16).

La salida es determinista: los mismos datos producen los mismos bytes (`invariant=1` fija
fechas e identificador internos y la página va sin comprimir). Así, emitir dos veces la misma
póliza no genera documentos distintos y su huella SHA-256 sirve para verificar la integridad.
"""

import io
from decimal import Decimal

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas

from app.firmas.modelos import ProcesoFirma
from app.polizas.dominio.endosos import Endoso
from app.polizas.dominio.modelos import ZONA_COLOMBIA, Poliza

_MARGEN = 2 * cm
_ANCHO_TEXTO = A4[0] - 2 * _MARGEN


def _moneda(valor: Decimal, moneda: str) -> str:
    entero = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{moneda} {entero}"


def _fecha_hora(instante) -> str:
    return instante.astimezone(ZONA_COLOMBIA).strftime("%Y-%m-%d %H:%M (hora Colombia)")


def _lineas(texto: str, fuente: str, tamano: float, canvas: Canvas, ancho: float) -> list[str]:
    lineas: list[str] = []
    actual = ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if canvas.stringWidth(prueba, fuente, tamano) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


class _Pagina:
    def __init__(self, canvas: Canvas):
        self.c = canvas
        self.y = A4[1] - _MARGEN

    def espacio(self, alto: float) -> None:
        if self.y - alto < _MARGEN:
            self.c.showPage()
            self.y = A4[1] - _MARGEN

    def titulo(self, texto: str) -> None:
        self.espacio(1.2 * cm)
        self.y -= 0.25 * cm
        self.c.setFont("Helvetica-Bold", 11)
        self.c.drawString(_MARGEN, self.y, texto.upper())
        self.y -= 0.15 * cm
        self.c.line(_MARGEN, self.y, A4[0] - _MARGEN, self.y)
        self.y -= 0.45 * cm

    def par(self, etiqueta: str, valor: str, ancho_etiqueta: float = 5 * cm) -> None:
        self.espacio(0.6 * cm)
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(_MARGEN, self.y, etiqueta)
        self.c.setFont("Helvetica", 9)
        self.c.drawString(_MARGEN + ancho_etiqueta, self.y, valor)
        self.y -= 0.45 * cm

    def parrafo(self, texto: str, tamano: float = 9, fuente: str = "Helvetica") -> None:
        self.c.setFont(fuente, tamano)
        for linea in _lineas(texto, fuente, tamano, self.c, _ANCHO_TEXTO):
            self.espacio(0.5 * cm)
            self.c.drawString(_MARGEN, self.y, linea)
            self.y -= 0.42 * cm
        self.y -= 0.1 * cm


def generar_pdf_poliza(poliza: Poliza, proceso: ProcesoFirma) -> bytes:
    """Arma el documento definitivo con los datos de la póliza y la evidencia de la firma."""

    contrato = proceso.contrato
    buffer = io.BytesIO()
    canvas = Canvas(
        buffer,
        pagesize=A4,
        pageCompression=0,
        invariant=1,
        title=f"Póliza {poliza.numero_poliza}",
        author="Solventa",
    )
    pag = _Pagina(canvas)

    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(_MARGEN, pag.y, "Solventa")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(_MARGEN, pag.y - 0.6 * cm, "Póliza de seguro")
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawRightString(A4[0] - _MARGEN, pag.y, f"No. {poliza.numero_poliza}")
    pag.y -= 1.2 * cm

    pag.titulo("Datos de la póliza")
    pag.par("Seguro", contrato.nombre_ramo)
    pag.par("Estado", "Vigente")
    pag.par("Emitida", _fecha_hora(poliza.emitida_en))
    pag.par("Vigencia", f"{poliza.fecha_inicio.isoformat()} a {poliza.fecha_fin.isoformat()}")

    pag.titulo("Asegurado")
    pag.par("Nombre", poliza.titular_nombre)
    pag.par("Documento", f"{poliza.titular_tipo_documento} {poliza.titular_numero_documento}")
    pag.par("Correo", str(contrato.titular.email))

    pag.titulo("Cobertura")
    cobertura = poliza.cobertura_principal
    pag.par("Cobertura", cobertura.nombre)
    pag.par("Suma asegurada", _moneda(cobertura.suma_asegurada, poliza.moneda))
    if cobertura.descripcion:
        pag.parrafo(cobertura.descripcion)

    if contrato.exclusiones_principales:
        pag.titulo("Exclusiones principales")
        for numero, exclusion in enumerate(contrato.exclusiones_principales, start=1):
            pag.parrafo(f"{numero}. {exclusion}")

    pag.titulo("Tarifa cobrada")
    pag.par("Prima total", _moneda(poliza.prima_total, poliza.moneda))
    pag.par("Pago", contrato.pago_id)
    pag.par("Referencia", contrato.referencia_pago or "-")
    pag.par("Fecha del pago", _fecha_hora(contrato.fecha_pago))

    pag.titulo("Condiciones")
    for numero, clausula in enumerate(contrato.clausulas, start=1):
        pag.parrafo(f"{numero}. {clausula}")

    pag.titulo("Firma electrónica")
    if proceso.firmado_en is not None:
        pag.par("Firmado el", _fecha_hora(proceso.firmado_en))
    pag.par("Firmante", proceso.firmante_id or "-")
    pag.par("IP", proceso.ip_firmante or "-")
    pag.par("Proveedor", proceso.referencia_proveedor or "-")
    pag.par("Sello", proceso.sello_proveedor or "-")
    pag.par("Huella del contrato", "")
    pag.parrafo(proceso.huella_documento, tamano=7, fuente="Courier")

    lado = 2.6 * cm
    # El título y el QR van juntos: si no caben en la página, pasan ambos a la siguiente.
    pag.espacio(lado + 1.6 * cm)
    pag.titulo("Verificación")
    pag.par("Código", poliza.codigo_verificacion)
    qr = QrCodeWidget(poliza.contenido_qr, barLevel="M")
    x0, y0, x1, y1 = qr.getBounds()
    dibujo = Drawing(lado, lado, transform=[lado / (x1 - x0), 0, 0, lado / (y1 - y0), 0, 0])
    dibujo.add(qr)
    renderPDF.draw(dibujo, canvas, _MARGEN, pag.y - lado)
    pag.y -= lado

    canvas.save()
    return buffer.getvalue()


_ROLES_SOLICITANTE = {
    "CLIENTE": "El asegurado, desde el portal web",
    "ASESOR_VENTAS": "Asesor de ventas, a solicitud del asegurado",
}


def generar_pdf_endoso(poliza: Poliza, endoso: Endoso) -> bytes:
    """Anexo de la póliza con los cambios del endoso. El documento de la póliza no se toca."""

    buffer = io.BytesIO()
    canvas = Canvas(
        buffer,
        pagesize=A4,
        pageCompression=0,
        invariant=1,
        title=f"Endoso {endoso.numero_endoso} a la póliza {poliza.numero_poliza}",
        author="Solventa",
    )
    pag = _Pagina(canvas)

    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(_MARGEN, pag.y, "Solventa")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(_MARGEN, pag.y - 0.6 * cm, "Endoso a la póliza de seguro")
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawRightString(A4[0] - _MARGEN, pag.y, f"Endoso No. {endoso.numero_endoso}")
    pag.y -= 1.2 * cm

    pag.titulo("Póliza")
    pag.par("Número", poliza.numero_poliza)
    pag.par("Seguro", poliza.nombre_ramo)
    pag.par("Asegurado", poliza.titular_nombre)
    pag.par("Documento", f"{poliza.titular_tipo_documento} {poliza.titular_numero_documento}")
    pag.par("Vigencia", f"{poliza.fecha_inicio.isoformat()} a {poliza.fecha_fin.isoformat()}")

    pag.titulo("Endoso")
    pag.par("Identificador", endoso.endoso_id)
    pag.par("Rige desde", endoso.fecha_efecto.isoformat())
    pag.par("Registrado", _fecha_hora(endoso.creado_en))
    solicitante = _ROLES_SOLICITANTE.get(endoso.rol_solicitante, endoso.rol_solicitante)
    pag.par("Solicitado por", solicitante)

    pag.titulo("Cambios")
    for numero, cambio in enumerate(endoso.cambios, start=1):
        pag.parrafo(f"{numero}. {cambio.descripcion}")

    pag.titulo("Coberturas vigentes")
    principal = poliza.cobertura_principal
    for cobertura in (principal, *endoso.coberturas_opcionales):
        pag.par(cobertura.nombre, _moneda(cobertura.suma_asegurada, poliza.moneda), 7 * cm)

    if endoso.beneficiarios or poliza.ramo.value == "VIDA":
        pag.titulo("Beneficiarios")
        if not endoso.beneficiarios:
            pag.parrafo(
                "Sin beneficiarios designados: la indemnización se paga a los herederos "
                "legales del asegurado."
            )
        for b in endoso.beneficiarios:
            pag.par(
                f"{b.porcentaje:.2f}".replace(".", ",") + " %",
                f"{b.nombre_completo} ({b.parentesco}) - {b.tipo_documento} {b.numero_documento}",
            )

    pag.titulo("Ajuste de prima")
    pag.par("Prima anterior", _moneda(endoso.prima_anterior, endoso.moneda))
    if endoso.es_cobro:
        concepto = "Cobro adicional"
    elif endoso.es_devolucion:
        concepto = "Devolución de prima no devengada"
    else:
        concepto = "Sin ajuste"
    pag.par(concepto, _moneda(abs(endoso.ajuste_prima), endoso.moneda))
    pag.par("Prima total", _moneda(endoso.prima_nueva, endoso.moneda))
    pag.parrafo(
        f"El ajuste corresponde a {endoso.dias_restantes} de los {endoso.dias_vigencia} días de "
        "vigencia de la póliza, contados desde la fecha en que rige el endoso."
    )

    pag.titulo("Condiciones")
    pag.parrafo(
        "Este endoso hace parte integral de la póliza. Las condiciones no modificadas aquí "
        "continúan vigentes en los términos del documento de la póliza."
    )
    pag.par("Huella de la solicitud", "")
    pag.parrafo(endoso.huella_solicitud, tamano=7, fuente="Courier")

    canvas.save()
    return buffer.getvalue()

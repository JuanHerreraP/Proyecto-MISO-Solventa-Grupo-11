"""Compilación del documento PDF de la póliza (HU12).

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

    def par(self, etiqueta: str, valor: str) -> None:
        self.espacio(0.6 * cm)
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(_MARGEN, self.y, etiqueta)
        self.c.setFont("Helvetica", 9)
        self.c.drawString(_MARGEN + 5 * cm, self.y, valor)
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

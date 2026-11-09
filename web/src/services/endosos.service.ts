import { fetchAutenticado } from "./session";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type ConceptoAjuste = "COBRO" | "DEVOLUCION" | "SIN_AJUSTE";
export type TipoEndoso = "BENEFICIARIOS" | "COBERTURAS" | "BENEFICIARIOS_Y_COBERTURAS";

export interface Cobertura {
  codigo: string;
  nombre: string;
  suma_asegurada: string;
  descripcion: string | null;
}

export interface CoberturaDisponible {
  codigo: string;
  nombre: string;
  descripcion: string;
  suma_minima: string;
  suma_maxima: string;
}

export interface Beneficiario {
  nombre_completo: string;
  tipo_documento: string;
  numero_documento: string;
  parentesco: string;
  porcentaje: string;
}

export interface OpcionesModificacion {
  poliza_id: string;
  numero_poliza: string;
  nombre_ramo: string;
  estado: string;
  modificable: boolean;
  fecha_inicio: string;
  fecha_fin: string;
  prima_total: string;
  moneda: string;
  cobertura_principal: Cobertura;
  coberturas_opcionales: Cobertura[];
  coberturas_disponibles: CoberturaDisponible[];
  admite_beneficiarios: boolean;
  max_beneficiarios: number;
  beneficiarios: Beneficiario[];
}

export interface CambioEndoso {
  tipo: string;
  descripcion: string;
  antes: Record<string, string> | null;
  despues: Record<string, string> | null;
}

export interface PropuestaEndoso {
  poliza_id: string;
  tipo: TipoEndoso;
  cambios: CambioEndoso[];
  beneficiarios: Beneficiario[];
  coberturas_opcionales: Cobertura[];
  fecha_efecto: string;
  dias_vigencia: number;
  dias_restantes: number;
  prima_anterior: string;
  ajuste_prima: string;
  concepto_ajuste: ConceptoAjuste;
  prima_nueva: string;
  moneda: string;
}

export interface Endoso extends Omit<PropuestaEndoso, "poliza_id"> {
  endoso_id: string;
  poliza_id: string;
  numero_endoso: number;
  rol_solicitante: string;
  creado_en: string;
  huella_documento: string;
}

/** Estado deseado de la póliza. Un campo ausente no cambia; una lista vacía quita todo. */
export interface SolicitudModificacion {
  beneficiarios?: Beneficiario[];
  coberturas_opcionales?: { codigo: string; suma_asegurada: string }[];
}

/** Error de negocio del backend: el código permite decidir qué mostrar y el campo, dónde. */
export class ErrorEndoso extends Error {
  readonly codigo: string;
  readonly status: number;
  readonly campo?: string;

  constructor(message: string, codigo: string, status: number, campo?: string) {
    super(message);
    this.codigo = codigo;
    this.status = status;
    this.campo = campo;
  }
}

async function procesar<T>(respuesta: Response, mensaje: string): Promise<T> {
  if (respuesta.ok) return respuesta.json();
  const cuerpo = await respuesta.json().catch(() => null);
  const detalle = cuerpo?.detail;
  if (detalle && typeof detalle === "object" && !Array.isArray(detalle)) {
    throw new ErrorEndoso(
      typeof detalle.mensaje === "string" ? detalle.mensaje : mensaje,
      detalle.codigo ?? "ERROR",
      respuesta.status,
      detalle.campo,
    );
  }
  // 422 de validación de FastAPI: lista de errores por campo.
  if (Array.isArray(detalle)) {
    throw new ErrorEndoso("Revisa los datos ingresados.", "DATOS_INVALIDOS", respuesta.status);
  }
  throw new ErrorEndoso(mensaje, "ERROR", respuesta.status);
}

function ruta(polizaId: string, sufijo = ""): string {
  return `${API_URL}/api/v1/polizas/${encodeURIComponent(polizaId)}/endosos${sufijo}`;
}

function post(url: string, cuerpo: unknown, cabeceras: Record<string, string> = {}): Promise<Response> {
  return fetchAutenticado(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...cabeceras },
    body: JSON.stringify(cuerpo),
  });
}

export async function obtenerOpciones(polizaId: string): Promise<OpcionesModificacion> {
  return procesar(
    await fetchAutenticado(ruta(polizaId, "/opciones")),
    "No fue posible consultar la póliza.",
  );
}

export async function simularEndoso(
  polizaId: string, solicitud: SolicitudModificacion,
): Promise<PropuestaEndoso> {
  return procesar(
    await post(ruta(polizaId, "/simulacion"), solicitud),
    "No fue posible calcular el ajuste.",
  );
}

/**
 * Confirma los cambios. La clave de idempotencia es la misma en cada reintento de una misma
 * confirmación: si la respuesta se pierde, repetir no crea un segundo endoso.
 */
export async function confirmarEndoso(
  polizaId: string, solicitud: SolicitudModificacion, claveIdempotencia: string,
): Promise<Endoso> {
  return procesar(
    await post(
      ruta(polizaId),
      { ...solicitud, acepta_condiciones: true },
      { "Idempotency-Key": claveIdempotencia },
    ),
    "No fue posible emitir el endoso.",
  );
}

export async function listarEndosos(polizaId: string): Promise<Endoso[]> {
  const historial = await procesar<{ endosos: Endoso[] }>(
    await fetchAutenticado(ruta(polizaId)),
    "No fue posible consultar los endosos.",
  );
  return historial.endosos;
}

function nombreDeArchivo(respuesta: Response, endosoId: string): string {
  const cabecera = respuesta.headers.get("Content-Disposition") ?? "";
  return /filename="([^"]+)"/.exec(cabecera)?.[1] ?? `endoso-${endosoId}.pdf`;
}

/** Descarga el PDF del endoso con la sesión del cliente (no sirve como enlace directo). */
export async function descargarEndoso(polizaId: string, endosoId: string): Promise<void> {
  const respuesta = await fetchAutenticado(
    ruta(polizaId, `/${encodeURIComponent(endosoId)}/documento`),
  );
  if (!respuesta.ok) {
    await procesar(respuesta, "No fue posible descargar el endoso.");
  }
  const url = URL.createObjectURL(await respuesta.blob());
  try {
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = nombreDeArchivo(respuesta, endosoId);
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

import { fetchAutenticado } from "./session";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type EstadoCicloRenovacion =
  | "PREAVISADA"
  | "DESACTIVADA"
  | "SIN_MEDIO_DE_PAGO"
  | "COBRO_PENDIENTE"
  | "COBRO_RECHAZADO"
  | "NO_RENOVABLE"
  | "NO_APLICADA"
  | "NO_PAGADA"
  | "RENOVADA";

/** Lo que hizo la renovación automática con el último periodo de la póliza (HU17). */
export interface CicloRenovacion {
  vence_el: string;
  estado: EstadoCicloRenovacion;
  preaviso_enviado_en: string | null;
  prima_avisada: string | null;
  moneda: string | null;
  renovacion_id: string | null;
  motivo: string | null;
  documento_disponible: boolean;
  contrato_enviado_en: string | null;
}

export interface RenovacionAutomatica {
  poliza_id: string;
  disponible: boolean;
  activa: boolean;
  /** Solo los últimos dígitos: el token de la tarjeta nunca vuelve al navegador. */
  tarjeta: { ultimos_digitos: string | null } | null;
  vence_el: string;
  preaviso_desde: string;
  cobro_programado_para: string;
  actualizado_en: string | null;
  ultimo_ciclo: CicloRenovacion | null;
}

export interface SolicitudRenovacionAutomatica {
  activa: boolean;
  tarjeta?: { token_tarjeta: string; ultimos_digitos?: string };
  quitar_tarjeta?: boolean;
}

export class ErrorRenovacionAutomatica extends Error {
  readonly codigo: string;
  readonly status: number;

  constructor(message: string, codigo: string, status: number) {
    super(message);
    this.codigo = codigo;
    this.status = status;
  }
}

async function error(respuesta: Response, mensaje: string): Promise<ErrorRenovacionAutomatica> {
  const cuerpo = await respuesta.json().catch(() => null);
  const detalle = cuerpo?.detail;
  if (detalle && typeof detalle === "object" && !Array.isArray(detalle)) {
    return new ErrorRenovacionAutomatica(
      typeof detalle.mensaje === "string" ? detalle.mensaje : mensaje,
      typeof detalle.codigo === "string" ? detalle.codigo : "ERROR",
      respuesta.status,
    );
  }
  if (Array.isArray(detalle)) {
    return new ErrorRenovacionAutomatica(
      "Revisa los datos de la tarjeta.",
      "DATOS_INVALIDOS",
      respuesta.status,
    );
  }
  return new ErrorRenovacionAutomatica(mensaje, "ERROR", respuesta.status);
}

function ruta(polizaId: string): string {
  return `${API_URL}/api/v1/polizas/${encodeURIComponent(polizaId)}/renovacion-automatica`;
}

export async function consultarRenovacionAutomatica(
  polizaId: string,
): Promise<RenovacionAutomatica> {
  const respuesta = await fetchAutenticado(ruta(polizaId));
  if (!respuesta.ok) {
    throw await error(respuesta, "No fue posible consultar la renovación automática.");
  }
  return respuesta.json();
}

export async function configurarRenovacionAutomatica(
  polizaId: string,
  solicitud: SolicitudRenovacionAutomatica,
): Promise<RenovacionAutomatica> {
  const respuesta = await fetchAutenticado(ruta(polizaId), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(solicitud),
  });
  if (!respuesta.ok) {
    throw await error(respuesta, "No fue posible guardar la renovación automática.");
  }
  return respuesta.json();
}

/** Descarga el documento contractual del periodo renovado automáticamente. */
export async function descargarDocumentoRenovacion(
  polizaId: string,
  renovacionId: string,
): Promise<void> {
  const respuesta = await fetchAutenticado(
    `${ruta(polizaId)}/${encodeURIComponent(renovacionId)}/documento`,
  );
  if (!respuesta.ok) {
    throw await error(respuesta, "No fue posible descargar el documento de la renovación.");
  }
  const cabecera = respuesta.headers.get("Content-Disposition") ?? "";
  const nombre = /filename="([^"]+)"/.exec(cabecera)?.[1] ?? `renovacion-${polizaId}.pdf`;
  const url = URL.createObjectURL(await respuesta.blob());
  try {
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = nombre;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

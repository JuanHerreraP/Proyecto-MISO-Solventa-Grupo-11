import { fetchAutenticado } from "./session";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface PagoResumen {
  pago_id: string;
  cotizacion_id: string;
  metodo: "TARJETA" | "PSE";
  monto: string;
  moneda: string;
  estado: "PENDIENTE" | "APROBADO" | "RECHAZADO";
  motivo_rechazo: string | null;
  creado_en: string;
}

export interface SolicitudPago {
  cotizacion_id: string;
  metodo: "TARJETA" | "PSE";
  token_tarjeta?: string;
  codigo_banco?: string;
  url_retorno?: string;
}

/** Resultado del recaudo: incluye la URL de redirección de PSE cuando aplica. */
export interface Pago extends PagoResumen {
  referencia_pasarela: string | null;
  url_redireccion: string | null;
  actualizado_en: string;
}

async function mensajeError(response: Response, porDefecto: string): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (body.detail?.mensaje) return body.detail.mensaje;
    return porDefecto;
  } catch {
    return porDefecto;
  }
}

export async function listarPagos(): Promise<PagoResumen[]> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/pagos`);
  if (!response.ok) throw new Error("No fue posible consultar tus pagos.");
  return response.json();
}

/** Consulta el estado de un pago (p. ej. al volver del portal PSE). */
export async function obtenerPago(pagoId: string): Promise<Pago> {
  const response = await fetchAutenticado(
    `${API_URL}/api/v1/pagos/${encodeURIComponent(pagoId)}`,
  );
  if (!response.ok) throw new Error("No fue posible consultar tu pago.");
  return response.json();
}

/**
 * Procesa el recaudo inicial de una cotización (HU13).
 * La Idempotency-Key evita cobrar dos veces si el cliente o la red reintentan.
 */
export async function crearPago(
  solicitud: SolicitudPago,
  idempotencyKey: string,
): Promise<Pago> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/pagos`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify(solicitud),
  });
  if (!response.ok) {
    throw new Error(await mensajeError(response, "No fue posible procesar el pago."));
  }
  return response.json();
}

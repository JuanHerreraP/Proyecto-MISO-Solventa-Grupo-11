import { fetchAutenticado } from "./session";

import { t } from "../i18n";

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
  /** Si el pago fue una compra o la renovación de una póliza (HU21). */
  concepto: "COMPRA" | "RENOVACION";
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

/** Lo que el cliente debe pagar o firmar para mantener su cobertura (HU21). */
export interface PrimaPendiente {
  tipo: "RENOVACION" | "COTIZACION" | "FIRMA_PENDIENTE";
  accion: "PAGAR" | "FIRMAR";
  referencia_id: string;
  cotizacion_id: string;
  poliza_id: string | null;
  numero_poliza: string | null;
  ramo: string;
  nombre_ramo: string;
  monto: string;
  moneda: string;
  fecha_limite: string | null;
  mensaje: string | null;
}

/** Comprobante de un pago aprobado (HU21). */
export interface Comprobante {
  comprobante_id: string;
  numero: string;
  pago_id: string;
  cotizacion_id: string;
  concepto: "COMPRA" | "RENOVACION";
  descripcion: string;
  poliza_id: string | null;
  numero_poliza: string | null;
  nombre_ramo: string;
  monto: string;
  moneda: string;
  metodo: "TARJETA" | "PSE";
  referencia_pasarela: string | null;
  pagado_en: string;
  emitido_en: string;
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
  if (!response.ok) throw new Error(t("pagosService.no_fue_posible_consultar_tus"));
  return response.json();
}

/** Primas pendientes del cliente: renovaciones, cotizaciones sin pagar y contratos por firmar. */
export async function listarPrimasPendientes(): Promise<PrimaPendiente[]> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/primas-pendientes`);
  if (!response.ok) throw new Error(t("pagosService.no_fue_posible_consultar_tus_2"));
  const cuerpo: { primas: PrimaPendiente[] } = await response.json();
  return cuerpo.primas;
}

/** Comprobante de un pago aprobado. */
export async function obtenerComprobante(pagoId: string): Promise<Comprobante> {
  const response = await fetchAutenticado(
    `${API_URL}/api/v1/pagos/${encodeURIComponent(pagoId)}/comprobante`,
  );
  if (!response.ok) throw new Error(t("pagosService.no_fue_posible_consultar_el"));
  return response.json();
}

/** Consulta el estado de un pago (p. ej. al volver del portal PSE). */
export async function obtenerPago(pagoId: string): Promise<Pago> {
  const response = await fetchAutenticado(
    `${API_URL}/api/v1/pagos/${encodeURIComponent(pagoId)}`,
  );
  if (!response.ok) throw new Error(t("pagosService.no_fue_posible_consultar_tu"));
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
    throw new Error(await mensajeError(response, t("pagosService.no_fue_posible_procesar_el")));
  }
  return response.json();
}

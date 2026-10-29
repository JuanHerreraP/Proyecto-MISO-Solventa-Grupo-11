import { fetchAutenticado } from "./session";
import type {
  Cotizacion,
  DefinicionRamo,
  SolicitudCotizacion,
} from "../types/cotizaciones";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

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

/** Ramos disponibles y los datos de riesgo que requiere cada uno. */
export async function obtenerRamos(): Promise<DefinicionRamo[]> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/cotizaciones/ramos`);
  if (!response.ok) throw new Error("No fue posible consultar los ramos disponibles.");
  return response.json();
}

/** Calcula y guarda una cotización. Devuelve la cotización vigente resultante. */
export async function crearCotizacion(
  solicitud: SolicitudCotizacion,
): Promise<Cotizacion> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/cotizaciones`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(solicitud),
  });
  if (!response.ok) {
    throw new Error(await mensajeError(response, "No fue posible crear la cotización."));
  }
  return response.json();
}

/** Lista las cotizaciones de un cliente, de la más reciente a la más antigua. */
export async function listarCotizaciones(clienteId: string): Promise<Cotizacion[]> {
  const response = await fetchAutenticado(
    `${API_URL}/api/v1/cotizaciones?cliente_id=${encodeURIComponent(clienteId)}`,
  );
  if (!response.ok) throw new Error("No fue posible consultar tus cotizaciones.");
  return response.json();
}

/** Consulta una cotización por su identificador. */
export async function obtenerCotizacion(cotizacionId: string): Promise<Cotizacion> {
  const response = await fetchAutenticado(
    `${API_URL}/api/v1/cotizaciones/${encodeURIComponent(cotizacionId)}`,
  );
  if (!response.ok) throw new Error("No fue posible consultar la cotización.");
  return response.json();
}

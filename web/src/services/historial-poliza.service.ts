import { fetchAutenticado } from "./session";
import type { HistorialPoliza } from "../types/historial";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** Traduce el error del backend a un mensaje legible, sin exponer detalles internos. */
async function mensajeError(response: Response): Promise<string> {
  const porCodigo: Record<string, string> = {
    POLIZA_NO_ENCONTRADA: "No encontramos la póliza.",
    ACCESS_DENIED: "No tienes acceso al historial de esta póliza.",
  };
  try {
    const body = await response.json();
    const codigo = body?.detail?.codigo;
    if (codigo && porCodigo[codigo]) return porCodigo[codigo];
    if (response.status === 401) return "Tu sesión expiró. Vuelve a iniciar sesión.";
  } catch {
    // Sin cuerpo legible: cae al mensaje genérico.
  }
  return "No fue posible consultar el historial de la póliza.";
}

/**
 * Consulta el historial consolidado de una póliza (HU25). El backend toma el cliente de la
 * sesión; el frontend nunca envía `cliente_id`.
 */
export async function obtenerHistorialPoliza(polizaId: string): Promise<HistorialPoliza> {
  const response = await fetchAutenticado(
    `${API_URL}/api/v1/polizas/${encodeURIComponent(polizaId)}/historial`,
  );
  if (!response.ok) {
    throw new Error(await mensajeError(response));
  }
  return response.json();
}

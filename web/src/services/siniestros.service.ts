import { fetchAutenticado } from "./session";
import type { Siniestro, SolicitudSiniestro } from "../types/siniestros";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** Traduce el error del backend a un mensaje legible, sin exponer detalles internos. */
async function mensajeError(response: Response): Promise<string> {
  const porCodigo: Record<string, string> = {
    POLIZA_NO_ENCONTRADA: "No encontramos la póliza seleccionada.",
    POLIZA_AJENA: "La póliza seleccionada no está asociada a tu cuenta.",
    POLIZA_NO_VIGENTE: "La póliza no está vigente; no es posible registrar el siniestro.",
    FECHA_FUTURA: "La fecha del evento no puede estar en el futuro.",
    FECHA_FUERA_DE_VIGENCIA: "La fecha del evento está fuera del periodo cubierto por la póliza.",
  };
  try {
    const body = await response.json();
    const codigo = body?.detail?.codigo;
    if (codigo && porCodigo[codigo]) return porCodigo[codigo];
    if (response.status === 422) return "Revisa los datos del evento e inténtalo de nuevo.";
    if (response.status === 401) return "Tu sesión expiró. Vuelve a iniciar sesión.";
  } catch {
    // Sin cuerpo legible: cae al mensaje genérico.
  }
  return "No fue posible registrar el siniestro. Inténtalo de nuevo.";
}

/** Registra manualmente un siniestro. El backend toma el cliente de la sesión. */
export async function crearSiniestro(solicitud: SolicitudSiniestro): Promise<Siniestro> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/siniestros`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(solicitud),
  });
  if (!response.ok) {
    throw new Error(await mensajeError(response));
  }
  return response.json();
}

/** Lista los siniestros del cliente, del más reciente al más antiguo. */
export async function listarSiniestros(): Promise<Siniestro[]> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/siniestros`);
  if (!response.ok) throw new Error("No fue posible consultar tus siniestros.");
  return response.json();
}

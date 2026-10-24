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

export async function listarPagos(): Promise<PagoResumen[]> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/pagos`);
  if (!response.ok) throw new Error("No fue posible consultar tus pagos.");
  return response.json();
}

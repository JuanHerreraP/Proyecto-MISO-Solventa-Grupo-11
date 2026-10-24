import { fetchAutenticado } from "./session";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface PolizaResumen {
  poliza_id: string;
  numero_poliza: string;
  nombre_ramo: string;
  estado: string;
  activa: boolean;
  fecha_fin: string;
  cobertura_principal: string;
}

export interface Billetera {
  polizas: PolizaResumen[];
  total_vigentes: number;
  total_inactivas: number;
}

export async function obtenerBilletera(): Promise<Billetera> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/billetera/polizas`);
  if (!response.ok) throw new Error("No fue posible consultar tus pólizas.");
  return response.json();
}

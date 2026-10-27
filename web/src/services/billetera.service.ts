import { fetchAutenticado } from "./session";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface PolizaResumen {
  poliza_id: string;
  numero_poliza: string;
  ramo: string;
  nombre_ramo: string;
  estado: string;
  activa: boolean;
  fecha_inicio: string;
  fecha_fin: string;
  cobertura_principal: string;
}

export interface Billetera {
  polizas: PolizaResumen[];
  total_vigentes: number;
  total_inactivas: number;
}

export interface Certificado {
  poliza_id: string;
  numero_poliza: string;
  nombre_ramo: string;
  estado: string;
  activa: boolean;
  titular: string;
  documento_titular: string;
  fecha_inicio: string;
  fecha_fin: string;
  cobertura_principal: string;
  suma_asegurada: string;
  prima_total: string;
  moneda: string;
  emitida_en: string;
  contenido_qr: string;
}

export async function obtenerBilletera(): Promise<Billetera> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/billetera/polizas`);
  if (!response.ok) throw new Error("No fue posible consultar tus pólizas.");
  return response.json();
}

/** Certificado completo de una póliza (titular, suma asegurada, QR). */
export async function obtenerCertificado(polizaId: string): Promise<Certificado> {
  const response = await fetchAutenticado(
    `${API_URL}/api/v1/billetera/polizas/${encodeURIComponent(polizaId)}/certificado`,
  );
  if (!response.ok) throw new Error("No fue posible consultar el certificado.");
  return response.json();
}

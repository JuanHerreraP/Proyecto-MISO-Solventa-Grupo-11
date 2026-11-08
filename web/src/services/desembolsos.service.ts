import { fetchAutenticado } from "./session";
import type { EstadoSiniestro, OrigenSiniestro } from "../types/siniestros";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type TipoCuenta = "AHORROS" | "CORRIENTE";
export type MedioDesembolso = "CUENTA_BANCARIA" | "CODIGO_RETIRO";
export type EstadoDesembolso = "PENDIENTE" | "COMPLETADA" | "FALLIDA";

/** Bancos habilitados en la red de desembolsos (mismos códigos del backend). */
export const BANCOS: Record<string, string> = {
  "1007": "Bancolombia",
  "1001": "Banco de Bogotá",
  "1051": "Davivienda",
  "1013": "BBVA Colombia",
  "1023": "Banco de Occidente",
  "1052": "Banco AV Villas",
  "1507": "Nequi",
};

export interface CuentaDesembolso {
  codigo_banco: string;
  nombre_banco: string;
  tipo_cuenta: TipoCuenta;
  ultimos_digitos: string;
  actualizada_en: string;
}

export interface Desembolso {
  desembolso_id: string;
  siniestro_id: string;
  poliza_id: string;
  monto: string;
  moneda: string;
  medio: MedioDesembolso;
  destino: string | null;
  estado: EstadoDesembolso;
  intento: number;
  referencia_transaccion: string | null;
  /** Solo llega en las consultas del titular. */
  codigo_retiro: string | null;
  motivo_fallo: string | null;
  creado_en: string;
  completado_en: string | null;
}

export interface SiniestroBandeja {
  siniestro_id: string;
  poliza_id: string;
  cliente_id: string;
  origen: OrigenSiniestro;
  estado: EstadoSiniestro;
  fecha_evento: string;
  lugar: string;
  descripcion: string;
  estimacion_danos: string;
  moneda: string;
  registrado_en: string;
  monto_aprobado: string | null;
  evaluado_por: string | null;
  evaluado_en: string | null;
  motivo_rechazo: string | null;
  desembolso: Desembolso | null;
}

/** Error de negocio del backend, con su código para decidir qué mostrar. */
export class ErrorDesembolso extends Error {
  readonly codigo: string;
  readonly status: number;

  constructor(message: string, codigo: string, status: number) {
    super(message);
    this.codigo = codigo;
    this.status = status;
  }
}

async function procesar<T>(respuesta: Response, mensaje: string): Promise<T> {
  if (respuesta.ok) return respuesta.json();
  const cuerpo = await respuesta.json().catch(() => null);
  const detalle = cuerpo?.detail;
  if (detalle && typeof detalle === "object" && !Array.isArray(detalle)) {
    throw new ErrorDesembolso(
      typeof detalle.mensaje === "string" ? detalle.mensaje : mensaje,
      detalle.codigo ?? "ERROR",
      respuesta.status,
    );
  }
  if (Array.isArray(detalle)) {
    throw new ErrorDesembolso("Revisa los datos ingresados.", "DATOS_INVALIDOS", respuesta.status);
  }
  throw new ErrorDesembolso(mensaje, "ERROR", respuesta.status);
}

function enviar(url: string, metodo: "POST" | "PUT", cuerpo?: unknown): Promise<Response> {
  return fetchAutenticado(url, {
    method: metodo,
    headers: { "Content-Type": "application/json" },
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  });
}

// --- Cliente ---------------------------------------------------------------------------

export async function obtenerCuenta(): Promise<CuentaDesembolso | null> {
  return procesar(
    await fetchAutenticado(`${API_URL}/api/v1/desembolsos/cuenta`),
    "No fue posible consultar tu cuenta.",
  );
}

/** El número viaja una sola vez: el backend lo tokeniza y solo guarda los últimos dígitos. */
export async function registrarCuenta(datos: {
  codigo_banco: string;
  tipo_cuenta: TipoCuenta;
  numero_cuenta: string;
}): Promise<CuentaDesembolso> {
  return procesar(
    await enviar(`${API_URL}/api/v1/desembolsos/cuenta`, "PUT", datos),
    "No fue posible registrar la cuenta.",
  );
}

export async function listarDesembolsos(): Promise<Desembolso[]> {
  return procesar(
    await fetchAutenticado(`${API_URL}/api/v1/desembolsos`),
    "No fue posible consultar tus indemnizaciones.",
  );
}

// --- Operaciones/Siniestros ------------------------------------------------------------

const BANDEJA = `${API_URL}/api/v1/operaciones/siniestros`;

export async function obtenerBandeja(estado?: EstadoSiniestro): Promise<SiniestroBandeja[]> {
  const filtro = estado ? `?estado=${encodeURIComponent(estado)}` : "";
  return procesar(
    await fetchAutenticado(`${BANDEJA}${filtro}`),
    "No fue posible consultar la bandeja de siniestros.",
  );
}

export async function aprobarSiniestro(
  siniestroId: string, montoAprobado?: string,
): Promise<SiniestroBandeja> {
  const cuerpo = montoAprobado ? { monto_aprobado: montoAprobado } : {};
  return procesar(
    await enviar(`${BANDEJA}/${encodeURIComponent(siniestroId)}/aprobacion`, "POST", cuerpo),
    "No fue posible aprobar el siniestro.",
  );
}

export async function rechazarSiniestro(
  siniestroId: string, motivo: string,
): Promise<SiniestroBandeja> {
  return procesar(
    await enviar(`${BANDEJA}/${encodeURIComponent(siniestroId)}/rechazo`, "POST", { motivo }),
    "No fue posible rechazar el siniestro.",
  );
}

export async function reintentarDesembolso(siniestroId: string): Promise<Desembolso> {
  return procesar(
    await enviar(`${BANDEJA}/${encodeURIComponent(siniestroId)}/desembolso/reintento`, "POST"),
    "No fue posible reintentar el desembolso.",
  );
}

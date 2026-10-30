import { fetchAutenticado } from "./session";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type EstadoFirma = "PENDIENTE" | "FIRMADA" | "BLOQUEADA";
export type CanalOtp = "SMS" | "EMAIL";

export interface ContratoSeguro {
  version_plantilla: string;
  cotizacion_id: string;
  ramo: string;
  nombre_ramo: string;
  titular: {
    nombre_completo: string;
    tipo_documento: string;
    numero_documento: string;
    email: string;
    celular: string | null;
  };
  cobertura_principal: { codigo: string; nombre: string; suma_asegurada: string; descripcion: string | null };
  datos_riesgo: Record<string, unknown>;
  prima_total: string;
  moneda: string;
  pago_id: string;
  referencia_pago: string | null;
  fecha_pago: string;
  clausulas: string[];
}

export interface ProcesoFirma {
  firma_id: string;
  cotizacion_id: string;
  estado: EstadoFirma;
  contrato: ContratoSeguro;
  huella_documento: string;
  documento_integro: boolean;
  otp_canal: CanalOtp | null;
  otp_destino: string | null;
  otp_expira_en: string | null;
  reenvio_disponible_en: string | null;
  intentos_restantes: number;
  envios_restantes: number;
  firmado_en: string | null;
  ip_firmante: string | null;
  referencia_proveedor: string | null;
}

/** Error de negocio del backend, con el código para decidir qué mostrar. */
export class ErrorFirma extends Error {
  readonly codigo: string;
  readonly status: number;
  readonly intentosRestantes?: number;
  readonly reenvioDisponibleEn?: string | null;

  constructor(
    message: string,
    codigo: string,
    status: number,
    intentosRestantes?: number,
    reenvioDisponibleEn?: string | null,
  ) {
    super(message);
    this.codigo = codigo;
    this.status = status;
    this.intentosRestantes = intentosRestantes;
    this.reenvioDisponibleEn = reenvioDisponibleEn;
  }
}

async function procesar(respuesta: Response, mensaje: string): Promise<ProcesoFirma> {
  if (respuesta.ok) return respuesta.json();
  const cuerpo = await respuesta.json().catch(() => null);
  const detalle = cuerpo?.detail;
  if (detalle && typeof detalle === "object" && !Array.isArray(detalle)) {
    throw new ErrorFirma(
      detalle.mensaje ?? mensaje, detalle.codigo ?? "ERROR", respuesta.status,
      detalle.intentos_restantes, detalle.reenvio_disponible_en,
    );
  }
  throw new ErrorFirma(mensaje, "ERROR", respuesta.status);
}

function ruta(cotizacionId: string, sufijo = ""): string {
  return `${API_URL}/api/v1/firmas/${encodeURIComponent(cotizacionId)}${sufijo}`;
}

function post(url: string, cuerpo: unknown): Promise<Response> {
  return fetchAutenticado(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
}

export async function obtenerContrato(cotizacionId: string): Promise<ProcesoFirma> {
  return procesar(await fetchAutenticado(ruta(cotizacionId)), "No fue posible cargar el contrato.");
}

export async function solicitarCodigo(cotizacionId: string, canal: CanalOtp): Promise<ProcesoFirma> {
  return procesar(await post(ruta(cotizacionId, "/otp"), { canal }), "No fue posible enviar el código.");
}

export async function firmarContrato(
  cotizacionId: string, codigo: string, huellaDocumento: string,
): Promise<ProcesoFirma> {
  return procesar(
    await post(ruta(cotizacionId, "/firma"), { codigo, huella_documento: huellaDocumento }),
    "No fue posible firmar el contrato.",
  );
}

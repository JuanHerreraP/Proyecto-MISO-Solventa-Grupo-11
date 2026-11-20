import { fetchAutenticado } from "./session";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type MotivoCancelacion =
  | "YA_NO_LA_NECESITO"
  | "PRECIO_ALTO"
  | "OTRA_ASEGURADORA"
  | "COBERTURA_INSUFICIENTE"
  | "OTRO";

export type EstadoDevolucion = "PENDIENTE" | "SIN_SALDO";

export interface BloqueoCancelacion {
  codigo: "POLIZA_NO_VIGENTE" | "SINIESTRO_EN_TRAMITE";
  mensaje: string;
  siniestros: string[];
}

export interface MotivoCancelacionDisponible {
  codigo: MotivoCancelacion;
  etiqueta: string;
}

export interface Cancelacion {
  cancelacion_id: string;
  poliza_id: string;
  motivo: MotivoCancelacion;
  detalle: string | null;
  fecha_efecto: string;
  dias_totales: number;
  dias_no_transcurridos: number;
  prima_total: string;
  saldo_estimado: string;
  moneda: string;
  estado_devolucion: EstadoDevolucion;
  creado_en: string;
}

export interface CondicionesCancelacion {
  poliza_id: string;
  numero_poliza: string;
  cancelable: boolean;
  bloqueos: BloqueoCancelacion[];
  fecha_efecto: string;
  dias_totales: number;
  dias_no_transcurridos: number;
  prima_total: string;
  saldo_estimado: string;
  moneda: string;
  consecuencias: string[];
  motivos: MotivoCancelacionDisponible[];
  cancelacion: Cancelacion | null;
}

export interface SolicitudCancelacion {
  motivo: MotivoCancelacion;
  detalle?: string;
}

export class ErrorCancelacion extends Error {
  readonly codigo: string;
  readonly status: number;
  readonly bloqueos: BloqueoCancelacion[];

  constructor(
    message: string,
    codigo: string,
    status: number,
    bloqueos: BloqueoCancelacion[] = [],
  ) {
    super(message);
    this.codigo = codigo;
    this.status = status;
    this.bloqueos = bloqueos;
  }
}

async function procesar<T>(respuesta: Response, mensaje: string): Promise<T> {
  if (respuesta.ok) return respuesta.json();

  const cuerpo = await respuesta.json().catch(() => null);
  const detalle = cuerpo?.detail;
  if (detalle && typeof detalle === "object" && !Array.isArray(detalle)) {
    throw new ErrorCancelacion(
      typeof detalle.mensaje === "string" ? detalle.mensaje : mensaje,
      typeof detalle.codigo === "string" ? detalle.codigo : "ERROR",
      respuesta.status,
      Array.isArray(detalle.bloqueos) ? detalle.bloqueos : [],
    );
  }
  if (Array.isArray(detalle)) {
    throw new ErrorCancelacion("Revisa los datos ingresados.", "DATOS_INVALIDOS", respuesta.status);
  }
  throw new ErrorCancelacion(mensaje, "ERROR", respuesta.status);
}

function ruta(polizaId: string): string {
  return `${API_URL}/api/v1/polizas/${encodeURIComponent(polizaId)}/cancelacion`;
}

export async function consultarCancelacion(polizaId: string): Promise<CondicionesCancelacion> {
  return procesar(
    await fetchAutenticado(ruta(polizaId)),
    "No fue posible consultar las condiciones de cancelación.",
  );
}

export async function confirmarCancelacion(
  polizaId: string,
  solicitud: SolicitudCancelacion,
  claveIdempotencia: string,
): Promise<Cancelacion> {
  return procesar(
    await fetchAutenticado(ruta(polizaId), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": claveIdempotencia,
      },
      body: JSON.stringify({ ...solicitud, confirmo: true }),
    }),
    "No fue posible cancelar la póliza.",
  );
}

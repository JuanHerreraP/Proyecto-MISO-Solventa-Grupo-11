/** Tipos del historial consolidado de movimientos de una póliza (HU25). */

export type CategoriaMovimiento = "FINANCIERO" | "CONTRACTUAL" | "POLIZA";

export type TipoMovimiento =
  | "EMISION"
  | "PAGO_PRIMA_INICIAL"
  | "ENDOSO"
  | "RENOVACION"
  | "CANCELACION"
  | "DESEMBOLSO_INDEMNIZACION"
  | "REEMBOLSO";

export type NaturalezaMonto = "COBRO" | "REEMBOLSO" | "INDEMNIZACION" | "AJUSTE";

/** Linaje de un cambio contractual. `antes`/`despues` traen pares campo→valor. */
export interface CambioHistorial {
  tipo: string;
  descripcion: string;
  antes: Record<string, string> | null;
  despues: Record<string, string> | null;
}

/** Evidencia del consentimiento explícito del cliente (endosos). */
export interface ConsentimientoHistorial {
  explicito: boolean;
  tipo: string;
  usuario_id: string | null;
  rol: string | null;
  fecha: string | null;
  huella_solicitud: string | null;
}

/** Datos técnicos de un movimiento, solo visibles para el analista de cumplimiento (HU25 §19). */
export interface InformacionAuditoria {
  usuario_id: string | null;
  rol: string | null;
  ip_solicitante: string | null;
  user_agent: string | null;
  huella_solicitud: string | null;
  creado_en: string | null;
}

/** Desglose del ajuste de prima de un endoso en la vista de auditoría (HU25 §20). */
export interface AjustePrimaHistorial {
  /** Decimales serializados como texto desde el backend. */
  prima_anterior: string;
  ajuste: string;
  prima_nueva: string;
  moneda: string;
}

export interface MovimientoPoliza {
  movimiento_id: string;
  poliza_id: string;
  categoria: CategoriaMovimiento;
  tipo: TipoMovimiento;
  fecha: string;
  descripcion: string;
  referencia: string | null;
  referencia_externa: string | null;
  estado: string | null;
  /** Decimal serializado como texto desde el backend; puede ser null. */
  monto: string | null;
  moneda: string | null;
  naturaleza_monto: NaturalezaMonto | null;
  cambios: CambioHistorial[];
  consentimiento: ConsentimientoHistorial | null;
  /** Solo en la vista de auditoría; para el cliente llegan en null. */
  ajuste_prima?: AjustePrimaHistorial | null;
  auditoria?: InformacionAuditoria | null;
}

export interface HistorialPoliza {
  poliza_id: string;
  numero_poliza: string;
  /** Metadatos de contexto de la póliza. El backend siempre los envía; opcionales en el tipo
   *  para no obligar a los consumidores que solo usan los movimientos. */
  cliente_id?: string;
  nombre_ramo?: string;
  estado?: string;
  movimientos: MovimientoPoliza[];
}

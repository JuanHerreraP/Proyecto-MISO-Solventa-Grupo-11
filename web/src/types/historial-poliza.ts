/** Tipos de la consulta de historial contractual del auditor (HU25).
 *
 * Reutiliza el modelo neutral del historial (`historial.ts`) y añade el tipo del resolutor de
 * pólizas que el auditor usa para convertir un número de póliza en su `poliza_id`.
 */

export type {
  AjustePrimaHistorial,
  CambioHistorial,
  CategoriaMovimiento,
  ConsentimientoHistorial,
  HistorialPoliza,
  InformacionAuditoria,
  MovimientoPoliza,
  NaturalezaMonto,
  TipoMovimiento,
} from "./historial";

/** Respuesta del resolutor `GET /api/v1/auditoria/polizas/{identificador}` (HU25 §8). */
export interface PolizaResuelta {
  poliza_id: string;
  numero_poliza: string;
  cliente_id: string;
  nombre_ramo: string;
  estado: string;
}

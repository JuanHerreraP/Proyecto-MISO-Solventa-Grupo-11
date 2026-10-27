/** Tipos del registro manual de siniestros (HU20). */

export type EstadoSiniestro = "REGISTRADO" | "EN_EVALUACION" | "APROBADO" | "RECHAZADO";
export type OrigenSiniestro = "MANUAL" | "AUTOMATICO";

export interface SolicitudSiniestro {
  poliza_id: string;
  fecha_evento: string;
  hora_evento: string;
  lugar: string;
  descripcion: string;
  estimacion_danos: number;
}

export interface Siniestro {
  siniestro_id: string;
  cliente_id: string;
  poliza_id: string;
  origen: OrigenSiniestro;
  estado: EstadoSiniestro;
  fecha_evento: string;
  hora_evento: string;
  lugar: string;
  descripcion: string;
  estimacion_danos: string;
  moneda: string;
  registrado_por: string;
  registrado_en: string;
}

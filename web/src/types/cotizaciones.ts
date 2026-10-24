/** Tipos del catálogo de ramos y cotizaciones (HU03 / BPM-25). */

export type RamoSeguro = "VIAJE" | "PROTECCION_DISPOSITIVOS" | "VIDA" | "PARAMETRICO";

export type TipoCampo = "TEXTO" | "ENTERO" | "DECIMAL" | "FECHA" | "BOOLEANO" | "OPCION";

export interface CampoRiesgo {
  codigo: string;
  etiqueta: string;
  tipo: TipoCampo;
  requerido: boolean;
  descripcion: string;
  unidad: string | null;
  opciones: string[];
}

export interface DefinicionRamo {
  ramo: RamoSeguro;
  nombre: string;
  descripcion: string;
  campos: CampoRiesgo[];
}

export type EstadoCotizacion =
  | "BORRADOR"
  | "VIGENTE"
  | "ACEPTADA"
  | "EXPIRADA"
  | "CANCELADA";

export interface CoberturaPrincipal {
  codigo: string;
  nombre: string;
  suma_asegurada: string;
  descripcion: string | null;
}

export interface Cotizacion {
  cotizacion_id: string;
  cliente_id: string;
  ramo: RamoSeguro;
  datos_riesgo: Record<string, unknown>;
  estado: EstadoCotizacion;
  prima_total: string | null;
  moneda: string;
  cobertura_principal: CoberturaPrincipal | null;
  creada_en: string;
  vigente_hasta: string | null;
}

export interface SolicitudCotizacion {
  cliente_id: string;
  ramo: RamoSeguro;
  datos_riesgo: Record<string, unknown>;
}

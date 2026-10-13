export interface ContactoTecnico {
  nombre: string;
  correo: string;
  telefono?: string;
}

export type TipoSeguro =
  | "VIAJE"
  | "PROTECCION_DISPOSITIVOS"
  | "MICROSEGURO_VIDA"
  | "PARAMETRICO"
  | "PROTECCION_PAGOS";

export type EndpointSocio =
  | "cotizaciones:crear"
  | "polizas:emitir";

export interface SolicitudRegistroSocio {
  nit: string;
  razon_social: string;
  contactos_tecnicos: ContactoTecnico[];
  pais_operacion: string;
  tipos_seguros_autorizados: TipoSeguro[];
  endpoints_autorizados: EndpointSocio[];
}

export interface RespuestaRegistroSocio
  extends SolicitudRegistroSocio {
  socio_id: string;
  tenant_id: string;
  estado: "PENDIENTE" | "ACTIVO" | "INACTIVO";
  creado_en: string;
  actualizado_en: string;
}

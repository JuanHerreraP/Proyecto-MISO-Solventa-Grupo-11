import { fetchAutenticado } from "./session";
import type { Billetera } from "./billetera.service";
import type { Siniestro, SolicitudSiniestro } from "../types/siniestros";

import { t } from "../i18n";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** Cliente atendido por un asesor de ventas (HU20). */
export interface ClienteDeAsesor {
  cliente_id: string;
  nombre: string;
  apellido: string;
  email: string;
}

/** Datos para que un manager cree un asesor de ventas (POST /api/v1/auth/users). */
export interface SolicitudCrearAsesor {
  nombre: string;
  apellido: string;
  email: string;
  password: string;
  tipo_documento: string;
  numero_documento: string;
  fecha_nacimiento: string;
}

/** Respuesta del alta de un usuario administrativo. */
export interface AsesorCreado {
  id: string;
  nombre: string;
  apellido: string;
  email: string;
  rol: string;
  kyc_validado: boolean;
  fecha_creacion: string;
}

/** Crea un asesor de ventas. Solo un manager (SERVICIO_INTERNO) puede hacerlo. */
export async function crearAsesorVentas(solicitud: SolicitudCrearAsesor): Promise<AsesorCreado> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/auth/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...solicitud,
      acepta_validacion_identidad: true,
      rol: "ASESOR_VENTAS",
    }),
  });
  if (!response.ok) {
    throw new Error(await mensajeErrorCrearAsesor(response));
  }
  return response.json();
}

async function mensajeErrorCrearAsesor(response: Response): Promise<string> {
  const porCodigo: Record<string, string> = {
    EMAIL_ALREADY_EXISTS: t("asesorService.ya_existe_un_usuario_con"),
    DOCUMENT_ALREADY_EXISTS: t("asesorService.ya_existe_una_cuenta_con"),
    KYC_REJECTED: t("asesorService.la_validacion_de_identidad_no"),
    KYC_PENDING: t("asesorService.la_validacion_de_identidad_quedo"),
    KYC_PROVIDER_UNAVAILABLE: t("asesorService.el_servicio_de_validacion_de"),
  };
  try {
    const body = await response.json();
    const codigo = body?.detail?.codigo;
    if (codigo && porCodigo[codigo]) return porCodigo[codigo];
    if (body?.detail?.mensaje) return body.detail.mensaje;
    if (response.status === 403) return t("asesorService.no_tienes_permisos_para_crear");
    if (response.status === 422) return t("asesorService.revisa_los_datos_del_asesor");
  } catch {
    // Sin cuerpo legible: cae al genérico.
  }
  return t("asesorService.no_fue_posible_crear_el");
}

/** Registro de siniestro asistido: el asesor indica a qué cliente pertenece. */
export interface SolicitudSiniestroAsesor extends SolicitudSiniestro {
  cliente_id: string;
}

/** Lista los clientes asociados al asesor autenticado. */
export async function listarClientesDeAsesor(): Promise<ClienteDeAsesor[]> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/asesor/clientes`);
  if (!response.ok) throw new Error(t("asesorService.no_fue_posible_consultar_tus"));
  return response.json();
}

/** Asocia un cliente (por correo) al asesor autenticado. */
export async function asociarCliente(email: string): Promise<ClienteDeAsesor> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/asesor/clientes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) {
    throw new Error(await mensajeErrorAsociacion(response));
  }
  return response.json();
}

/** Pólizas de un cliente asociado, para elegir la afectada al registrar un siniestro. */
export async function obtenerPolizasDeCliente(clienteId: string): Promise<Billetera> {
  const response = await fetchAutenticado(
    `${API_URL}/api/v1/asesor/clientes/${encodeURIComponent(clienteId)}/polizas`,
  );
  if (!response.ok) throw new Error(t("asesorService.no_fue_posible_consultar_las"));
  return response.json();
}

/** Registra un siniestro en nombre de un cliente asociado. */
export async function crearSiniestroAsistido(
  solicitud: SolicitudSiniestroAsesor,
): Promise<Siniestro> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/siniestros/asistido`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(solicitud),
  });
  if (!response.ok) {
    throw new Error(await mensajeErrorSiniestro(response));
  }
  return response.json();
}

async function mensajeErrorAsociacion(response: Response): Promise<string> {
  const porCodigo: Record<string, string> = {
    CLIENTE_NO_ENCONTRADO: t("asesorService.no_existe_un_cliente_con"),
    CLIENTE_YA_ASOCIADO: t("asesorService.ese_cliente_ya_esta_asociado"),
  };
  try {
    const body = await response.json();
    const codigo = body?.detail?.codigo;
    if (codigo && porCodigo[codigo]) return porCodigo[codigo];
  } catch {
    // Sin cuerpo legible: cae al genérico.
  }
  return t("asesorService.no_fue_posible_asociar_al");
}

async function mensajeErrorSiniestro(response: Response): Promise<string> {
  const porCodigo: Record<string, string> = {
    CLIENTE_NO_ASOCIADO: t("asesorService.el_cliente_no_esta_asociado"),
    POLIZA_NO_ENCONTRADA: t("asesorService.no_encontramos_la_poliza_seleccionada"),
    POLIZA_AJENA: t("asesorService.la_poliza_no_pertenece_al"),
    POLIZA_NO_VIGENTE: t("asesorService.la_poliza_no_esta_vigente"),
    FECHA_FUTURA: t("asesorService.la_fecha_del_evento_no"),
    FECHA_FUERA_DE_VIGENCIA: t("asesorService.la_fecha_del_evento_esta"),
  };
  try {
    const body = await response.json();
    const codigo = body?.detail?.codigo;
    if (codigo && porCodigo[codigo]) return porCodigo[codigo];
    if (response.status === 422) return t("asesorService.revisa_los_datos_del_evento");
    if (response.status === 401) return t("asesorService.tu_sesion_expiro_vuelve_a");
  } catch {
    // Sin cuerpo legible: cae al genérico.
  }
  return t("asesorService.no_fue_posible_registrar_el");
}

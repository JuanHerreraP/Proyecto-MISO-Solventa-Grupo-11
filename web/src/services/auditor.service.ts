import { fetchAutenticado } from "./session";

import { t } from "../i18n";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** Datos para que un manager cree un analista de cumplimiento (POST /api/v1/auth/users). */
export interface SolicitudCrearAnalista {
  nombre: string;
  apellido: string;
  email: string;
  password: string;
  tipo_documento: string;
  numero_documento: string;
  fecha_nacimiento: string;
}

/** Respuesta del alta de un usuario administrativo. */
export interface AnalistaCreado {
  id: string;
  nombre: string;
  apellido: string;
  email: string;
  rol: string;
  kyc_validado: boolean;
  fecha_creacion: string;
}

/** Crea un analista de cumplimiento. Solo un manager (SERVICIO_INTERNO) puede hacerlo. */
export async function crearAnalistaCumplimiento(
  solicitud: SolicitudCrearAnalista,
): Promise<AnalistaCreado> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/auth/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...solicitud,
      acepta_validacion_identidad: true,
      rol: "ANALISTA_CUMPLIMIENTO",
    }),
  });
  if (!response.ok) {
    throw new Error(await mensajeErrorCrearAnalista(response));
  }
  return response.json();
}

async function mensajeErrorCrearAnalista(response: Response): Promise<string> {
  const porCodigo: Record<string, string> = {
    EMAIL_ALREADY_EXISTS: t("auditorService.ya_existe_un_usuario_con"),
    DOCUMENT_ALREADY_EXISTS: t("auditorService.ya_existe_una_cuenta_con"),
    KYC_REJECTED: t("auditorService.la_validacion_de_identidad_no"),
    KYC_PENDING: t("auditorService.la_validacion_de_identidad_quedo"),
    KYC_PROVIDER_UNAVAILABLE: t("auditorService.el_servicio_de_validacion_de"),
  };
  try {
    const body = await response.json();
    const codigo = body?.detail?.codigo;
    if (codigo && porCodigo[codigo]) return porCodigo[codigo];
    if (body?.detail?.mensaje) return body.detail.mensaje;
    if (response.status === 403) return t("auditorService.no_tienes_permisos_para_crear");
    if (response.status === 422) return t("auditorService.revisa_los_datos_del_analista");
  } catch {
    // Sin cuerpo legible: cae al genérico.
  }
  return t("auditorService.no_fue_posible_crear_el");
}

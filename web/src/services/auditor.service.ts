import { fetchAutenticado } from "./session";

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
    EMAIL_ALREADY_EXISTS: "Ya existe un usuario con ese correo.",
    DOCUMENT_ALREADY_EXISTS: "Ya existe una cuenta con ese tipo y número de documento.",
    KYC_REJECTED: "La validación de identidad no fue aprobada.",
    KYC_PENDING: "La validación de identidad quedó pendiente de revisión.",
    KYC_PROVIDER_UNAVAILABLE: "El servicio de validación de identidad no está disponible.",
  };
  try {
    const body = await response.json();
    const codigo = body?.detail?.codigo;
    if (codigo && porCodigo[codigo]) return porCodigo[codigo];
    if (body?.detail?.mensaje) return body.detail.mensaje;
    if (response.status === 403) return "No tienes permisos para crear analistas de cumplimiento.";
    if (response.status === 422) return "Revisa los datos del analista e inténtalo de nuevo.";
  } catch {
    // Sin cuerpo legible: cae al genérico.
  }
  return "No fue posible crear el analista de cumplimiento. Inténtalo de nuevo.";
}

import { fetchAutenticado } from "./session";
import type { Billetera } from "./billetera.service";
import type { Siniestro, SolicitudSiniestro } from "../types/siniestros";

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
    if (response.status === 403) return "No tienes permisos para crear asesores.";
    if (response.status === 422) return "Revisa los datos del asesor e inténtalo de nuevo.";
  } catch {
    // Sin cuerpo legible: cae al genérico.
  }
  return "No fue posible crear el asesor. Inténtalo de nuevo.";
}

/** Registro de siniestro asistido: el asesor indica a qué cliente pertenece. */
export interface SolicitudSiniestroAsesor extends SolicitudSiniestro {
  cliente_id: string;
}

/** Lista los clientes asociados al asesor autenticado. */
export async function listarClientesDeAsesor(): Promise<ClienteDeAsesor[]> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/asesor/clientes`);
  if (!response.ok) throw new Error("No fue posible consultar tus clientes.");
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
  if (!response.ok) throw new Error("No fue posible consultar las pólizas del cliente.");
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
    CLIENTE_NO_ENCONTRADO: "No existe un cliente con ese correo.",
    CLIENTE_YA_ASOCIADO: "Ese cliente ya está asociado a tu cuenta.",
  };
  try {
    const body = await response.json();
    const codigo = body?.detail?.codigo;
    if (codigo && porCodigo[codigo]) return porCodigo[codigo];
  } catch {
    // Sin cuerpo legible: cae al genérico.
  }
  return "No fue posible asociar al cliente. Inténtalo de nuevo.";
}

async function mensajeErrorSiniestro(response: Response): Promise<string> {
  const porCodigo: Record<string, string> = {
    CLIENTE_NO_ASOCIADO: "El cliente no está asociado a tu cuenta.",
    POLIZA_NO_ENCONTRADA: "No encontramos la póliza seleccionada.",
    POLIZA_AJENA: "La póliza no pertenece al cliente seleccionado.",
    POLIZA_NO_VIGENTE: "La póliza no está vigente; no es posible registrar el siniestro.",
    FECHA_FUTURA: "La fecha del evento no puede estar en el futuro.",
    FECHA_FUERA_DE_VIGENCIA: "La fecha del evento está fuera del periodo cubierto por la póliza.",
  };
  try {
    const body = await response.json();
    const codigo = body?.detail?.codigo;
    if (codigo && porCodigo[codigo]) return porCodigo[codigo];
    if (response.status === 422) return "Revisa los datos del evento e inténtalo de nuevo.";
    if (response.status === 401) return "Tu sesión expiró. Vuelve a iniciar sesión.";
  } catch {
    // Sin cuerpo legible: cae al genérico.
  }
  return "No fue posible registrar el siniestro. Inténtalo de nuevo.";
}

import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
} from "../types/auth";

const API_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function obtenerMensajeError(response: Response): Promise<string> {
  try {
    const body = await response.json();

    if (typeof body.detail === "string") {
      return body.detail;
    }

    if (body.detail?.mensaje) {
      return body.detail.mensaje;
    }

    return "Ocurrió un error al procesar la solicitud.";
  } catch {
    return "No fue posible comunicarse correctamente con el servidor.";
  }
}

export async function login(
  data: LoginRequest,
): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(await obtenerMensajeError(response));
  }

  return response.json();
}

export async function register(
  data: RegisterRequest,
): Promise<RegisterResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(await obtenerMensajeError(response));
  }

  return response.json();
}

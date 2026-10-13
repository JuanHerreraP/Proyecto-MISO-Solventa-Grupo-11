import type {
  RespuestaRegistroSocio,
  SolicitudRegistroSocio,
} from "../types/socios";

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

    return "No fue posible registrar el socio.";
  } catch {
    return "No fue posible comunicarse correctamente con el servidor.";
  }
}

export async function registrarSocio(
  solicitud: SolicitudRegistroSocio,
): Promise<RespuestaRegistroSocio> {
  const accessToken = localStorage.getItem("access_token");

  if (!accessToken) {
    throw new Error(
      "Debes iniciar sesión con un usuario autorizado para registrar socios.",
    );
  }

  const response = await fetch(`${API_URL}/api/v1/socios`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(solicitud),
  });

  if (!response.ok) {
    throw new Error(await obtenerMensajeError(response));
  }

  return response.json();
}

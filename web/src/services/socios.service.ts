import type {
  CredencialesSocioEmitidas,
  RespuestaRegistroSocio,
  SolicitudRegistroSocio,
} from "../types/socios";

const API_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function obtenerMensajeError(
  response: Response,
  mensajePredeterminado = "No fue posible registrar el socio.",
): Promise<string> {
  try {
    const body = await response.json();

    if (typeof body.detail === "string") {
      return body.detail;
    }

    if (body.detail?.mensaje) {
      return body.detail.mensaje;
    }

    return mensajePredeterminado;
  } catch {
    return "No fue posible comunicarse correctamente con el servidor.";
  }
}

function obtenerAccessToken(): string {
  const accessToken = localStorage.getItem("access_token");

  if (!accessToken) {
    throw new Error(
      "Debes iniciar sesión con un usuario autorizado para registrar socios.",
    );
  }

  return accessToken;
}

export async function registrarSocio(
  solicitud: SolicitudRegistroSocio,
): Promise<RespuestaRegistroSocio> {
  const accessToken = obtenerAccessToken();

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

export async function generarCredencialesSocio(
  socioId: string,
): Promise<CredencialesSocioEmitidas> {
  const accessToken = obtenerAccessToken();
  const response = await fetch(
    `${API_URL}/api/v1/socios/${encodeURIComponent(socioId)}/credenciales`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  );

  if (!response.ok) {
    throw new Error(
      await obtenerMensajeError(
        response,
        "El socio fue registrado, pero no fue posible generar sus credenciales.",
      ),
    );
  }

  return response.json();
}

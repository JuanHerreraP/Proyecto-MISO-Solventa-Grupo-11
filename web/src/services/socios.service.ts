import type {
  CredencialesSocioEmitidas,
  RespuestaRegistroSocio,
  SolicitudRegistroSocio,
} from "../types/socios";
import { fetchAutenticado, obtenerAccessToken as tokenDeSesion } from "./session";

import { t } from "../i18n";

const API_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function obtenerMensajeError(
  response: Response,
  mensajePredeterminado = t("sociosService.no_fue_posible_registrar_el"),
): Promise<string> {
  try {
    const body = await response.json();

    if (typeof body.detail === "string") {
      return body.detail;
    }

    if (body.detail?.mensaje) {
      return body.detail.mensaje;
    }

    if (Array.isArray(body.detail)) {
      const campos: Record<string, string> = {
        nit: "NIT", razon_social: t("sociosService.razon_social"), contactos_tecnicos: t("sociosService.contacto_tecnico"),
        nombre: t("sociosService.nombre"), correo: t("sociosService.correo"), telefono: t("sociosService.telefono"),
        pais_operacion: t("sociosService.pais"), tipos_seguros_autorizados: t("sociosService.tipos_de_seguro"),
        endpoints_autorizados: t("sociosService.permisos_de_api"),
      };
      return body.detail.map((error: { loc?: (string | number)[]; msg?: string }) => {
        const campo = (error.loc ?? []).filter((parte) => parte !== "body")
          .map((parte) => typeof parte === "number" ? `${parte + 1}` : (campos[parte] ?? parte))
          .join(" / ");
        return `${campo || t("sociosService.datos_del_socio")}: ${error.msg ?? t("sociosService.valor_invalido")}`;
      }).join("; ");
    }

    return mensajePredeterminado;
  } catch {
    return t("sociosService.no_fue_posible_comunicarse_correctamente");
  }
}

function obtenerAccessToken(): string {
  const accessToken = tokenDeSesion();

  if (!accessToken) {
    throw new Error(
      t("sociosService.debes_iniciar_sesion_con_un"),
    );
  }

  return accessToken;
}

export async function registrarSocio(
  solicitud: SolicitudRegistroSocio,
): Promise<RespuestaRegistroSocio> {
  const accessToken = obtenerAccessToken();

  const response = await fetchAutenticado(`${API_URL}/api/v1/socios`, {
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
  const response = await fetchAutenticado(
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
        t("sociosService.el_socio_fue_registrado_pero"),
      ),
    );
  }

  return response.json();
}

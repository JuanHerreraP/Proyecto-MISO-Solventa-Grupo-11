import { fetchAutenticado } from "./session";
import type { Siniestro, SolicitudSiniestro } from "../types/siniestros";

import { t } from "../i18n";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** Traduce el error del backend a un mensaje legible, sin exponer detalles internos. */
async function mensajeError(response: Response): Promise<string> {
  const porCodigo: Record<string, string> = {
    POLIZA_NO_ENCONTRADA: t("siniestrosService.no_encontramos_la_poliza_seleccionada"),
    POLIZA_AJENA: t("siniestrosService.la_poliza_seleccionada_no_esta"),
    POLIZA_NO_VIGENTE: t("siniestrosService.la_poliza_no_esta_vigente"),
    FECHA_FUTURA: t("siniestrosService.la_fecha_del_evento_no"),
    FECHA_FUERA_DE_VIGENCIA: t("siniestrosService.la_fecha_del_evento_esta"),
  };
  try {
    const body = await response.json();
    const codigo = body?.detail?.codigo;
    if (codigo && porCodigo[codigo]) return porCodigo[codigo];
    if (response.status === 422) return t("siniestrosService.revisa_los_datos_del_evento");
    if (response.status === 401) return t("siniestrosService.tu_sesion_expiro_vuelve_a");
  } catch {
    // Sin cuerpo legible: cae al mensaje genérico.
  }
  return t("siniestrosService.no_fue_posible_registrar_el");
}

/** Registra manualmente un siniestro. El backend toma el cliente de la sesión. */
export async function crearSiniestro(solicitud: SolicitudSiniestro): Promise<Siniestro> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/siniestros`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(solicitud),
  });
  if (!response.ok) {
    throw new Error(await mensajeError(response));
  }
  return response.json();
}

/** Lista los siniestros del cliente, del más reciente al más antiguo. */
export async function listarSiniestros(): Promise<Siniestro[]> {
  const response = await fetchAutenticado(`${API_URL}/api/v1/siniestros`);
  if (!response.ok) throw new Error(t("siniestrosService.no_fue_posible_consultar_tus"));
  return response.json();
}

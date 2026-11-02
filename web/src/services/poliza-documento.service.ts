import { fetchAutenticado } from "./session";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function nombreDeArchivo(respuesta: Response, polizaId: string): string {
  const cabecera = respuesta.headers.get("Content-Disposition") ?? "";
  return /filename="([^"]+)"/.exec(cabecera)?.[1] ?? `poliza-${polizaId}.pdf`;
}

/**
 * Descarga el PDF de la póliza con la sesión del cliente. El archivo se pide con el token de
 * acceso, por eso no puede abrirse como un enlace directo.
 */
export async function descargarDocumentoPoliza(polizaId: string): Promise<void> {
  const respuesta = await fetchAutenticado(
    `${API_URL}/api/v1/polizas/${encodeURIComponent(polizaId)}/documento`,
  );
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null);
    const detalle = cuerpo?.detail;
    const mensaje =
      detalle && typeof detalle === "object" && typeof detalle.mensaje === "string"
        ? detalle.mensaje
        : "No fue posible descargar la póliza.";
    throw new Error(mensaje);
  }

  const url = URL.createObjectURL(await respuesta.blob());
  try {
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = nombreDeArchivo(respuesta, polizaId);
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

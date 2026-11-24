import { t } from "../i18n";
/**
 * La condición paramétrica de una póliza llega en `descripcion_cobertura` como pares
 * `clave=valor` separados por `;`, por ejemplo:
 *
 *   "tipo_evento=RETRASO_VUELO; numero_vuelo=AV123; ubicacion=BOG; umbral_disparo=180; unidad=MINUTOS"
 *
 * Este módulo la convierte en filas legibles (etiqueta + valor) para mostrarlas en el detalle de
 * la póliza, igual que el certificado en la app móvil. Solo se incluyen los campos con valor.
 */

export interface CampoParametrico {
  etiqueta: string;
  valor: string;
  esMoneda: boolean;
}

// `tipo_evento` no se muestra: ya se refleja en el nombre de la cobertura.
// La etiqueta se traduce al construir las filas, para respetar el idioma activo.
const ETIQUETAS: Array<[string, () => string]> = [
  ["numero_vuelo", () => t("condicionParametrica.numero_de_vuelo")],
  ["ubicacion", () => t("condicionParametrica.ubicacion")],
  ["parametro", () => t("condicionParametrica.parametro")],
  ["umbral_disparo", () => t("condicionParametrica.umbral_de_activacion")],
  ["unidad", () => t("condicionParametrica.unidad")],
  ["valor_asegurado", () => t("condicionParametrica.valor_asegurado")],
];

const MONEDA = new Set(["valor_asegurado"]);

const VALORES: Record<string, string> = {
  get RETRASO_VUELO() { return t("condicionParametrica.retraso_de_vuelo"); },
  get EVENTO_CLIMATICO() { return t("condicionParametrica.evento_climatico"); },
  get PRECIPITACION() { return t("condicionParametrica.precipitacion"); },
  get MINUTOS() { return t("condicionParametrica.minutos"); },
  MM: "mm",
};

/** Pares crudos `clave=valor`. Tolera espacios, vacíos y claves repetidas (gana la última). */
function parsear(descripcion: string | null | undefined): Map<string, string> {
  const resultado = new Map<string, string>();
  if (!descripcion) return resultado;
  for (const parte of descripcion.split(";")) {
    const idx = parte.indexOf("=");
    if (idx <= 0) continue;
    const clave = parte.slice(0, idx).trim().toLowerCase();
    const valor = parte.slice(idx + 1).trim();
    if (clave && valor) resultado.set(clave, valor);
  }
  return resultado;
}

function humanizarValor(valor: string): string {
  return VALORES[valor] ?? valor;
}

function humanizarClave(clave: string): string {
  const texto = clave.replaceAll("_", " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/**
 * Filas legibles de la condición, en un orden estable. Los campos conocidos van primero con su
 * etiqueta amigable; cualquier campo extra con valor se agrega al final con su clave formateada.
 */
export function camposCondicionParametrica(
  descripcion: string | null | undefined,
): CampoParametrico[] {
  const crudos = parsear(descripcion);
  crudos.delete("tipo_evento");
  const filas: CampoParametrico[] = [];
  for (const [clave, etiqueta] of ETIQUETAS) {
    const valor = crudos.get(clave);
    if (valor === undefined) continue;
    crudos.delete(clave);
    filas.push({ etiqueta: etiqueta(), valor: humanizarValor(valor), esMoneda: MONEDA.has(clave) });
  }
  for (const [clave, valor] of crudos) {
    filas.push({ etiqueta: humanizarClave(clave), valor: humanizarValor(valor), esMoneda: false });
  }
  return filas;
}

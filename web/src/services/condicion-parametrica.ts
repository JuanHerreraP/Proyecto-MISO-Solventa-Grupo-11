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
const ETIQUETAS: Array<[string, string]> = [
  ["numero_vuelo", "Número de vuelo"],
  ["ubicacion", "Ubicación"],
  ["parametro", "Parámetro"],
  ["umbral_disparo", "Umbral de activación"],
  ["unidad", "Unidad"],
  ["valor_asegurado", "Valor asegurado"],
];

const MONEDA = new Set(["valor_asegurado"]);

const VALORES: Record<string, string> = {
  RETRASO_VUELO: "Retraso de vuelo",
  EVENTO_CLIMATICO: "Evento climático",
  PRECIPITACION: "Precipitación",
  MINUTOS: "minutos",
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
    filas.push({ etiqueta, valor: humanizarValor(valor), esMoneda: MONEDA.has(clave) });
  }
  for (const [clave, valor] of crudos) {
    filas.push({ etiqueta: humanizarClave(clave), valor: humanizarValor(valor), esMoneda: false });
  }
  return filas;
}

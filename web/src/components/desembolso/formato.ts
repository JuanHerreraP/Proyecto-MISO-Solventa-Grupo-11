export const ESTADOS_DESEMBOLSO: Record<string, string> = {
  PENDIENTE: "Pendiente",
  COMPLETADA: "Completada",
  FALLIDA: "Fallida",
};

export function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString("es-CO", {
    style: "currency", currency: moneda, maximumFractionDigits: 0,
  });
}

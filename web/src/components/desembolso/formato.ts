import { t, localeActual } from "../../i18n";
export const ESTADOS_DESEMBOLSO: Record<string, string> = {
  get PENDIENTE() { return t("formato.pendiente"); },
  get COMPLETADA() { return t("formato.completada"); },
  get FALLIDA() { return t("formato.fallida"); },
};

export function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString(localeActual(), {
    style: "currency", currency: moneda, maximumFractionDigits: 0,
  });
}

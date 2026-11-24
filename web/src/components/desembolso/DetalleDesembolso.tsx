import type { Desembolso } from "../../services/desembolsos.service";
import { ESTADOS_DESEMBOLSO, formatearMonto } from "./formato";
import "../../styles/desembolsos.css";

import { t } from "../../i18n";

const MOTIVOS: Record<string, string> = {
  get RED_NO_DISPONIBLE() { return t("detalleDesembolso.la_red_de_pagos_no"); },
  get CUENTA_INEXISTENTE() { return t("detalleDesembolso.el_banco_rechazo_la_cuenta"); },
};

type Props = { desembolso: Desembolso };

/** Estado de la indemnización: medio, destino, transacción y, al titular, su código de retiro. */
export default function DetalleDesembolso({ desembolso }: Props) {
  const porCodigo = desembolso.medio === "CODIGO_RETIRO";
  return (
    <div className="cotizar-detalle" aria-label={t("detalleDesembolso.indemnizacion")}>
      <span>{t("detalleDesembolso.indemnizacion")}</span>
      <strong>
        {formatearMonto(desembolso.monto, desembolso.moneda)}{" "}
        <span className={`home-chip desembolso-chip-${desembolso.estado}`}>
          {ESTADOS_DESEMBOLSO[desembolso.estado] ?? desembolso.estado}
        </span>
      </strong>
      <small>
        {porCodigo ? t("detalleDesembolso.codigo_de_retiro") : t("detalleDesembolso.transferencia_a_valor", { valor: desembolso.destino ?? "tu cuenta" })}
        {desembolso.referencia_transaccion && t("detalleDesembolso.transaccion_referencia_transaccion", { referencia_transaccion: desembolso.referencia_transaccion })}
      </small>
      {porCodigo && desembolso.codigo_retiro && desembolso.estado === "COMPLETADA" && (
        <>
          <small>{t("detalleDesembolso.retira_el_dinero_con_este")}</small>
          <strong className="desembolso-codigo" aria-label={t("detalleDesembolso.codigo_de_retiro")}>
            {desembolso.codigo_retiro}
          </strong>
        </>
      )}
      {desembolso.motivo_fallo && desembolso.estado !== "COMPLETADA" && (
        <small role="note">{MOTIVOS[desembolso.motivo_fallo] ?? desembolso.motivo_fallo}</small>
      )}
    </div>
  );
}

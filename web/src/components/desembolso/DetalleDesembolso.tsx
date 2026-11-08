import type { Desembolso } from "../../services/desembolsos.service";
import { ESTADOS_DESEMBOLSO, formatearMonto } from "./formato";
import "../../styles/desembolsos.css";

const MOTIVOS: Record<string, string> = {
  RED_NO_DISPONIBLE: "La red de pagos no respondió; se reintentará.",
  CUENTA_INEXISTENTE: "El banco rechazó la cuenta registrada.",
};

type Props = { desembolso: Desembolso };

/** Estado de la indemnización: medio, destino, transacción y, al titular, su código de retiro. */
export default function DetalleDesembolso({ desembolso }: Props) {
  const porCodigo = desembolso.medio === "CODIGO_RETIRO";
  return (
    <div className="cotizar-detalle" aria-label="Indemnización">
      <span>Indemnización</span>
      <strong>
        {formatearMonto(desembolso.monto, desembolso.moneda)}{" "}
        <span className={`home-chip desembolso-chip-${desembolso.estado}`}>
          {ESTADOS_DESEMBOLSO[desembolso.estado] ?? desembolso.estado}
        </span>
      </strong>
      <small>
        {porCodigo ? "Código de retiro" : `Transferencia a ${desembolso.destino ?? "tu cuenta"}`}
        {desembolso.referencia_transaccion && ` · Transacción ${desembolso.referencia_transaccion}`}
      </small>
      {porCodigo && desembolso.codigo_retiro && desembolso.estado === "COMPLETADA" && (
        <>
          <small>Retira el dinero con este código y tu documento:</small>
          <strong className="desembolso-codigo" aria-label="Código de retiro">
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

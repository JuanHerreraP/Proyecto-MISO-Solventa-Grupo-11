import { useEffect, useState } from "react";
import {
  BANCOS,
  obtenerCuenta,
  registrarCuenta,
  type CuentaDesembolso,
  type TipoCuenta,
} from "../../services/desembolsos.service";
import "../../styles/desembolsos.css";

import { t } from "../../i18n";

/** Cuenta donde el cliente recibe sus indemnizaciones. Sin cuenta, se paga con código de retiro. */
export default function CuentaIndemnizaciones() {
  const [cuenta, setCuenta] = useState<CuentaDesembolso | null | undefined>(undefined);
  const [editando, setEditando] = useState(false);
  const [banco, setBanco] = useState("1007");
  const [tipo, setTipo] = useState<TipoCuenta>("AHORROS");
  const [numero, setNumero] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let activo = true;
    obtenerCuenta().then(
      (actual) => { if (activo) setCuenta(actual); },
      () => { if (activo) setCuenta(null); },
    );
    return () => { activo = false; };
  }, []);

  const numeroValido = /^\d{6,20}$/.test(numero.replace(/[\s-]/g, ""));

  async function guardar() {
    setGuardando(true);
    setError("");
    try {
      const registrada = await registrarCuenta({
        codigo_banco: banco,
        tipo_cuenta: tipo,
        numero_cuenta: numero.replace(/[\s-]/g, ""),
      });
      setCuenta(registrada);
      setEditando(false);
      setNumero("");
    } catch (fallo) {
      setError((fallo as Error).message);
    } finally {
      setGuardando(false);
    }
  }

  if (cuenta === undefined) return null;

  return (
    <section className="home-panel cuenta-panel" aria-labelledby="titulo-cuenta">
      <h2 id="titulo-cuenta">{t("cuentaIndemnizaciones.cuenta_para_recibir_indemnizaciones")}</h2>
      <p>
        {t("cuentaIndemnizaciones.cuando_se_aprueba_un_siniestro")}
      </p>

      {cuenta && !editando ? (
        <div className="cuenta-actual">
          <strong>
            {cuenta.nombre_banco} · {cuenta.tipo_cuenta === "AHORROS" ? t("cuentaIndemnizaciones.ahorros") : t("cuentaIndemnizaciones.corriente")} · ****{cuenta.ultimos_digitos}
          </strong>
          <button type="button" className="cotizar-boton-secundario" onClick={() => setEditando(true)}>
            {t("cuentaIndemnizaciones.cambiar_cuenta")}
          </button>
        </div>
      ) : (
        <div className="cuenta-form">
          <div className="cotizar-campo">
            <label htmlFor="cuenta-banco">{t("cuentaIndemnizaciones.banco")}</label>
            <select id="cuenta-banco" value={banco} onChange={(e) => setBanco(e.target.value)}>
              {Object.entries(BANCOS).map(([codigo, nombre]) => (
                <option key={codigo} value={codigo}>{nombre}</option>
              ))}
            </select>
          </div>
          <div className="cotizar-campo">
            <label htmlFor="cuenta-tipo">{t("cuentaIndemnizaciones.tipo")}</label>
            <select id="cuenta-tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoCuenta)}>
              <option value="AHORROS">{t("cuentaIndemnizaciones.ahorros")}</option>
              <option value="CORRIENTE">{t("cuentaIndemnizaciones.corriente")}</option>
            </select>
          </div>
          <div className="cotizar-campo">
            <label htmlFor="cuenta-numero">{t("cuentaIndemnizaciones.numero_de_cuenta")}</label>
            <input
              id="cuenta-numero"
              inputMode="numeric"
              autoComplete="off"
              value={numero}
              onChange={(e) => setNumero(e.target.value)}
            />
          </div>
          <div className="cotizar-acciones" style={{ marginTop: 0 }}>
            {cuenta && (
              <button type="button" className="cotizar-boton-secundario" onClick={() => { setEditando(false); setNumero(""); }}>
                {t("cuentaIndemnizaciones.cancelar")}
              </button>
            )}
            <button
              type="button"
              className="cotizar-boton-primario"
              disabled={guardando || !numeroValido}
              onClick={() => void guardar()}
            >
              {guardando ? t("cuentaIndemnizaciones.guardando") : t("cuentaIndemnizaciones.guardar_cuenta")}
            </button>
          </div>
        </div>
      )}
      {error && <p role="alert" className="home-aviso">{error}</p>}
    </section>
  );
}

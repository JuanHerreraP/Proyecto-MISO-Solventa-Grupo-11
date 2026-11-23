import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import {
  confirmarCancelacion,
  consultarCancelacion,
  type Cancelacion,
  type CondicionesCancelacion,
  type MotivoCancelacion,
} from "../services/cancelaciones.service";
import "../styles/cancelaciones.css";

import { t, localeActual } from "../i18n";

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString(localeActual(), {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: 0,
  });
}

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString(localeActual(), {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function nuevaClave(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function CancelarPolizaPage() {
  const { polizaId = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [condiciones, setCondiciones] = useState<CondicionesCancelacion | null>(null);
  const [motivo, setMotivo] = useState<MotivoCancelacion | "">("");
  const [detalle, setDetalle] = useState("");
  const [confirmado, setConfirmado] = useState(false);
  const [clave] = useState(nuevaClave);
  const [cancelacion, setCancelacion] = useState<Cancelacion | null>(null);
  const [cargando, setCargando] = useState(true);
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => { if (activo) setPerfil(datos); },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    consultarCancelacion(polizaId).then(
      (datos) => {
        if (!activo) return;
        setCondiciones(datos);
        setCancelacion(datos.cancelacion);
        setCargando(false);
      },
      (fallo: Error) => {
        if (!activo) return;
        setError(fallo.message);
        setCargando(false);
      },
    );
    return () => { activo = false; };
  }, [navigate, polizaId]);

  async function cancelar() {
    if (!motivo) return;
    setProcesando(true);
    setError("");
    try {
      setCancelacion(
        await confirmarCancelacion(
          polizaId,
          { motivo, ...(detalle.trim() ? { detalle: detalle.trim() } : {}) },
          clave,
        ),
      );
    } catch (fallo) {
      setError((fallo as Error).message);
    } finally {
      setProcesando(false);
    }
  }

  const detalleRequerido = motivo === "OTRO" && !detalle.trim();
  const clienteNombre = (location.state as { clienteNombre?: string } | null)?.clienteNombre;
  const esAsesor = perfil?.rol === "ASESOR_VENTAS";
  const puedeConfirmar = Boolean(
    condiciones?.cancelable && motivo && confirmado && !detalleRequerido && !procesando,
  );

  return (
    <AppLayout activo="Mis pólizas" rol={perfil?.rol ?? null}>
      <header className="home-header">
        <div>
          <h1>{t("cancelarPolizaPage.cancelar_poliza")}</h1>
          <p>{condiciones?.numero_poliza ?? t("cancelarPolizaPage.consulta_las_condiciones_antes_de")}</p>
        </div>
        <button
          type="button"
          className="cotizar-boton-secundario"
          onClick={() => navigate("/polizas")}
        >
          {t("cancelarPolizaPage.volver_a_mis_polizas")}
        </button>
      </header>

      {cargando && <p role="status" className="home-card-vacio">{t("cancelarPolizaPage.calculando_condiciones")}</p>}
      {error && <p role="alert" className="home-aviso">{error}</p>}

      {esAsesor && (
        <p className="cancelacion-asistida">
          <span className="material-symbols-outlined" aria-hidden="true">support_agent</span>
          {t("cancelarPolizaPage.estas_gestionando_esta_cancelacion_como")}
          {clienteNombre ? ` para ${clienteNombre}` : t("cancelarPolizaPage.en_nombre_del_cliente")}.
        </p>
      )}

      {cancelacion && (
        <section className="home-panel cancelacion-resultado" aria-label={t("cancelarPolizaPage.poliza_cancelada")}>
          <span className="material-symbols-outlined" aria-hidden="true">check_circle</span>
          <div>
            <h2>{t("cancelarPolizaPage.poliza_cancelada")}</h2>
            <p>{t("cancelarPolizaPage.la_cancelacion_rige_desde_el", { formatearFecha: formatearFecha(cancelacion.fecha_efecto) })}</p>
            <strong>
              {cancelacion.saldo_estimado === "0.00"
                ? t("cancelarPolizaPage.no_hay_saldo_pendiente_de")
                : t("cancelarPolizaPage.saldo_estimado_a_devolver_formatearmonto", { formatearMonto: formatearMonto(cancelacion.saldo_estimado, cancelacion.moneda) })}
            </strong>
          </div>
        </section>
      )}

      {condiciones && !cancelacion && !condiciones.cancelable && (
        <section className="home-panel cancelacion-bloqueada" aria-labelledby="cancelacion-no-disponible">
          <h2 id="cancelacion-no-disponible">{t("cancelarPolizaPage.esta_poliza_no_se_puede")}</h2>
          <ul>
            {condiciones.bloqueos.map((bloqueo) => (
              <li key={bloqueo.codigo}>{bloqueo.mensaje}</li>
            ))}
          </ul>
        </section>
      )}

      {condiciones?.cancelable && !cancelacion && (
        <div className="cancelacion-pagina">
          <section className="home-panel cancelacion-resumen" aria-labelledby="resumen-cancelacion">
            <h2 id="resumen-cancelacion">{t("cancelarPolizaPage.liquidacion_estimada")}</h2>
            <dl className="cotizacion-datos">
              <div><dt>{t("cancelarPolizaPage.prima_pagada")}</dt><dd>{formatearMonto(condiciones.prima_total, condiciones.moneda)}</dd></div>
              <div><dt>{t("cancelarPolizaPage.dias_de_cobertura_sin_usar")}</dt><dd>{condiciones.dias_no_transcurridos}</dd></div>
              <div className="cancelacion-saldo">
                <dt>{t("cancelarPolizaPage.saldo_estimado_a_devolver")}</dt>
                <dd>{formatearMonto(condiciones.saldo_estimado, condiciones.moneda)}</dd>
              </div>
            </dl>
            <small>{t("cancelarPolizaPage.el_valor_definitivo_se_gestionara")}</small>
          </section>

          <section className="home-panel cancelacion-formulario" aria-labelledby="motivo-cancelacion">
            <h2 id="motivo-cancelacion">{t("cancelarPolizaPage.motivo_de_cancelacion")}</h2>
            <div className="cotizar-campo">
              <label htmlFor="motivo">{t("cancelarPolizaPage.selecciona_un_motivo")}</label>
              <select
                id="motivo"
                value={motivo}
                onChange={(evento) => {
                  setMotivo(evento.target.value as MotivoCancelacion | "");
                  setConfirmado(false);
                }}
              >
                <option value="">{t("cancelarPolizaPage.selecciona_una_opcion")}</option>
                {condiciones.motivos.map((opcion) => (
                  <option key={opcion.codigo} value={opcion.codigo}>{opcion.etiqueta}</option>
                ))}
              </select>
            </div>

            <div className="cotizar-campo">
              <label htmlFor="detalle">{motivo === "OTRO" ? t("cancelarPolizaPage.cuentanos_mas_obligatorio") : t("cancelarPolizaPage.cuentanos_mas_opcional")}</label>
              <textarea
                id="detalle"
                value={detalle}
                maxLength={300}
                rows={3}
                onChange={(evento) => {
                  setDetalle(evento.target.value);
                  setConfirmado(false);
                }}
              />
            </div>

            <h3>{t("cancelarPolizaPage.ten_en_cuenta")}</h3>
            <ul className="cancelacion-consecuencias">
              {condiciones.consecuencias.map((consecuencia) => (
                <li key={consecuencia}>{consecuencia}</li>
              ))}
            </ul>

            <label className="endoso-aceptar">
              <input
                type="checkbox"
                checked={confirmado}
                onChange={(evento) => setConfirmado(evento.target.checked)}
              />
              {t("cancelarPolizaPage.confirmo_que_quiero_cancelar_esta")}
            </label>

            <div className="cotizar-acciones">
              <button
                type="button"
                className="cotizar-boton-secundario"
                onClick={() => navigate("/polizas")}
              >
                {t("cancelarPolizaPage.conservar_mi_poliza")}
              </button>
              <button
                type="button"
                className="poliza-boton-cancelar poliza-boton-cancelar-solido"
                disabled={!puedeConfirmar}
                onClick={() => void cancelar()}
              >
                {procesando ? t("cancelarPolizaPage.cancelando") : t("cancelarPolizaPage.confirmar_cancelacion")}
              </button>
            </div>
          </section>
        </div>
      )}
    </AppLayout>
  );
}

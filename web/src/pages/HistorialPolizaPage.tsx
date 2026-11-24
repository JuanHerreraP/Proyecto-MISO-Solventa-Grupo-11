import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import { obtenerHistorialPoliza } from "../services/historial-poliza.service";
import type {
  CategoriaMovimiento,
  HistorialPoliza,
  MovimientoPoliza,
  NaturalezaMonto,
  TipoMovimiento,
} from "../types/historial";

import { t, localeActual } from "../i18n";

const ICONO_TIPO: Record<TipoMovimiento, string> = {
  EMISION: "verified",
  PAGO_PRIMA_INICIAL: "payments",
  ENDOSO: "edit_document",
  RENOVACION: "autorenew",
  CANCELACION: "cancel",
  DESEMBOLSO_INDEMNIZACION: "account_balance_wallet",
  REEMBOLSO: "undo",
};

const TITULO_TIPO: Record<TipoMovimiento, string> = {
  get EMISION() { return t("historialPolizaPage.emision_de_poliza"); },
  get PAGO_PRIMA_INICIAL() { return t("historialPolizaPage.pago_de_prima_inicial"); },
  get ENDOSO() { return t("historialPolizaPage.modificacion_contractual"); },
  get RENOVACION() { return t("historialPolizaPage.renovacion"); },
  get CANCELACION() { return t("historialPolizaPage.cancelacion"); },
  get DESEMBOLSO_INDEMNIZACION() { return t("historialPolizaPage.pago_de_indemnizacion"); },
  get REEMBOLSO() { return t("historialPolizaPage.reembolso"); },
};

const ETIQUETA_CATEGORIA: Record<CategoriaMovimiento, string> = {
  get FINANCIERO() { return t("historialPolizaPage.movimiento_financiero"); },
  get CONTRACTUAL() { return t("historialPolizaPage.movimiento_contractual"); },
  get POLIZA() { return t("historialPolizaPage.poliza"); },
};

function formatearFechaHora(iso: string): string {
  const fecha = new Date(iso);
  return fecha.toLocaleString(localeActual(), {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** El monto siempre es positivo; el signo mostrado depende de la naturaleza del movimiento. */
function formatearMonto(monto: string, moneda: string | null, naturaleza: NaturalezaMonto | null): string {
  const valor = Number(monto).toLocaleString(localeActual(), {
    style: "currency",
    currency: moneda ?? "COP",
    maximumFractionDigits: 0,
  });
  if (naturaleza === "COBRO") return `-${valor}`;
  if (naturaleza === "REEMBOLSO" || naturaleza === "INDEMNIZACION") return `+${valor}`;
  return valor;
}

/** Representa de forma legible un lado del linaje (antes/después) de un endoso. */
function entradasLinaje(datos: Record<string, string> | null): [string, string][] {
  if (!datos) return [];
  return Object.entries(datos);
}

export default function HistorialPolizaPage() {
  const navigate = useNavigate();
  const { polizaId = "" } = useParams<{ polizaId: string }>();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [historial, setHistorial] = useState<HistorialPoliza | null>(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(true);
  const [expandido, setExpandido] = useState<string | null>(null);

  const cargar = useCallback(() => {
    return obtenerHistorialPoliza(polizaId).then(
      (datos) => { setHistorial(datos); setError(""); setCargando(false); },
      (fallo: Error) => { setError(fallo.message); setCargando(false); },
    );
  }, [polizaId]);

  function reintentar() {
    setCargando(true);
    void cargar();
  }

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => { if (activo) setPerfil(datos); },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    void cargar();
    return () => { activo = false; };
  }, [navigate, cargar]);

  const rol = perfil?.rol ?? null;
  const movimientos = historial?.movimientos ?? [];

  return (
    <AppLayout activo="Mis pólizas" rol={rol}>
      <header className="home-header">
        <div>
          <h1>{t("historialPolizaPage.historial_de_movimientos")}</h1>
          {historial && <p>{historial.numero_poliza}</p>}
        </div>
        <button type="button" className="cotizar-boton-secundario" onClick={() => navigate("/polizas")}>
          {t("historialPolizaPage.volver_a_mis_polizas")}
        </button>
      </header>

      {error && (
        <div className="home-panel">
          <p role="alert" className="home-aviso">{error}</p>
          <button type="button" className="cotizar-boton-primario" onClick={() => reintentar()}>
            {t("historialPolizaPage.reintentar")}
          </button>
        </div>
      )}

      {cargando && !error && (
        <p role="status" className="home-card-vacio">{t("historialPolizaPage.cargando_historial")}</p>
      )}

      {!cargando && !error && movimientos.length === 0 && (
        <div className="home-panel">
          <p className="home-card-vacio">
            {t("historialPolizaPage.todavia_no_hay_movimientos_registrados")}
          </p>
        </div>
      )}

      {!cargando && !error && movimientos.length > 0 && (
        <section aria-label={t("historialPolizaPage.historial_de_movimientos")} className="cotizaciones-lista">
          {movimientos.map((movimiento) => (
            <TarjetaMovimiento
              key={movimiento.movimiento_id}
              movimiento={movimiento}
              abierto={expandido === movimiento.movimiento_id}
              onAlternar={() =>
                setExpandido(
                  expandido === movimiento.movimiento_id ? null : movimiento.movimiento_id,
                )
              }
            />
          ))}
        </section>
      )}
    </AppLayout>
  );
}

function TarjetaMovimiento({
  movimiento,
  abierto,
  onAlternar,
}: {
  movimiento: MovimientoPoliza;
  abierto: boolean;
  onAlternar: () => void;
}) {
  const tieneDetalle = movimiento.cambios.length > 0 || movimiento.consentimiento !== null;

  return (
    <article className="cotizacion-item">
      <div className="cotizacion-cabecera" style={{ cursor: "default" }}>
        <span className="cotizar-ramo-icono material-symbols-outlined" aria-hidden="true">
          {ICONO_TIPO[movimiento.tipo] ?? "history"}
        </span>
        <span className="cotizacion-cabecera-texto">
          <strong>{TITULO_TIPO[movimiento.tipo] ?? movimiento.tipo}</strong>
          <small>{formatearFechaHora(movimiento.fecha)}</small>
          <small>{ETIQUETA_CATEGORIA[movimiento.categoria]}</small>
        </span>
        {movimiento.estado && (
          <span className="home-chip cotizacion-estado">{movimiento.estado}</span>
        )}
      </div>

      <div className="cotizacion-detalle">
        <p className="siniestro-descripcion">{movimiento.descripcion}</p>

        <dl className="cotizacion-datos">
          {movimiento.monto !== null && (
            <div>
              <dt>{movimiento.naturaleza_monto === "AJUSTE" ? t("historialPolizaPage.ajuste_de_prima") : t("historialPolizaPage.monto")}</dt>
              <dd>{formatearMonto(movimiento.monto, movimiento.moneda, movimiento.naturaleza_monto)}</dd>
            </div>
          )}
          {movimiento.referencia && (
            <div>
              <dt>{t("historialPolizaPage.referencia")}</dt>
              <dd>{movimiento.referencia}</dd>
            </div>
          )}
          {movimiento.categoria === "FINANCIERO" && (
            <div>
              <dt>{t("historialPolizaPage.referencia_de_pasarela")}</dt>
              <dd>{movimiento.referencia_externa ?? t("historialPolizaPage.sin_referencia_externa")}</dd>
            </div>
          )}
        </dl>

        {movimiento.consentimiento?.explicito && (
          <p className="historial-consentimiento">
            <span className="material-symbols-outlined" aria-hidden="true">check_circle</span>
            {t("historialPolizaPage.consentimiento_confirmado_por_el_cliente")}
          </p>
        )}

        {tieneDetalle && (
          <button
            type="button"
            className="cotizar-boton-secundario"
            aria-expanded={abierto}
            onClick={onAlternar}
          >
            {abierto ? t("historialPolizaPage.ocultar_detalle") : t("historialPolizaPage.ver_detalle")}
          </button>
        )}

        {abierto && movimiento.cambios.length > 0 && (
          <div className="historial-cambios">
            <h3 className="cotizacion-subtitulo">{t("historialPolizaPage.cambios")}</h3>
            {movimiento.cambios.map((cambio, indice) => (
              <div key={`${movimiento.movimiento_id}-${indice}`} className="historial-cambio">
                <strong>{cambio.descripcion}</strong>
                <div className="historial-linaje">
                  <div>
                    <span className="historial-linaje-rotulo">{t("historialPolizaPage.antes")}</span>
                    {entradasLinaje(cambio.antes).length === 0 ? (
                      <small>—</small>
                    ) : (
                      entradasLinaje(cambio.antes).map(([campo, valor]) => (
                        <small key={`antes-${campo}`}>{campo}: {valor}</small>
                      ))
                    )}
                  </div>
                  <div>
                    <span className="historial-linaje-rotulo">{t("historialPolizaPage.despues")}</span>
                    {entradasLinaje(cambio.despues).length === 0 ? (
                      <small>—</small>
                    ) : (
                      entradasLinaje(cambio.despues).map(([campo, valor]) => (
                        <small key={`despues-${campo}`}>{campo}: {valor}</small>
                      ))
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}

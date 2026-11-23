import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import {
  obtenerHistorialPoliza,
  resolverPolizaAuditoria,
} from "../services/historial-poliza.service";
import type {
  CategoriaMovimiento,
  HistorialPoliza,
  MovimientoPoliza,
  NaturalezaMonto,
  TipoMovimiento,
} from "../types/historial-poliza";

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
  get EMISION() { return t("consultaHistorialContractualPage.emision_de_poliza"); },
  get PAGO_PRIMA_INICIAL() { return t("consultaHistorialContractualPage.pago_de_prima_inicial"); },
  get ENDOSO() { return t("consultaHistorialContractualPage.modificacion_contractual"); },
  get RENOVACION() { return t("consultaHistorialContractualPage.renovacion"); },
  get CANCELACION() { return t("consultaHistorialContractualPage.cancelacion"); },
  get DESEMBOLSO_INDEMNIZACION() { return t("consultaHistorialContractualPage.pago_de_indemnizacion"); },
  get REEMBOLSO() { return t("consultaHistorialContractualPage.reembolso"); },
};

const ETIQUETA_CATEGORIA: Record<CategoriaMovimiento, string> = {
  get FINANCIERO() { return t("consultaHistorialContractualPage.movimiento_financiero"); },
  get CONTRACTUAL() { return t("consultaHistorialContractualPage.movimiento_contractual"); },
  get POLIZA() { return t("consultaHistorialContractualPage.poliza"); },
};

function formatearFechaHora(iso: string): string {
  return new Date(iso).toLocaleString(localeActual(), {
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

/** Ajuste de prima con signo explícito; es un cambio contractual, no un cobro ejecutado. */
function formatearAjuste(valor: string, moneda: string): string {
  const numero = Number(valor);
  const texto = Math.abs(numero).toLocaleString(localeActual(), {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: 0,
  });
  if (numero > 0) return `+${texto}`;
  if (numero < 0) return `-${texto}`;
  return texto;
}

function entradasLinaje(datos: Record<string, string> | null): [string, string][] {
  return datos ? Object.entries(datos) : [];
}

export default function ConsultaHistorialContractualPage() {
  const navigate = useNavigate();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [identificador, setIdentificador] = useState("");
  const [errorCampo, setErrorCampo] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [historial, setHistorial] = useState<HistorialPoliza | null>(null);
  const [expandido, setExpandido] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => { if (activo) setPerfil(datos); },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    return () => { activo = false; };
  }, [navigate]);

  async function consultar(evento: React.FormEvent) {
    evento.preventDefault();
    const valor = identificador.trim();
    if (valor === "") {
      setErrorCampo(t("consultaHistorialContractualPage.ingresa_el_identificador_o_numero"));
      return;
    }
    setErrorCampo("");
    setError("");
    setCargando(true);
    setHistorial(null);
    setExpandido(null);
    try {
      const resuelta = await resolverPolizaAuditoria(valor);
      const datos = await obtenerHistorialPoliza(resuelta.poliza_id);
      setHistorial(datos);
    } catch (fallo) {
      setError((fallo as Error).message);
    } finally {
      setCargando(false);
    }
  }

  const rol = perfil?.rol ?? null;
  const movimientos = historial?.movimientos ?? [];

  return (
    <AppLayout activo="Historial contractual" rol={rol}>
      <header className="home-header">
        <div>
          <h1>{t("consultaHistorialContractualPage.consulta_de_historial_contractual")}</h1>
          <p>{t("consultaHistorialContractualPage.consulta_las_transacciones_y_cambios")}</p>
        </div>
      </header>

      <section className="home-panel" aria-labelledby="buscar-poliza">
        <h2 id="buscar-poliza" className="home-acciones-titulo">{t("consultaHistorialContractualPage.buscar_poliza")}</h2>
        <form onSubmit={consultar} aria-label={t("consultaHistorialContractualPage.consultar_historial_de_una_poliza")}>
          <div className="cotizar-campo cotizar-campo-ancho">
            <label htmlFor="identificador-poliza">{t("consultaHistorialContractualPage.poliza")}</label>
            <input
              id="identificador-poliza"
              type="text"
              value={identificador}
              placeholder={t("consultaHistorialContractualPage.pol_001_o_solv_vid")}
              aria-invalid={errorCampo !== ""}
              aria-describedby={errorCampo ? "error-identificador" : undefined}
              onChange={(e) => setIdentificador(e.target.value)}
            />
          </div>
          {errorCampo && (
            <p id="error-identificador" role="alert" className="home-aviso">{errorCampo}</p>
          )}
          <div className="cotizar-acciones">
            <button type="submit" className="cotizar-boton-primario" disabled={cargando}>
              {cargando ? t("consultaHistorialContractualPage.consultando") : t("consultaHistorialContractualPage.consultar_historial")}
            </button>
          </div>
        </form>
      </section>

      {error && (
        <div className="home-panel">
          <p role="alert" className="home-aviso">{error}</p>
        </div>
      )}

      {cargando && !error && (
        <p role="status" className="home-card-vacio">{t("consultaHistorialContractualPage.cargando_historial")}</p>
      )}

      {historial && !cargando && (
        <>
          <section className="home-panel" aria-label={t("consultaHistorialContractualPage.datos_de_la_poliza")}>
            <h2>{historial.nombre_ramo ?? t("consultaHistorialContractualPage.poliza")}</h2>
            <p className="home-card-detalle">{historial.numero_poliza}</p>
            <dl className="cotizacion-datos">
              <div>
                <dt>{t("consultaHistorialContractualPage.cliente")}</dt>
                <dd>{historial.cliente_id ?? "—"}</dd>
              </div>
              <div>
                <dt>{t("consultaHistorialContractualPage.estado")}</dt>
                <dd><span className="home-chip cotizacion-estado">{historial.estado ?? "—"}</span></dd>
              </div>
            </dl>
          </section>

          {movimientos.length === 0 ? (
            <div className="home-panel">
              <p className="home-card-vacio">
                {t("consultaHistorialContractualPage.todavia_no_hay_movimientos_registrados")}
              </p>
            </div>
          ) : (
            <section aria-label={t("consultaHistorialContractualPage.historial_de_movimientos")} className="cotizaciones-lista">
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
        </>
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
  const auditoria = movimiento.auditoria ?? null;
  const ajuste = movimiento.ajuste_prima ?? null;
  const tieneDetalle =
    movimiento.cambios.length > 0 ||
    movimiento.consentimiento !== null ||
    auditoria !== null ||
    ajuste !== null;

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
              <dt>{movimiento.naturaleza_monto === "AJUSTE" ? t("consultaHistorialContractualPage.ajuste_de_prima") : t("consultaHistorialContractualPage.monto")}</dt>
              <dd>{formatearMonto(movimiento.monto, movimiento.moneda, movimiento.naturaleza_monto)}</dd>
            </div>
          )}
          {movimiento.referencia && (
            <div>
              <dt>{t("consultaHistorialContractualPage.id_interno")}</dt>
              <dd>{movimiento.referencia}</dd>
            </div>
          )}
          {movimiento.categoria === "FINANCIERO" && (
            <div>
              <dt>{t("consultaHistorialContractualPage.id_pasarela")}</dt>
              <dd>{movimiento.referencia_externa ?? t("consultaHistorialContractualPage.sin_referencia_externa")}</dd>
            </div>
          )}
        </dl>

        {movimiento.consentimiento?.explicito && (
          <p className="historial-consentimiento">
            <span className="material-symbols-outlined" aria-hidden="true">check_circle</span>
            {t("consultaHistorialContractualPage.consentimiento_aceptacion_explicita_registrada")}
          </p>
        )}

        {tieneDetalle && (
          <button
            type="button"
            className="cotizar-boton-secundario"
            aria-expanded={abierto}
            onClick={onAlternar}
          >
            {abierto ? t("consultaHistorialContractualPage.ocultar_detalle") : t("consultaHistorialContractualPage.ver_detalle")}
          </button>
        )}

        {abierto && (
          <div className="historial-cambios">
            {ajuste && (
              <div className="historial-cambio">
                <h3 className="cotizacion-subtitulo">{t("consultaHistorialContractualPage.ajuste_de_prima_contractual")}</h3>
                <dl className="cotizacion-datos">
                  <div>
                    <dt>{t("consultaHistorialContractualPage.prima_anterior")}</dt>
                    <dd>{formatearAjuste(ajuste.prima_anterior, ajuste.moneda)}</dd>
                  </div>
                  <div>
                    <dt>{t("consultaHistorialContractualPage.ajuste")}</dt>
                    <dd>{formatearAjuste(ajuste.ajuste, ajuste.moneda)}</dd>
                  </div>
                  <div>
                    <dt>{t("consultaHistorialContractualPage.nueva_prima")}</dt>
                    <dd>{formatearAjuste(ajuste.prima_nueva, ajuste.moneda)}</dd>
                  </div>
                </dl>
              </div>
            )}

            {movimiento.cambios.length > 0 && (
              <div className="historial-cambio">
                <h3 className="cotizacion-subtitulo">{t("consultaHistorialContractualPage.cambios")}</h3>
                {movimiento.cambios.map((cambio, indice) => (
                  <div key={`${movimiento.movimiento_id}-${indice}`} className="historial-cambio">
                    <strong>{cambio.descripcion}</strong>
                    <div className="historial-linaje">
                      <div>
                        <span className="historial-linaje-rotulo">{t("consultaHistorialContractualPage.antes")}</span>
                        {entradasLinaje(cambio.antes).length === 0 ? (
                          <small>—</small>
                        ) : (
                          entradasLinaje(cambio.antes).map(([campo, valor]) => (
                            <small key={`antes-${campo}`}>{campo}: {valor}</small>
                          ))
                        )}
                      </div>
                      <div>
                        <span className="historial-linaje-rotulo">{t("consultaHistorialContractualPage.despues")}</span>
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

            {auditoria && (
              <div className="historial-cambio">
                <h3 className="cotizacion-subtitulo">{t("consultaHistorialContractualPage.informacion_de_auditoria")}</h3>
                <dl className="cotizacion-datos">
                  <div>
                    <dt>{t("consultaHistorialContractualPage.usuario")}</dt>
                    <dd>{auditoria.usuario_id ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>{t("consultaHistorialContractualPage.rol")}</dt>
                    <dd>{auditoria.rol ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>IP</dt>
                    <dd>{auditoria.ip_solicitante ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>{t("consultaHistorialContractualPage.navegador")}</dt>
                    <dd>{auditoria.user_agent ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>{t("consultaHistorialContractualPage.huella_de_solicitud")}</dt>
                    <dd>{auditoria.huella_solicitud ?? "—"}</dd>
                  </div>
                </dl>
              </div>
            )}
          </div>
        )}
      </div>
    </article>
  );
}

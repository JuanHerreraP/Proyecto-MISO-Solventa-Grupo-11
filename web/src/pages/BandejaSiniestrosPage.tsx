import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import DetalleDesembolso from "../components/desembolso/DetalleDesembolso";
import { formatearMonto } from "../components/desembolso/formato";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import {
  aprobarSiniestro,
  obtenerBandeja,
  rechazarSiniestro,
  reintentarDesembolso,
  type SiniestroBandeja,
} from "../services/desembolsos.service";
import type { EstadoSiniestro } from "../types/siniestros";
import "../styles/desembolsos.css";

import { t, localeActual } from "../i18n";

const FILTROS: { etiqueta: string; estado?: EstadoSiniestro }[] = [
  { get etiqueta() { return t("bandejaSiniestrosPage.por_evaluar"); }, estado: "REGISTRADO" },
  { get etiqueta() { return t("bandejaSiniestrosPage.aprobados"); }, estado: "APROBADO" },
  { get etiqueta() { return t("bandejaSiniestrosPage.rechazados"); }, estado: "RECHAZADO" },
  { get etiqueta() { return t("bandejaSiniestrosPage.todos"); } },
];

const ESTADOS: Record<string, string> = {
  get REGISTRADO() { return t("bandejaSiniestrosPage.por_evaluar"); },
  get EN_EVALUACION() { return t("bandejaSiniestrosPage.en_evaluacion"); },
  get APROBADO() { return t("bandejaSiniestrosPage.aprobado"); },
  get RECHAZADO() { return t("bandejaSiniestrosPage.rechazado"); },
};

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString(localeActual(), {
    day: "numeric", month: "long", year: "numeric",
  });
}

export default function BandejaSiniestrosPage() {
  const navigate = useNavigate();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [filtro, setFiltro] = useState<EstadoSiniestro | undefined>("REGISTRADO");
  const [siniestros, setSiniestros] = useState<SiniestroBandeja[] | null>(null);
  const [error, setError] = useState("");
  const [abierto, setAbierto] = useState<string | null>(null);
  const [monto, setMonto] = useState("");
  const [motivo, setMotivo] = useState("");
  const [procesando, setProcesando] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState("");
  const [aviso, setAviso] = useState("");

  const cargar = useCallback(() => {
    return obtenerBandeja(filtro).then(
      (lista) => { setSiniestros(lista); setError(""); },
      (fallo: Error) => { setError(fallo.message); },
    );
  }, [filtro]);

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => { if (activo) setPerfil(datos); },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    void cargar();
    return () => { activo = false; };
  }, [navigate, cargar]);

  function alternar(siniestro: SiniestroBandeja) {
    const abrir = abierto !== siniestro.siniestro_id;
    setAbierto(abrir ? siniestro.siniestro_id : null);
    setMonto(abrir ? String(Number(siniestro.estimacion_danos)) : "");
    setMotivo("");
    setErrorAccion("");
  }

  async function ejecutar(siniestroId: string, accion: () => Promise<unknown>, exito: string) {
    setProcesando(siniestroId);
    setErrorAccion("");
    try {
      await accion();
      setAviso(exito);
      setAbierto(null);
      await cargar();
    } catch (fallo) {
      setErrorAccion((fallo as Error).message);
    } finally {
      setProcesando(null);
    }
  }

  return (
    <AppLayout activo="Bandeja de siniestros" rol={perfil?.rol ?? null}>
      <header className="home-header">
        <div>
          <h1>{t("bandejaSiniestrosPage.bandeja_de_siniestros")}</h1>
          <p>{t("bandejaSiniestrosPage.evalua_las_reclamaciones_al_aprobar")}</p>
        </div>
      </header>

      <div className="bandeja-filtros" role="group" aria-label={t("bandejaSiniestrosPage.filtrar_por_estado")}>
        {FILTROS.map(({ etiqueta, estado }) => (
          <button
            key={etiqueta}
            type="button"
            className="bandeja-filtro"
            aria-pressed={filtro === estado}
            onClick={() => { setFiltro(estado); setAbierto(null); setAviso(""); }}
          >
            {etiqueta}
          </button>
        ))}
      </div>

      {aviso && <p role="status" className="cotizar-mensaje-ok">{aviso}</p>}
      {error && <p role="alert" className="home-aviso">{error}</p>}

      <section aria-label={t("bandejaSiniestrosPage.siniestros")} className="cotizaciones-lista">
        {siniestros === null && !error && (
          <p role="status" className="home-card-vacio">{t("bandejaSiniestrosPage.cargando_la_bandeja")}</p>
        )}
        {siniestros?.length === 0 && (
          <div className="home-panel"><p className="home-card-vacio">{t("bandejaSiniestrosPage.no_hay_siniestros_en_esta")}</p></div>
        )}
        {siniestros?.map((s) => {
          const esAbierto = abierto === s.siniestro_id;
          const ocupado = procesando === s.siniestro_id;
          const porEvaluar = s.estado === "REGISTRADO" || s.estado === "EN_EVALUACION";
          const reintentable =
            s.estado === "APROBADO" && (s.desembolso === null || s.desembolso.estado !== "COMPLETADA");
          return (
            <article key={s.siniestro_id} className="cotizacion-item">
              <button
                type="button"
                className="cotizacion-cabecera"
                aria-expanded={esAbierto}
                onClick={() => alternar(s)}
              >
                <span className="cotizar-ramo-icono material-symbols-outlined" aria-hidden="true">
                  {s.origen === "AUTOMATICO" ? "bolt" : "error"}
                </span>
                <span className="cotizacion-cabecera-texto">
                  <strong>{formatearMonto(s.estimacion_danos, s.moneda)} · {s.lugar}</strong>
                  <small>
                    {s.origen === "AUTOMATICO" ? t("bandejaSiniestrosPage.parametrico") : t("bandejaSiniestrosPage.manual")} · {formatearFecha(s.fecha_evento)} · {s.poliza_id}
                  </small>
                </span>
                <span className="home-chip cotizacion-estado">{ESTADOS[s.estado] ?? s.estado}</span>
                <span className="material-symbols-outlined cotizacion-chevron" aria-hidden="true">
                  {esAbierto ? "expand_less" : "expand_more"}
                </span>
              </button>

              {esAbierto && (
                <div className="cotizacion-detalle">
                  <h3 className="cotizacion-subtitulo">{t("bandejaSiniestrosPage.descripcion")}</h3>
                  <p className="siniestro-descripcion">{s.descripcion}</p>
                  <dl className="cotizacion-datos">
                    <div><dt>{t("bandejaSiniestrosPage.siniestro")}</dt><dd>{s.siniestro_id}</dd></div>
                    <div><dt>{t("bandejaSiniestrosPage.registrado")}</dt><dd>{formatearFecha(s.registrado_en)}</dd></div>
                    {s.monto_aprobado && (
                      <div><dt>{t("bandejaSiniestrosPage.monto_aprobado")}</dt><dd>{formatearMonto(s.monto_aprobado, s.moneda)}</dd></div>
                    )}
                    {s.evaluado_por && (
                      <div><dt>{t("bandejaSiniestrosPage.evaluado_por")}</dt><dd>{s.evaluado_por === "SISTEMA" ? t("bandejaSiniestrosPage.aprobacion_automatica") : s.evaluado_por}</dd></div>
                    )}
                    {s.motivo_rechazo && (
                      <div><dt>{t("bandejaSiniestrosPage.motivo_del_rechazo")}</dt><dd>{s.motivo_rechazo}</dd></div>
                    )}
                  </dl>

                  {s.desembolso && <DetalleDesembolso desembolso={s.desembolso} />}

                  {porEvaluar && (
                    <div className="bandeja-decision">
                      <div>
                        <h4>{t("bandejaSiniestrosPage.aprobar")}</h4>
                        <div className="cotizar-campo">
                          <label htmlFor={`monto-${s.siniestro_id}`}>{t("bandejaSiniestrosPage.monto_a_indemnizar")}</label>
                          <input
                            id={`monto-${s.siniestro_id}`}
                            type="number"
                            inputMode="numeric"
                            min={1}
                            value={monto}
                            onChange={(e) => setMonto(e.target.value)}
                          />
                          <span className="cotizar-ayuda">{t("bandejaSiniestrosPage.tope_la_suma_asegurada_de")}</span>
                        </div>
                        <button
                          type="button"
                          className="cotizar-boton-primario"
                          disabled={ocupado || !(Number(monto) > 0)}
                          onClick={() => void ejecutar(
                            s.siniestro_id,
                            () => aprobarSiniestro(s.siniestro_id, monto),
                            t("bandejaSiniestrosPage.siniestro_aprobado_se_ordeno_el"),
                          )}
                        >
                          {ocupado ? t("bandejaSiniestrosPage.procesando") : t("bandejaSiniestrosPage.aprobar_y_desembolsar")}
                        </button>
                      </div>
                      <div>
                        <h4>{t("bandejaSiniestrosPage.rechazar")}</h4>
                        <div className="cotizar-campo">
                          <label htmlFor={`motivo-${s.siniestro_id}`}>{t("bandejaSiniestrosPage.motivo")}</label>
                          <textarea
                            id={`motivo-${s.siniestro_id}`}
                            rows={3}
                            maxLength={500}
                            value={motivo}
                            onChange={(e) => setMotivo(e.target.value)}
                          />
                        </div>
                        <button
                          type="button"
                          className="boton-rechazar"
                          disabled={ocupado || motivo.trim().length < 5}
                          onClick={() => void ejecutar(
                            s.siniestro_id,
                            () => rechazarSiniestro(s.siniestro_id, motivo.trim()),
                            t("bandejaSiniestrosPage.siniestro_rechazado"),
                          )}
                        >
                          {t("bandejaSiniestrosPage.rechazar_siniestro")}
                        </button>
                      </div>
                    </div>
                  )}

                  {reintentable && (
                    <div className="poliza-acciones">
                      <button
                        type="button"
                        className="cotizar-boton-primario"
                        disabled={ocupado}
                        onClick={() => void ejecutar(
                          s.siniestro_id,
                          () => reintentarDesembolso(s.siniestro_id),
                          t("bandejaSiniestrosPage.se_reintento_el_desembolso"),
                        )}
                      >
                        {ocupado ? t("bandejaSiniestrosPage.reintentando") : t("bandejaSiniestrosPage.reintentar_desembolso")}
                      </button>
                    </div>
                  )}
                  {errorAccion && <p role="alert" className="home-aviso">{errorAccion}</p>}
                </div>
              )}
            </article>
          );
        })}
      </section>
    </AppLayout>
  );
}

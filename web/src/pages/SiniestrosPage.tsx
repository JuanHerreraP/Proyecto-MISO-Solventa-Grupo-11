import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import CuentaIndemnizaciones from "../components/desembolso/CuentaIndemnizaciones";
import DetalleDesembolso from "../components/desembolso/DetalleDesembolso";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import { obtenerBilletera, type PolizaResumen } from "../services/billetera.service";
import { listarDesembolsos, type Desembolso } from "../services/desembolsos.service";
import { listarSiniestros } from "../services/siniestros.service";
import type { EstadoSiniestro, Siniestro } from "../types/siniestros";

import { t, localeActual } from "../i18n";

const ESTADOS: Record<EstadoSiniestro, string> = {
  get REGISTRADO() { return t("siniestrosPage.registrado"); },
  get EN_EVALUACION() { return t("siniestrosPage.en_evaluacion"); },
  get APROBADO() { return t("siniestrosPage.aprobado"); },
  get RECHAZADO() { return t("siniestrosPage.rechazado"); },
};

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString(localeActual(), {
    day: "numeric", month: "long", year: "numeric",
  });
}

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString(localeActual(), {
    style: "currency", currency: moneda, maximumFractionDigits: 0,
  });
}

export default function SiniestrosPage() {
  const navigate = useNavigate();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [siniestros, setSiniestros] = useState<Siniestro[] | null>(null);
  const [polizas, setPolizas] = useState<PolizaResumen[]>([]);
  const [error, setError] = useState("");
  const [expandido, setExpandido] = useState<string | null>(null);
  const [desembolsos, setDesembolsos] = useState<Desembolso[]>([]);

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => { if (activo) setPerfil(datos); },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    listarSiniestros().then(
      (lista) => { if (activo) setSiniestros(lista); },
      (fallo: Error) => { if (activo) setError(fallo.message); },
    );
    // El estado de cada indemnización (HU15); sin ella, la lista se muestra igual.
    listarDesembolsos().then(
      (lista) => { if (activo) setDesembolsos(lista); },
      () => undefined,
    );
    // La billetera aporta el nombre del ramo y número de la póliza asociada.
    obtenerBilletera().then(
      (billetera) => { if (activo) setPolizas(billetera.polizas); },
      () => undefined,
    );
    return () => { activo = false; };
  }, [navigate]);

  const rol = perfil?.rol ?? null;

  const polizaPorId = useMemo(() => {
    const mapa: Record<string, PolizaResumen> = {};
    for (const p of polizas) mapa[p.poliza_id] = p;
    return mapa;
  }, [polizas]);

  const desembolsoPorSiniestro = useMemo(() => {
    const mapa: Record<string, Desembolso> = {};
    for (const d of desembolsos) mapa[d.siniestro_id] = d;
    return mapa;
  }, [desembolsos]);

  return (
    <AppLayout activo="Siniestros" rol={rol}>
      <header className="home-header">
        <div>
          <h1>{t("siniestrosPage.mis_siniestros")}</h1>
          <p>{t("siniestrosPage.consulta_tus_reclamaciones_y_el")}</p>
        </div>
        <button
          type="button"
          className="cotizar-boton-primario"
          onClick={() => navigate("/siniestros/nuevo")}
        >
          {t("siniestrosPage.reportar_siniestro")}
        </button>
      </header>

      {error && <p role="alert" className="home-aviso">{error}</p>}

      <CuentaIndemnizaciones />

      <section aria-label={t("siniestrosPage.lista_de_siniestros")} className="cotizaciones-lista">
        {siniestros === null && !error && (
          <p role="status" className="home-card-vacio">{t("siniestrosPage.cargando_tus_siniestros")}</p>
        )}
        {siniestros?.length === 0 && (
          <div className="home-panel">
            <p className="home-card-vacio">{t("siniestrosPage.aun_no_tienes_siniestros_registrados")}</p>
          </div>
        )}
        {siniestros?.map((siniestro) => {
          const abierto = expandido === siniestro.siniestro_id;
          const poliza = polizaPorId[siniestro.poliza_id];
          const desembolso = desembolsoPorSiniestro[siniestro.siniestro_id];
          return (
            <article key={siniestro.siniestro_id} className="cotizacion-item">
              <button
                type="button"
                className="cotizacion-cabecera"
                aria-expanded={abierto}
                onClick={() => setExpandido(abierto ? null : siniestro.siniestro_id)}
              >
                <span className="cotizar-ramo-icono material-symbols-outlined" aria-hidden="true">
                  error
                </span>
                <span className="cotizacion-cabecera-texto">
                  <strong>{poliza?.nombre_ramo ?? t("siniestrosPage.siniestro")}</strong>
                  <small>{formatearFecha(siniestro.fecha_evento)} · {siniestro.lugar}</small>
                </span>
                <span className="home-chip cotizacion-estado">
                  {ESTADOS[siniestro.estado] ?? siniestro.estado}
                </span>
                <span className="material-symbols-outlined cotizacion-chevron" aria-hidden="true">
                  {abierto ? "expand_less" : "expand_more"}
                </span>
              </button>

              {abierto && (
                <div className="cotizacion-detalle">
                  {poliza && (
                    <div className="cotizar-detalle">
                      <span>{t("siniestrosPage.poliza_afectada")}</span>
                      <strong>{poliza.nombre_ramo}</strong>
                      <small>{poliza.numero_poliza} · {poliza.cobertura_principal}</small>
                    </div>
                  )}

                  {desembolso && <DetalleDesembolso desembolso={desembolso} />}
                  {siniestro.estado === "RECHAZADO" && siniestro.motivo_rechazo && (
                    <div className="cotizar-detalle">
                      <span>{t("siniestrosPage.motivo_del_rechazo")}</span>
                      <strong>{siniestro.motivo_rechazo}</strong>
                    </div>
                  )}

                  <h3 className="cotizacion-subtitulo">{t("siniestrosPage.detalle_del_evento")}</h3>
                  <dl className="cotizacion-datos">
                    <div>
                      <dt>{t("siniestrosPage.fecha_y_hora")}</dt>
                      <dd>{formatearFecha(siniestro.fecha_evento)} · {siniestro.hora_evento}</dd>
                    </div>
                    <div>
                      <dt>{t("siniestrosPage.lugar")}</dt>
                      <dd>{siniestro.lugar}</dd>
                    </div>
                    <div>
                      <dt>{t("siniestrosPage.estimacion_de_danos")}</dt>
                      <dd>{formatearMonto(siniestro.estimacion_danos, siniestro.moneda)}</dd>
                    </div>
                  </dl>

                  <h3 className="cotizacion-subtitulo">{t("siniestrosPage.descripcion")}</h3>
                  <p className="siniestro-descripcion">{siniestro.descripcion}</p>

                  <dl className="cotizacion-datos">
                    <div>
                      <dt>{t("siniestrosPage.numero_de_siniestro")}</dt>
                      <dd>{siniestro.siniestro_id}</dd>
                    </div>
                    <div>
                      <dt>{t("siniestrosPage.registrado")}</dt>
                      <dd>{formatearFecha(siniestro.registrado_en.slice(0, 10))}</dd>
                    </div>
                  </dl>
                </div>
              )}
            </article>
          );
        })}
      </section>
    </AppLayout>
  );
}

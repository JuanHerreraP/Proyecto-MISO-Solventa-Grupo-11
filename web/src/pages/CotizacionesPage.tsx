import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import { listarCotizaciones, obtenerRamos } from "../services/cotizaciones.service";
import type { Cotizacion, DefinicionRamo, RamoSeguro } from "../types/cotizaciones";

import { t, localeActual } from "../i18n";

const ICONO_RAMO: Record<RamoSeguro, string> = {
  VIAJE: "flight_takeoff",
  PROTECCION_DISPOSITIVOS: "devices",
  VIDA: "favorite",
  PARAMETRICO: "thunderstorm",
};

const ESTADOS: Record<string, string> = {
  get VIGENTE() { return t("cotizacionesPage.vigente"); },
  get ACEPTADA() { return t("cotizacionesPage.aceptada"); },
  get EXPIRADA() { return t("cotizacionesPage.expirada"); },
  get CANCELADA() { return t("cotizacionesPage.cancelada"); },
  get BORRADOR() { return t("cotizacionesPage.borrador"); },
};

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString(localeActual(), {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: 0,
  });
}

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString(localeActual(), {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Presenta un valor del formulario de forma legible (booleanos, números, texto). */
function formatearValor(valor: unknown): string {
  if (typeof valor === "boolean") return valor ? t("cotizacionesPage.si") : t("cotizacionesPage.no");
  if (typeof valor === "number") return valor.toLocaleString(localeActual());
  return String(valor);
}

/** La cotización sigue vigente: ni aceptada, ni cancelada, ni con la oferta vencida. */
function puedePagarse(cotizacion: Cotizacion): boolean {
  return (
    cotizacion.estado === "VIGENTE" &&
    (!cotizacion.vigente_hasta || new Date(cotizacion.vigente_hasta) > new Date())
  );
}

export default function CotizacionesPage() {
  const navigate = useNavigate();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [cotizaciones, setCotizaciones] = useState<Cotizacion[] | null>(null);
  const [ramos, setRamos] = useState<DefinicionRamo[]>([]);
  const [error, setError] = useState("");
  const [expandida, setExpandida] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => {
        if (!activo) return;
        setPerfil(datos);
        if (datos.id) {
          listarCotizaciones(datos.id).then(
            (lista) => { if (activo) setCotizaciones(lista); },
            (fallo: Error) => { if (activo) setError(fallo.message); },
          );
        }
      },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    obtenerRamos().then(
      (datos) => { if (activo) setRamos(datos); },
      () => undefined,
    );
    return () => { activo = false; };
  }, [navigate]);

  const rol = perfil?.rol ?? null;

  // Mapa ramo -> (código de campo -> etiqueta legible), para mostrar el formulario.
  const etiquetasPorRamo = useMemo(() => {
    const mapa: Record<string, Record<string, string>> = {};
    for (const definicion of ramos) {
      mapa[definicion.ramo] = Object.fromEntries(
        definicion.campos.map((campo) => [campo.codigo, campo.etiqueta]),
      );
    }
    return mapa;
  }, [ramos]);

  const nombreRamo = (ramo: RamoSeguro) =>
    ramos.find((r) => r.ramo === ramo)?.nombre ?? ramo;

  function alternar(id: string) {
    setExpandida((actual) => (actual === id ? null : id));
  }

  return (
    <AppLayout activo="Mis cotizaciones" rol={rol}>
      <header className="home-header">
        <div>
          <h1>{t("cotizacionesPage.mis_cotizaciones")}</h1>
          <p>{t("cotizacionesPage.consulta_tus_cotizaciones_y_el")}</p>
        </div>
        <button
          type="button"
          className="cotizar-boton-primario"
          onClick={() => navigate("/cotizar")}
        >
          {t("cotizacionesPage.crear_cotizacion")}
        </button>
      </header>

      {error && <p role="alert" className="home-aviso">{error}</p>}

      <section aria-label={t("cotizacionesPage.lista_de_cotizaciones")} className="cotizaciones-lista">
        {cotizaciones === null && !error && (
          <p role="status" className="home-card-vacio">{t("cotizacionesPage.cargando_tus_cotizaciones")}</p>
        )}
        {cotizaciones?.length === 0 && (
          <div className="home-panel">
            <p className="home-card-vacio">{t("cotizacionesPage.aun_no_tienes_cotizaciones")}</p>
          </div>
        )}
        {cotizaciones?.map((cotizacion) => {
          const abierta = expandida === cotizacion.cotizacion_id;
          const etiquetas = etiquetasPorRamo[cotizacion.ramo] ?? {};
          const datos = Object.entries(cotizacion.datos_riesgo ?? {});
          return (
            <article key={cotizacion.cotizacion_id} className="cotizacion-item">
              <button
                type="button"
                className="cotizacion-cabecera"
                aria-expanded={abierta}
                onClick={() => alternar(cotizacion.cotizacion_id)}
              >
                <span className="cotizar-ramo-icono material-symbols-outlined" aria-hidden="true">
                  {ICONO_RAMO[cotizacion.ramo]}
                </span>
                <span className="cotizacion-cabecera-texto">
                  <strong>{nombreRamo(cotizacion.ramo)}</strong>
                  <small>
                    {cotizacion.prima_total
                      ? formatearMonto(cotizacion.prima_total, cotizacion.moneda)
                      : "—"}
                  </small>
                </span>
                <span className={`home-chip ${abierta ? "" : ""} cotizacion-estado`}>
                  {ESTADOS[cotizacion.estado] ?? cotizacion.estado}
                </span>
                <span className="material-symbols-outlined cotizacion-chevron" aria-hidden="true">
                  {abierta ? "expand_less" : "expand_more"}
                </span>
              </button>

              {abierta && (
                <div className="cotizacion-detalle">
                  {cotizacion.cobertura_principal && (
                    <div className="cotizar-detalle">
                      <span>{t("cotizacionesPage.cobertura_principal")}</span>
                      <strong>{cotizacion.cobertura_principal.nombre}</strong>
                      <small>
                        {t("cotizacionesPage.suma_asegurada_formatearmonto", { formatearMonto: formatearMonto(
                          cotizacion.cobertura_principal.suma_asegurada,
                          cotizacion.moneda,
                        ) })}
                      </small>
                    </div>
                  )}

                  <h3 className="cotizacion-subtitulo">{t("cotizacionesPage.datos_de_la_solicitud")}</h3>
                  <dl className="cotizacion-datos">
                    {datos.map(([codigo, valor]) => (
                      <div key={codigo}>
                        <dt>{etiquetas[codigo] ?? codigo}</dt>
                        <dd>{formatearValor(valor)}</dd>
                      </div>
                    ))}
                    {datos.length === 0 && (
                      <p className="home-card-vacio">{t("cotizacionesPage.sin_datos_registrados")}</p>
                    )}
                  </dl>

                  {puedePagarse(cotizacion) && (
                    <button
                      type="button"
                      className="cotizar-boton-primario"
                      onClick={() =>
                        navigate(`/cotizar?cotizacion=${encodeURIComponent(cotizacion.cotizacion_id)}`)
                      }
                    >
                      {t("cotizacionesPage.pagar")}
                    </button>
                  )}

                  <dl className="cotizacion-datos">
                    {cotizacion.vigente_hasta && (
                      <div>
                        <dt>{t("cotizacionesPage.vigencia_de_la_oferta")}</dt>
                        <dd>{t("cotizacionesPage.hasta_el_formatearfecha", { formatearFecha: formatearFecha(cotizacion.vigente_hasta) })}</dd>
                      </div>
                    )}
                    <div>
                      <dt>{t("cotizacionesPage.creada")}</dt>
                      <dd>{formatearFecha(cotizacion.creada_en)}</dd>
                    </div>
                    <div>
                      <dt>{t("cotizacionesPage.referencia")}</dt>
                      <dd>{cotizacion.cotizacion_id}</dd>
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

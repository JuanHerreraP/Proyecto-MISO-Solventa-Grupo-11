import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import { obtenerBilletera, type PolizaResumen } from "../services/billetera.service";
import { listarSiniestros } from "../services/siniestros.service";
import type { EstadoSiniestro, Siniestro } from "../types/siniestros";

const ESTADOS: Record<EstadoSiniestro, string> = {
  REGISTRADO: "Registrado",
  EN_EVALUACION: "En evaluación",
  APROBADO: "Aprobado",
  RECHAZADO: "Rechazado",
};

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString("es-CO", {
    day: "numeric", month: "long", year: "numeric",
  });
}

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString("es-CO", {
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

  return (
    <AppLayout activo="Siniestros" rol={rol}>
      <header className="home-header">
        <div>
          <h1>Mis siniestros</h1>
          <p>Consulta tus reclamaciones y el detalle de cada una.</p>
        </div>
        <button
          type="button"
          className="cotizar-boton-primario"
          onClick={() => navigate("/siniestros/nuevo")}
        >
          Reportar siniestro
        </button>
      </header>

      {error && <p role="alert" className="home-aviso">{error}</p>}

      <section aria-label="Lista de siniestros" className="cotizaciones-lista">
        {siniestros === null && !error && (
          <p role="status" className="home-card-vacio">Cargando tus siniestros…</p>
        )}
        {siniestros?.length === 0 && (
          <div className="home-panel">
            <p className="home-card-vacio">Aún no tienes siniestros registrados.</p>
          </div>
        )}
        {siniestros?.map((siniestro) => {
          const abierto = expandido === siniestro.siniestro_id;
          const poliza = polizaPorId[siniestro.poliza_id];
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
                  <strong>{poliza?.nombre_ramo ?? "Siniestro"}</strong>
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
                      <span>Póliza afectada</span>
                      <strong>{poliza.nombre_ramo}</strong>
                      <small>{poliza.numero_poliza} · {poliza.cobertura_principal}</small>
                    </div>
                  )}

                  <h3 className="cotizacion-subtitulo">Detalle del evento</h3>
                  <dl className="cotizacion-datos">
                    <div>
                      <dt>Fecha y hora</dt>
                      <dd>{formatearFecha(siniestro.fecha_evento)} · {siniestro.hora_evento}</dd>
                    </div>
                    <div>
                      <dt>Lugar</dt>
                      <dd>{siniestro.lugar}</dd>
                    </div>
                    <div>
                      <dt>Estimación de daños</dt>
                      <dd>{formatearMonto(siniestro.estimacion_danos, siniestro.moneda)}</dd>
                    </div>
                  </dl>

                  <h3 className="cotizacion-subtitulo">Descripción</h3>
                  <p className="siniestro-descripcion">{siniestro.descripcion}</p>

                  <dl className="cotizacion-datos">
                    <div>
                      <dt>Número de siniestro</dt>
                      <dd>{siniestro.siniestro_id}</dd>
                    </div>
                    <div>
                      <dt>Registrado</dt>
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

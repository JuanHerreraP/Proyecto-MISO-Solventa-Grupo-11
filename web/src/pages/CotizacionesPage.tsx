import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import { listarCotizaciones, obtenerRamos } from "../services/cotizaciones.service";
import type { Cotizacion, DefinicionRamo, RamoSeguro } from "../types/cotizaciones";

const ICONO_RAMO: Record<RamoSeguro, string> = {
  VIAJE: "flight_takeoff",
  PROTECCION_DISPOSITIVOS: "devices",
  VIDA: "favorite",
  PARAMETRICO: "thunderstorm",
};

const ESTADOS: Record<string, string> = {
  VIGENTE: "Vigente",
  ACEPTADA: "Aceptada",
  EXPIRADA: "Expirada",
  CANCELADA: "Cancelada",
  BORRADOR: "Borrador",
};

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString("es-CO", {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: 0,
  });
}

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Presenta un valor del formulario de forma legible (booleanos, números, texto). */
function formatearValor(valor: unknown): string {
  if (typeof valor === "boolean") return valor ? "Sí" : "No";
  if (typeof valor === "number") return valor.toLocaleString("es-CO");
  return String(valor);
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
          <h1>Mis cotizaciones</h1>
          <p>Consulta tus cotizaciones y el detalle de cada una.</p>
        </div>
        <button
          type="button"
          className="cotizar-boton-primario"
          onClick={() => navigate("/cotizar")}
        >
          Crear cotización
        </button>
      </header>

      {error && <p role="alert" className="home-aviso">{error}</p>}

      <section aria-label="Lista de cotizaciones" className="cotizaciones-lista">
        {cotizaciones === null && !error && (
          <p role="status" className="home-card-vacio">Cargando tus cotizaciones…</p>
        )}
        {cotizaciones?.length === 0 && (
          <div className="home-panel">
            <p className="home-card-vacio">Aún no tienes cotizaciones.</p>
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
                      <span>Cobertura principal</span>
                      <strong>{cotizacion.cobertura_principal.nombre}</strong>
                      <small>
                        Suma asegurada:{" "}
                        {formatearMonto(
                          cotizacion.cobertura_principal.suma_asegurada,
                          cotizacion.moneda,
                        )}
                      </small>
                    </div>
                  )}

                  <h3 className="cotizacion-subtitulo">Datos de la solicitud</h3>
                  <dl className="cotizacion-datos">
                    {datos.map(([codigo, valor]) => (
                      <div key={codigo}>
                        <dt>{etiquetas[codigo] ?? codigo}</dt>
                        <dd>{formatearValor(valor)}</dd>
                      </div>
                    ))}
                    {datos.length === 0 && (
                      <p className="home-card-vacio">Sin datos registrados.</p>
                    )}
                  </dl>

                  <dl className="cotizacion-datos">
                    {cotizacion.vigente_hasta && (
                      <div>
                        <dt>Vigencia de la oferta</dt>
                        <dd>Hasta el {formatearFecha(cotizacion.vigente_hasta)}</dd>
                      </div>
                    )}
                    <div>
                      <dt>Creada</dt>
                      <dd>{formatearFecha(cotizacion.creada_en)}</dd>
                    </div>
                    <div>
                      <dt>Referencia</dt>
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

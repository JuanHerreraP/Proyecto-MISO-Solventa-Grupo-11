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
  EMISION: "Emisión de póliza",
  PAGO_PRIMA_INICIAL: "Pago de prima inicial",
  ENDOSO: "Modificación contractual",
  RENOVACION: "Renovación",
  CANCELACION: "Cancelación",
  DESEMBOLSO_INDEMNIZACION: "Pago de indemnización",
  REEMBOLSO: "Reembolso",
};

const ETIQUETA_CATEGORIA: Record<CategoriaMovimiento, string> = {
  FINANCIERO: "Movimiento financiero",
  CONTRACTUAL: "Movimiento contractual",
  POLIZA: "Póliza",
};

function formatearFechaHora(iso: string): string {
  const fecha = new Date(iso);
  return fecha.toLocaleString("es-CO", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** El monto siempre es positivo; el signo mostrado depende de la naturaleza del movimiento. */
function formatearMonto(monto: string, moneda: string | null, naturaleza: NaturalezaMonto | null): string {
  const valor = Number(monto).toLocaleString("es-CO", {
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
          <h1>Historial de movimientos</h1>
          {historial && <p>{historial.numero_poliza}</p>}
        </div>
        <button type="button" className="cotizar-boton-secundario" onClick={() => navigate("/polizas")}>
          Volver a mis pólizas
        </button>
      </header>

      {error && (
        <div className="home-panel">
          <p role="alert" className="home-aviso">{error}</p>
          <button type="button" className="cotizar-boton-primario" onClick={() => reintentar()}>
            Reintentar
          </button>
        </div>
      )}

      {cargando && !error && (
        <p role="status" className="home-card-vacio">Cargando historial…</p>
      )}

      {!cargando && !error && movimientos.length === 0 && (
        <div className="home-panel">
          <p className="home-card-vacio">
            Todavía no hay movimientos registrados para esta póliza.
          </p>
        </div>
      )}

      {!cargando && !error && movimientos.length > 0 && (
        <section aria-label="Historial de movimientos" className="cotizaciones-lista">
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
              <dt>{movimiento.naturaleza_monto === "AJUSTE" ? "Ajuste de prima" : "Monto"}</dt>
              <dd>{formatearMonto(movimiento.monto, movimiento.moneda, movimiento.naturaleza_monto)}</dd>
            </div>
          )}
          {movimiento.referencia && (
            <div>
              <dt>Referencia</dt>
              <dd>{movimiento.referencia}</dd>
            </div>
          )}
          {movimiento.categoria === "FINANCIERO" && (
            <div>
              <dt>Referencia de pasarela</dt>
              <dd>{movimiento.referencia_externa ?? "Sin referencia externa"}</dd>
            </div>
          )}
        </dl>

        {movimiento.consentimiento?.explicito && (
          <p className="historial-consentimiento">
            <span className="material-symbols-outlined" aria-hidden="true">check_circle</span>
            Consentimiento: confirmado por el cliente
          </p>
        )}

        {tieneDetalle && (
          <button
            type="button"
            className="cotizar-boton-secundario"
            aria-expanded={abierto}
            onClick={onAlternar}
          >
            {abierto ? "Ocultar detalle" : "Ver detalle"}
          </button>
        )}

        {abierto && movimiento.cambios.length > 0 && (
          <div className="historial-cambios">
            <h3 className="cotizacion-subtitulo">Cambios</h3>
            {movimiento.cambios.map((cambio, indice) => (
              <div key={`${movimiento.movimiento_id}-${indice}`} className="historial-cambio">
                <strong>{cambio.descripcion}</strong>
                <div className="historial-linaje">
                  <div>
                    <span className="historial-linaje-rotulo">Antes</span>
                    {entradasLinaje(cambio.antes).length === 0 ? (
                      <small>—</small>
                    ) : (
                      entradasLinaje(cambio.antes).map(([campo, valor]) => (
                        <small key={`antes-${campo}`}>{campo}: {valor}</small>
                      ))
                    )}
                  </div>
                  <div>
                    <span className="historial-linaje-rotulo">Después</span>
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

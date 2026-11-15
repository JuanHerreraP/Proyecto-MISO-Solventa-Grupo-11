import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
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

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString("es-CO", {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: 0,
  });
}

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString("es-CO", {
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
  const puedeConfirmar = Boolean(
    condiciones?.cancelable && motivo && confirmado && !detalleRequerido && !procesando,
  );

  return (
    <AppLayout activo="Mis pólizas" rol={perfil?.rol ?? null}>
      <header className="home-header">
        <div>
          <h1>Cancelar póliza</h1>
          <p>{condiciones?.numero_poliza ?? "Consulta las condiciones antes de continuar."}</p>
        </div>
        <button
          type="button"
          className="cotizar-boton-secundario"
          onClick={() => navigate("/polizas")}
        >
          Volver a mis pólizas
        </button>
      </header>

      {cargando && <p role="status" className="home-card-vacio">Calculando condiciones…</p>}
      {error && <p role="alert" className="home-aviso">{error}</p>}

      {cancelacion && (
        <section className="home-panel cancelacion-resultado" aria-label="Póliza cancelada">
          <span className="material-symbols-outlined" aria-hidden="true">check_circle</span>
          <div>
            <h2>Póliza cancelada</h2>
            <p>La cancelación rige desde el {formatearFecha(cancelacion.fecha_efecto)}.</p>
            <strong>
              {cancelacion.saldo_estimado === "0.00"
                ? "No hay saldo pendiente de devolución."
                : `Saldo estimado a devolver: ${formatearMonto(cancelacion.saldo_estimado, cancelacion.moneda)}`}
            </strong>
          </div>
        </section>
      )}

      {condiciones && !cancelacion && !condiciones.cancelable && (
        <section className="home-panel cancelacion-bloqueada" aria-labelledby="cancelacion-no-disponible">
          <h2 id="cancelacion-no-disponible">Esta póliza no se puede cancelar</h2>
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
            <h2 id="resumen-cancelacion">Liquidación estimada</h2>
            <dl className="cotizacion-datos">
              <div><dt>Prima pagada</dt><dd>{formatearMonto(condiciones.prima_total, condiciones.moneda)}</dd></div>
              <div><dt>Días de cobertura sin usar</dt><dd>{condiciones.dias_no_transcurridos}</dd></div>
              <div className="cancelacion-saldo">
                <dt>Saldo estimado a devolver</dt>
                <dd>{formatearMonto(condiciones.saldo_estimado, condiciones.moneda)}</dd>
              </div>
            </dl>
            <small>El valor definitivo se gestionará como devolución después de confirmar.</small>
          </section>

          <section className="home-panel cancelacion-formulario" aria-labelledby="motivo-cancelacion">
            <h2 id="motivo-cancelacion">Motivo de cancelación</h2>
            <div className="cotizar-campo">
              <label htmlFor="motivo">Selecciona un motivo</label>
              <select
                id="motivo"
                value={motivo}
                onChange={(evento) => {
                  setMotivo(evento.target.value as MotivoCancelacion | "");
                  setConfirmado(false);
                }}
              >
                <option value="">Selecciona una opción</option>
                {condiciones.motivos.map((opcion) => (
                  <option key={opcion.codigo} value={opcion.codigo}>{opcion.etiqueta}</option>
                ))}
              </select>
            </div>

            <div className="cotizar-campo">
              <label htmlFor="detalle">Cuéntanos más {motivo === "OTRO" ? "(obligatorio)" : "(opcional)"}</label>
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

            <h3>Ten en cuenta</h3>
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
              Confirmo que quiero cancelar esta póliza de forma definitiva.
            </label>

            <div className="cotizar-acciones">
              <button
                type="button"
                className="cotizar-boton-secundario"
                onClick={() => navigate("/polizas")}
              >
                Conservar mi póliza
              </button>
              <button
                type="button"
                className="poliza-boton-cancelar poliza-boton-cancelar-solido"
                disabled={!puedeConfirmar}
                onClick={() => void cancelar()}
              >
                {procesando ? "Cancelando…" : "Confirmar cancelación"}
              </button>
            </div>
          </section>
        </div>
      )}
    </AppLayout>
  );
}

import { useEffect, useState, type FormEvent } from "react";
import {
  configurarRenovacionAutomatica,
  consultarRenovacionAutomatica,
  descargarDocumentoRenovacion,
  type CicloRenovacion,
  type RenovacionAutomatica as Estado,
  type SolicitudRenovacionAutomatica,
} from "../../services/renovacion-automatica.service";
import {
  formatearNumeroTarjeta,
  formatearVencimiento,
  tokenizarTarjeta,
  ultimosDigitos,
} from "../../services/tokenizacion";
import "../../styles/renovacion-automatica.css";

interface Props {
  polizaId: string;
  /** Solo el cliente titular registra o quita su tarjeta; el asesor solo activa o desactiva. */
  puedeRegistrarTarjeta: boolean;
}

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString("es-CO", {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: 0,
  });
}

function describirCiclo(ciclo: CicloRenovacion): string {
  const vence = formatearFecha(ciclo.vence_el);
  switch (ciclo.estado) {
    case "PREAVISADA":
      return ciclo.prima_avisada && ciclo.moneda
        ? `Te enviamos el preaviso: la renovación costará ${formatearMonto(ciclo.prima_avisada, ciclo.moneda)}.`
        : "Te enviamos el preaviso de la renovación.";
    case "RENOVADA":
      return `Tu póliza se renovó automáticamente al terminar la vigencia del ${vence}.`;
    case "DESACTIVADA":
      return `No se renovó el ${vence} porque la renovación automática estaba desactivada.`;
    case "SIN_MEDIO_DE_PAGO":
      return "No pudimos renovarla: no había una tarjeta registrada. Registra una o paga la renovación en Pagos.";
    case "COBRO_RECHAZADO":
      return "La tarjeta fue rechazada. Registra otra tarjeta o paga la renovación en Pagos.";
    case "COBRO_PENDIENTE":
      return "Estamos esperando la confirmación del pago de la renovación.";
    case "NO_PAGADA":
      return "La renovación venció sin un pago aprobado.";
    case "NO_RENOVABLE":
    case "NO_APLICADA":
      return ciclo.motivo ?? "La póliza no se pudo renovar automáticamente.";
  }
}

export default function RenovacionAutomatica({ polizaId, puedeRegistrarTarjeta }: Props) {
  const [estado, setEstado] = useState<Estado | null>(null);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [editandoTarjeta, setEditandoTarjeta] = useState(false);
  const [numero, setNumero] = useState("");
  const [vencimiento, setVencimiento] = useState("");
  const [cvv, setCvv] = useState("");

  useEffect(() => {
    let activo = true;
    consultarRenovacionAutomatica(polizaId).then(
      (datos) => { if (activo) setEstado(datos); },
      (fallo: Error) => { if (activo) setError(fallo.message); },
    );
    return () => { activo = false; };
  }, [polizaId]);

  async function guardar(solicitud: SolicitudRenovacionAutomatica, exito: string) {
    setGuardando(true);
    setError("");
    setMensaje("");
    try {
      setEstado(await configurarRenovacionAutomatica(polizaId, solicitud));
      setMensaje(exito);
      return true;
    } catch (fallo) {
      setError((fallo as Error).message);
      return false;
    } finally {
      setGuardando(false);
    }
  }

  async function registrarTarjeta(evento: FormEvent) {
    evento.preventDefault();
    if (!estado) return;
    const ok = await guardar(
      {
        activa: estado.activa,
        tarjeta: { token_tarjeta: tokenizarTarjeta(numero), ultimos_digitos: ultimosDigitos(numero) },
      },
      "Guardamos tu tarjeta para la renovación automática.",
    );
    if (ok) {
      setEditandoTarjeta(false);
      setNumero("");
      setVencimiento("");
      setCvv("");
    }
  }

  async function descargar(renovacionId: string) {
    setError("");
    try {
      await descargarDocumentoRenovacion(polizaId, renovacionId);
    } catch (fallo) {
      setError((fallo as Error).message);
    }
  }

  if (!estado) {
    return error
      ? <p role="alert" className="home-aviso">{error}</p>
      : <p role="status" className="home-card-vacio">Cargando renovación automática…</p>;
  }
  if (!estado.disponible) return null;

  const tarjeta = estado.tarjeta;
  const ciclo = estado.ultimo_ciclo;
  const tituloId = `renovacion-auto-${polizaId}`;

  return (
    <section className="renovacion-auto" aria-labelledby={tituloId}>
      <div className="renovacion-auto-cabecera">
        <span className="material-symbols-outlined renovacion-auto-icono" aria-hidden="true">autorenew</span>
        <div>
          <h3 id={tituloId}>Renovación automática</h3>
          <p>
            {estado.activa
              ? `Tu póliza se renovará el ${formatearFecha(estado.cobro_programado_para)} con la tarjeta registrada. Te avisaremos el precio desde el ${formatearFecha(estado.preaviso_desde)}.`
              : "Está desactivada: cuando se acerque el vencimiento deberás renovar tu póliza manualmente."}
          </p>
        </div>
        <label className="renovacion-auto-interruptor">
          <input
            type="checkbox"
            role="switch"
            checked={estado.activa}
            disabled={guardando}
            aria-label="Renovar automáticamente"
            onChange={(evento) => {
              const activa = evento.target.checked;
              void guardar(
                { activa },
                activa ? "Activaste la renovación automática." : "Desactivaste la renovación automática.",
              );
            }}
          />
          <span aria-hidden="true" />
        </label>
      </div>

      <dl className="cotizacion-datos">
        <div>
          <dt>Tarjeta para el cobro</dt>
          <dd>
            {tarjeta
              ? `Terminada en ${tarjeta.ultimos_digitos ?? "****"}`
              : "Sin tarjeta registrada"}
          </dd>
        </div>
        <div>
          <dt>Cobro programado</dt>
          <dd>{formatearFecha(estado.cobro_programado_para)}</dd>
        </div>
      </dl>

      {estado.activa && !tarjeta && (
        <p className="renovacion-auto-alerta">
          Registra una tarjeta para que podamos renovar tu póliza sin que tengas que hacer nada.
        </p>
      )}

      {puedeRegistrarTarjeta && !editandoTarjeta && (
        <div className="poliza-acciones">
          <button
            type="button"
            className="cotizar-boton-secundario"
            onClick={() => setEditandoTarjeta(true)}
          >
            <span className="material-symbols-outlined" aria-hidden="true">credit_card</span>
            {tarjeta ? "Cambiar tarjeta" : "Registrar tarjeta"}
          </button>
          {tarjeta && (
            <button
              type="button"
              className="cotizar-boton-secundario"
              disabled={guardando}
              onClick={() => void guardar(
                { activa: estado.activa, quitar_tarjeta: true },
                "Quitamos la tarjeta registrada.",
              )}
            >
              Quitar tarjeta
            </button>
          )}
        </div>
      )}

      {puedeRegistrarTarjeta && editandoTarjeta && (
        <form className="renovacion-auto-tarjeta" onSubmit={(evento) => void registrarTarjeta(evento)}>
          <div className="cotizar-campo cotizar-campo-ancho">
            <label htmlFor={`numero-${polizaId}`}>Número de tarjeta</label>
            <input
              id={`numero-${polizaId}`}
              type="text"
              inputMode="numeric"
              autoComplete="cc-number"
              placeholder="4111 1111 1111 1111"
              required
              pattern="[0-9 ]{15,19}"
              value={numero}
              onChange={(evento) => setNumero(formatearNumeroTarjeta(evento.target.value))}
            />
            <small className="cotizar-ayuda">
              Los datos de la tarjeta se tokenizan y no se envían al servidor.
            </small>
          </div>
          <div className="cotizar-campo">
            <label htmlFor={`vencimiento-${polizaId}`}>Vencimiento (MM/AA)</label>
            <input
              id={`vencimiento-${polizaId}`}
              type="text"
              inputMode="numeric"
              autoComplete="cc-exp"
              placeholder="08/29"
              required
              value={vencimiento}
              onChange={(evento) => setVencimiento(formatearVencimiento(evento.target.value))}
            />
          </div>
          <div className="cotizar-campo">
            <label htmlFor={`cvv-${polizaId}`}>CVV</label>
            <input
              id={`cvv-${polizaId}`}
              type="text"
              inputMode="numeric"
              autoComplete="cc-csc"
              placeholder="123"
              maxLength={4}
              required
              value={cvv}
              onChange={(evento) => setCvv(evento.target.value.replace(/\D/g, "").slice(0, 4))}
            />
          </div>
          <div className="poliza-acciones">
            <button type="submit" className="cotizar-boton-primario" disabled={guardando}>
              {guardando ? "Guardando…" : "Guardar tarjeta"}
            </button>
            <button
              type="button"
              className="cotizar-boton-secundario"
              onClick={() => setEditandoTarjeta(false)}
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {ciclo && (
        <div className={`renovacion-auto-ciclo renovacion-auto-ciclo-${ciclo.estado.toLowerCase()}`}>
          <p>{describirCiclo(ciclo)}</p>
          {ciclo.documento_disponible && ciclo.renovacion_id && (
            <button
              type="button"
              className="cotizar-boton-secundario"
              onClick={() => void descargar(ciclo.renovacion_id as string)}
            >
              <span className="material-symbols-outlined" aria-hidden="true">download</span>
              Descargar renovación (PDF)
            </button>
          )}
        </div>
      )}

      {mensaje && <p role="status" className="renovacion-auto-mensaje">{mensaje}</p>}
      {error && <p role="alert" className="home-aviso">{error}</p>}
    </section>
  );
}

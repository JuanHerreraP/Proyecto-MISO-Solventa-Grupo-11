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

import { t, localeActual } from "../../i18n";

interface Props {
  polizaId: string;
  /** Solo el cliente titular registra o quita su tarjeta; el asesor solo activa o desactiva. */
  puedeRegistrarTarjeta: boolean;
}

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString(localeActual(), {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString(localeActual(), {
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
        ? t("renovacionAutomatica.te_enviamos_el_preaviso_la", { formatearMonto: formatearMonto(ciclo.prima_avisada, ciclo.moneda) })
        : t("renovacionAutomatica.te_enviamos_el_preaviso_de");
    case "RENOVADA":
      return t("renovacionAutomatica.tu_poliza_se_renovo_automaticamente", { vence: vence });
    case "DESACTIVADA":
      return t("renovacionAutomatica.no_se_renovo_el_vence", { vence: vence });
    case "SIN_MEDIO_DE_PAGO":
      return t("renovacionAutomatica.no_pudimos_renovarla_no_habia");
    case "COBRO_RECHAZADO":
      return t("renovacionAutomatica.la_tarjeta_fue_rechazada_registra");
    case "COBRO_PENDIENTE":
      return t("renovacionAutomatica.estamos_esperando_la_confirmacion_del");
    case "NO_PAGADA":
      return t("renovacionAutomatica.la_renovacion_vencio_sin_un");
    case "NO_RENOVABLE":
    case "NO_APLICADA":
      return ciclo.motivo ?? t("renovacionAutomatica.la_poliza_no_se_pudo");
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
      t("renovacionAutomatica.guardamos_tu_tarjeta_para_la"),
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
      : <p role="status" className="home-card-vacio">{t("renovacionAutomatica.cargando_renovacion_automatica")}</p>;
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
          <h3 id={tituloId}>{t("renovacionAutomatica.renovacion_automatica")}</h3>
          <p>
            {estado.activa
              ? t("renovacionAutomatica.tu_poliza_se_renovara_el", { formatearFecha: formatearFecha(estado.cobro_programado_para), formatearFecha2: formatearFecha(estado.preaviso_desde) })
              : t("renovacionAutomatica.esta_desactivada_cuando_se_acerque")}
          </p>
        </div>
        <label className="renovacion-auto-interruptor">
          <input
            type="checkbox"
            role="switch"
            checked={estado.activa}
            disabled={guardando}
            aria-label={t("renovacionAutomatica.renovar_automaticamente")}
            onChange={(evento) => {
              const activa = evento.target.checked;
              void guardar(
                { activa },
                activa ? t("renovacionAutomatica.activaste_la_renovacion_automatica") : t("renovacionAutomatica.desactivaste_la_renovacion_automatica"),
              );
            }}
          />
          <span aria-hidden="true" />
        </label>
      </div>

      <dl className="cotizacion-datos">
        <div>
          <dt>{t("renovacionAutomatica.tarjeta_para_el_cobro")}</dt>
          <dd>
            {tarjeta
              ? t("renovacionAutomatica.terminada_en_valor", { valor: tarjeta.ultimos_digitos ?? "****" })
              : t("renovacionAutomatica.sin_tarjeta_registrada")}
          </dd>
        </div>
        <div>
          <dt>{t("renovacionAutomatica.cobro_programado")}</dt>
          <dd>{formatearFecha(estado.cobro_programado_para)}</dd>
        </div>
      </dl>

      {estado.activa && !tarjeta && (
        <p className="renovacion-auto-alerta">
          {t("renovacionAutomatica.registra_una_tarjeta_para_que")}
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
            {tarjeta ? t("renovacionAutomatica.cambiar_tarjeta") : t("renovacionAutomatica.registrar_tarjeta")}
          </button>
          {tarjeta && (
            <button
              type="button"
              className="cotizar-boton-secundario"
              disabled={guardando}
              onClick={() => void guardar(
                { activa: estado.activa, quitar_tarjeta: true },
                t("renovacionAutomatica.quitamos_la_tarjeta_registrada"),
              )}
            >
              {t("renovacionAutomatica.quitar_tarjeta")}
            </button>
          )}
        </div>
      )}

      {puedeRegistrarTarjeta && editandoTarjeta && (
        <form className="renovacion-auto-tarjeta" onSubmit={(evento) => void registrarTarjeta(evento)}>
          <div className="cotizar-campo cotizar-campo-ancho">
            <label htmlFor={`numero-${polizaId}`}>{t("renovacionAutomatica.numero_de_tarjeta")}</label>
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
              {t("renovacionAutomatica.los_datos_de_la_tarjeta")}
            </small>
          </div>
          <div className="cotizar-campo">
            <label htmlFor={`vencimiento-${polizaId}`}>{t("renovacionAutomatica.vencimiento_mm_aa")}</label>
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
              {guardando ? t("renovacionAutomatica.guardando") : t("renovacionAutomatica.guardar_tarjeta")}
            </button>
            <button
              type="button"
              className="cotizar-boton-secundario"
              onClick={() => setEditandoTarjeta(false)}
            >
              {t("renovacionAutomatica.cancelar")}
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
              {t("renovacionAutomatica.descargar_renovacion_pdf")}
            </button>
          )}
        </div>
      )}

      {mensaje && <p role="status" className="renovacion-auto-mensaje">{mensaje}</p>}
      {error && <p role="alert" className="home-aviso">{error}</p>}
    </section>
  );
}

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ErrorFirma,
  firmarContrato,
  obtenerContrato,
  solicitarCodigo,
  type CanalOtp,
  type ProcesoFirma,
} from "../services/firma.service";
import "../styles/firma.css";

const PASOS = ["Consentimiento", "Perfil de riesgo", "Cotización", "Pago y firma", "Póliza emitida"];
const PASO_ACTUAL = 3;

function moneda(valor: string, codigo: string): string {
  return Number(valor).toLocaleString("es-CO", {
    style: "currency", currency: codigo, maximumFractionDigits: 0,
  });
}

function fechaHora(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function etiqueta(campo: string): string {
  const texto = campo.replaceAll("_", " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function valorRiesgo(valor: unknown): string {
  if (typeof valor === "number") return valor.toLocaleString("es-CO");
  if (typeof valor === "boolean") return valor ? "Sí" : "No";
  if (valor === null || valor === undefined) return "—";
  return typeof valor === "object" ? JSON.stringify(valor) : String(valor);
}

function segundosHasta(iso: string | null, ahora: number): number {
  if (!iso) return 0;
  return Math.max(0, Math.ceil((new Date(iso).getTime() - ahora) / 1000));
}

function Pasos() {
  return (
    <header className="firma-barra">
      <div className="firma-marca">
        <span className="material-symbols-outlined" aria-hidden="true">shield</span>
        Solventa
      </div>
      <ol className="firma-pasos" aria-label="Progreso de la compra">
      {PASOS.map((paso, indice) => (
        <li
          key={paso}
          className={indice < PASO_ACTUAL ? "hecho" : indice === PASO_ACTUAL ? "actual" : ""}
          aria-current={indice === PASO_ACTUAL ? "step" : undefined}
        >
          <span className="firma-paso-numero">{indice < PASO_ACTUAL ? "✓" : indice + 1}</span>
          {paso}
        </li>
      ))}
      </ol>
    </header>
  );
}

function Fila({ t, children }: { t: string; children: ReactNode }) {
  return <div className="firma-fila"><dt>{t}</dt><dd>{children}</dd></div>;
}

function Contrato({ proceso }: { proceso: ProcesoFirma }) {
  const { contrato } = proceso;
  const riesgo = Object.entries(contrato.datos_riesgo);
  return (
    <article className="firma-documento" aria-labelledby="titulo-contrato">
      <header>
        <h2 id="titulo-contrato">Contrato de seguro — condiciones particulares</h2>
        <p>{contrato.nombre_ramo} · Cotización {contrato.cotizacion_id}</p>
      </header>
      <section>
        <h3>Tomador y asegurado</h3>
        <dl>
          <Fila t="Nombre">{contrato.titular.nombre_completo}</Fila>
          <Fila t="Documento">{contrato.titular.tipo_documento} {contrato.titular.numero_documento}</Fila>
          <Fila t="Correo">{contrato.titular.email}</Fila>
        </dl>
      </section>
      <section>
        <h3>Cobertura</h3>
        <dl>
          <Fila t="Amparo principal">{contrato.cobertura_principal.nombre}</Fila>
          <Fila t="Suma asegurada">{moneda(contrato.cobertura_principal.suma_asegurada, contrato.moneda)}</Fila>
          {riesgo.map(([campo, valor]) => (
            <Fila key={campo} t={etiqueta(campo)}>{valorRiesgo(valor)}</Fila>
          ))}
        </dl>
      </section>
      <section>
        <h3>Prima</h3>
        <dl>
          <Fila t="Prima total">{moneda(contrato.prima_total, contrato.moneda)}</Fila>
          <Fila t="Pagada el">{fechaHora(contrato.fecha_pago)}</Fila>
          <Fila t="Referencia del pago">{contrato.referencia_pago ?? contrato.pago_id}</Fila>
        </dl>
      </section>
      <section>
        <h3>Cláusulas</h3>
        <ol className="firma-clausulas">
          {contrato.clausulas.map((clausula) => <li key={clausula}>{clausula}</li>)}
        </ol>
      </section>
      <footer className="firma-huella">
        Huella del documento (SHA-256): <code>{proceso.huella_documento}</code>
      </footer>
    </article>
  );
}

function Resumen({ proceso }: { proceso: ProcesoFirma }) {
  const { contrato } = proceso;
  return (
    <aside className="firma-resumen" aria-label="Resumen">
      <small>Resumen</small>
      <strong>{contrato.nombre_ramo}</strong>
      <p className="firma-resumen-valor">{moneda(contrato.prima_total, contrato.moneda)}</p>
      <dl>
        <Fila t="Suma asegurada">{moneda(contrato.cobertura_principal.suma_asegurada, contrato.moneda)}</Fila>
        <Fila t="Pago"><span className="firma-ok">Aprobado</span></Fila>
        <Fila t="Firma">{proceso.estado === "FIRMADA" ? "Firmada" : proceso.estado === "BLOQUEADA" ? "Bloqueada" : "Pendiente"}</Fila>
      </dl>
    </aside>
  );
}

export default function FirmaPage() {
  const { cotizacionId = "" } = useParams();
  const navigate = useNavigate();
  const [proceso, setProceso] = useState<ProcesoFirma | null>(null);
  const [errorCarga, setErrorCarga] = useState("");
  const [aviso, setAviso] = useState("");
  const [autoriza, setAutoriza] = useState(false);
  const [canal, setCanal] = useState<CanalOtp>("SMS");
  const [codigo, setCodigo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [ahora, setAhora] = useState(() => Date.now());

  useEffect(() => {
    let activo = true;
    obtenerContrato(cotizacionId).then(
      (datos) => { if (activo) setProceso(datos); },
      (fallo: Error) => { if (activo) setErrorCarga(fallo.message); },
    );
    return () => { activo = false; };
  }, [cotizacionId]);

  const espera = segundosHasta(proceso?.reenvio_disponible_en ?? null, ahora);
  useEffect(() => {
    if (espera <= 0) return;
    const reloj = window.setInterval(() => setAhora(Date.now()), 1000);
    return () => window.clearInterval(reloj);
  }, [espera]);

  if (errorCarga) {
    return (
      <div className="firma-pagina">
        <Pasos />
        <main className="firma-contenido">
          <p role="alert" className="firma-alerta">{errorCarga}</p>
          <button type="button" className="firma-boton-secundario" onClick={() => navigate("/pagos")}>
            Volver a pagos
          </button>
        </main>
      </div>
    );
  }
  if (!proceso) return <p role="status">Cargando contrato…</p>;

  const codigoEnviado = proceso.otp_destino !== null && proceso.intentos_restantes > 0;

  async function enviarCodigo() {
    setAviso("");
    setEnviando(true);
    try {
      const actualizado = await solicitarCodigo(cotizacionId, canal);
      setProceso(actualizado);
      setAhora(Date.now());
      setCodigo("");
    } catch (fallo) {
      setAviso((fallo as Error).message);
      if (fallo instanceof ErrorFirma && fallo.codigo === "FIRMA_BLOQUEADA") {
        setProceso({ ...proceso!, estado: "BLOQUEADA" });
      }
    } finally {
      setEnviando(false);
    }
  }

  async function firmar(evento: FormEvent) {
    evento.preventDefault();
    setAviso("");
    setEnviando(true);
    try {
      setProceso(await firmarContrato(cotizacionId, codigo, proceso!.huella_documento));
    } catch (fallo) {
      const error = fallo as Error;
      if (fallo instanceof ErrorFirma) {
        if (fallo.codigo === "FIRMA_BLOQUEADA") setProceso({ ...proceso!, estado: "BLOQUEADA" });
        else if (fallo.intentosRestantes !== undefined) {
          setProceso({ ...proceso!, intentos_restantes: fallo.intentosRestantes });
        }
        const restantes = fallo.codigo === "OTP_INCORRECTO" && fallo.intentosRestantes
          ? ` Te quedan ${fallo.intentosRestantes} intentos.` : "";
        setAviso(error.message + restantes);
      } else {
        setAviso(error.message);
      }
      setCodigo("");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="firma-pagina">
      <Pasos />
      <main className="firma-contenido">
        <div className="firma-principal">
          <header className="firma-encabezado">
            <h1>{proceso.estado === "FIRMADA" ? "Contrato firmado" : "Firma tu contrato"}</h1>
            <p>
              {proceso.estado === "FIRMADA"
                ? "Tu firma quedó registrada. La póliza se emitirá con este contrato."
                : "Revisa las condiciones de tu seguro y fírmalas con el código que te enviamos."}
            </p>
          </header>

          {!proceso.documento_integro && (
            <p role="alert" className="firma-alerta">
              El contrato no coincide con su huella. No lo firmes y comunícate con tu asesor.
            </p>
          )}

          <Contrato proceso={proceso} />

          {proceso.estado === "FIRMADA" && (
            <section className="firma-tarjeta firma-exito" aria-label="Firma registrada">
              <span className="material-symbols-outlined" aria-hidden="true">verified</span>
              <div>
                <strong>Firmado el {fechaHora(proceso.firmado_en!)}</strong>
                <small>Referencia de la firma: {proceso.referencia_proveedor}</small>
              </div>
            </section>
          )}

          {proceso.estado === "BLOQUEADA" && (
            <p role="alert" className="firma-alerta">
              La firma se bloqueó por intentos fallidos. Comunícate con tu asesor para continuar.
            </p>
          )}

          {proceso.estado === "PENDIENTE" && (
            <section className="firma-tarjeta" aria-labelledby="titulo-firma">
              <span className="material-symbols-outlined firma-icono" aria-hidden="true">signature</span>
              <div className="firma-tarjeta-cuerpo">
                <h2 id="titulo-firma">Firma electrónica del contrato</h2>
                <label className="firma-autoriza">
                  <input
                    type="checkbox"
                    checked={autoriza}
                    onChange={(evento) => setAutoriza(evento.target.checked)}
                  />
                  Leí el contrato y autorizo su firma electrónica, con validez legal equivalente a la firma manuscrita.
                </label>

                <fieldset className="firma-canal" disabled={!autoriza || enviando}>
                  <legend>Enviar el código por</legend>
                  <label>
                    <input type="radio" name="canal" checked={canal === "SMS"} onChange={() => setCanal("SMS")} />
                    SMS al celular
                  </label>
                  <label>
                    <input type="radio" name="canal" checked={canal === "EMAIL"} onChange={() => setCanal("EMAIL")} />
                    Correo electrónico
                  </label>
                  <button
                    type="button"
                    className="firma-boton-secundario"
                    onClick={() => void enviarCodigo()}
                    disabled={espera > 0 || proceso.envios_restantes === 0}
                  >
                    {proceso.otp_destino ? "Reenviar código" : "Enviar código"}
                    {espera > 0 && ` (${espera} s)`}
                  </button>
                </fieldset>

                {codigoEnviado && (
                  <form className="firma-codigo" onSubmit={(evento) => void firmar(evento)}>
                    <p role="status">
                      Enviamos un código a {proceso.otp_destino}.
                      {proceso.otp_expira_en && ` Es válido hasta las ${new Date(proceso.otp_expira_en)
                        .toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}`}
                    </p>
                    <label htmlFor="codigo-otp">Código de verificación</label>
                    <input
                      id="codigo-otp"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      maxLength={6}
                      value={codigo}
                      onChange={(evento) => setCodigo(evento.target.value.replace(/\D/g, ""))}
                    />
                    <button
                      type="submit"
                      className="firma-boton-primario"
                      disabled={codigo.length !== 6 || enviando || !proceso.documento_integro}
                    >
                      Firmar contrato
                      <span className="material-symbols-outlined" aria-hidden="true">arrow_forward</span>
                    </button>
                  </form>
                )}
                {aviso && <p role="alert" className="firma-alerta">{aviso}</p>}
              </div>
            </section>
          )}

          <nav className="firma-acciones">
            <button type="button" className="firma-volver" onClick={() => navigate("/pagos")}>
              <span className="material-symbols-outlined" aria-hidden="true">arrow_back</span>
              Volver a pagos
            </button>
          </nav>
        </div>
        <Resumen proceso={proceso} />
      </main>
    </div>
  );
}

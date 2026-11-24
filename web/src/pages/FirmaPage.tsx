import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil } from "../services/auth.service";
import {
  ErrorFirma,
  firmarContrato,
  obtenerContrato,
  solicitarCodigo,
  type CanalOtp,
  type ProcesoFirma,
} from "../services/firma.service";
import { descargarDocumentoPoliza } from "../services/poliza-documento.service";
import "../styles/firma.css";

import { localeActual, t } from "../i18n";

function moneda(valor: string, codigo: string): string {
  return Number(valor).toLocaleString(localeActual(), {
    style: "currency", currency: codigo, maximumFractionDigits: 0,
  });
}

function fechaHora(iso: string): string {
  return new Date(iso).toLocaleString(localeActual(), {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function etiqueta(campo: string): string {
  const texto = campo.replaceAll("_", " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function valorRiesgo(valor: unknown): string {
  if (typeof valor === "number") return valor.toLocaleString(localeActual());
  if (typeof valor === "boolean") return valor ? t("firmaPage.si") : t("firmaPage.no");
  if (valor === null || valor === undefined) return "—";
  return typeof valor === "object" ? JSON.stringify(valor) : String(valor);
}

function segundosHasta(iso: string | null, ahora: number): number {
  if (!iso) return 0;
  return Math.max(0, Math.ceil((new Date(iso).getTime() - ahora) / 1000));
}

function Fila({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  return <div className="firma-fila"><dt>{etiqueta}</dt><dd>{children}</dd></div>;
}

function Contrato({ proceso }: { proceso: ProcesoFirma }) {
  const { contrato } = proceso;
  const riesgo = Object.entries(contrato.datos_riesgo);
  return (
    <article className="firma-documento" aria-labelledby="titulo-contrato">
      <header>
        <h2 id="titulo-contrato">{t("firmaPage.contrato_de_seguro_condiciones_particulares")}</h2>
        <p>{t("firmaPage.nombre_ramo_cotizacion_cotizacion_id", { nombre_ramo: contrato.nombre_ramo, cotizacion_id: contrato.cotizacion_id })}</p>
      </header>
      <section>
        <h3>{t("firmaPage.tomador_y_asegurado")}</h3>
        <dl>
          <Fila etiqueta={t("firmaPage.nombre")}>{contrato.titular.nombre_completo}</Fila>
          <Fila etiqueta={t("firmaPage.documento")}>{contrato.titular.tipo_documento} {contrato.titular.numero_documento}</Fila>
          <Fila etiqueta={t("firmaPage.correo")}>{contrato.titular.email}</Fila>
        </dl>
      </section>
      <section>
        <h3>{t("firmaPage.cobertura")}</h3>
        <dl>
          <Fila etiqueta={t("firmaPage.amparo_principal")}>{contrato.cobertura_principal.nombre}</Fila>
          <Fila etiqueta={t("firmaPage.suma_asegurada")}>{moneda(contrato.cobertura_principal.suma_asegurada, contrato.moneda)}</Fila>
          {riesgo.map(([campo, valor]) => (
            <Fila key={campo} etiqueta={etiqueta(campo)}>{valorRiesgo(valor)}</Fila>
          ))}
        </dl>
      </section>
      <section>
        <h3>{t("firmaPage.prima")}</h3>
        <dl>
          <Fila etiqueta={t("firmaPage.prima_total")}>{moneda(contrato.prima_total, contrato.moneda)}</Fila>
          <Fila etiqueta={t("firmaPage.pagada_el")}>{fechaHora(contrato.fecha_pago)}</Fila>
          <Fila etiqueta={t("firmaPage.referencia_del_pago")}>{contrato.referencia_pago ?? contrato.pago_id}</Fila>
        </dl>
      </section>
      <section>
        <h3>{t("firmaPage.clausulas")}</h3>
        <ol className="firma-clausulas">
          {contrato.clausulas.map((clausula) => <li key={clausula}>{clausula}</li>)}
        </ol>
      </section>
      <footer className="firma-huella">
        {t("firmaPage.huella_del_documento_sha_256")} <code>{proceso.huella_documento}</code>
      </footer>
    </article>
  );
}

function Resumen({ proceso }: { proceso: ProcesoFirma }) {
  const { contrato } = proceso;
  return (
    <aside className="firma-resumen" aria-label={t("firmaPage.resumen")}>
      <small>{t("firmaPage.resumen")}</small>
      <strong>{contrato.nombre_ramo}</strong>
      <p className="firma-resumen-valor">{moneda(contrato.prima_total, contrato.moneda)}</p>
      <dl>
        <Fila etiqueta={t("firmaPage.suma_asegurada")}>{moneda(contrato.cobertura_principal.suma_asegurada, contrato.moneda)}</Fila>
        <Fila etiqueta={t("firmaPage.pago")}><span className="firma-ok">{t("firmaPage.aprobado")}</span></Fila>
        <Fila etiqueta={t("firmaPage.firma")}>{proceso.estado === "FIRMADA" ? t("firmaPage.firmada") : proceso.estado === "BLOQUEADA" ? t("firmaPage.bloqueada") : t("firmaPage.pendiente")}</Fila>
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
  const [descargando, setDescargando] = useState(false);
  const [errorDescarga, setErrorDescarga] = useState("");
  const [rol, setRol] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (perfil) => { if (activo) setRol(perfil.rol); },
      () => undefined,
    );
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
      <AppLayout activo="Pagos" rol={rol}>
        <header className="home-header firma-cabecera">
          <div>
            <h1>{t("firmaPage.no_podemos_mostrar_el_contrato")}</h1>
            <p>{t("firmaPage.revisa_el_estado_del_pago")}</p>
          </div>
        </header>
        <section className="home-panel firma-panel">
          <p role="alert" className="firma-alerta">{errorCarga}</p>
        </section>
      </AppLayout>
    );
  }
  if (!proceso) {
    return (
      <AppLayout activo="Pagos" rol={rol}>
        <p role="status" className="home-card-vacio">{t("firmaPage.cargando_contrato")}</p>
      </AppLayout>
    );
  }

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

  async function descargarPoliza() {
    if (!proceso?.poliza_id) return;
    setErrorDescarga("");
    setDescargando(true);
    try {
      await descargarDocumentoPoliza(proceso.poliza_id);
    } catch (fallo) {
      setErrorDescarga((fallo as Error).message);
    } finally {
      setDescargando(false);
    }
  }

  // Si la emisión quedó pendiente, consultar el contrato la completa en el servidor.
  async function actualizarPoliza() {
    setErrorDescarga("");
    try {
      setProceso(await obtenerContrato(cotizacionId));
    } catch (fallo) {
      setErrorDescarga((fallo as Error).message);
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
          ? t("firmaPage.te_quedan_intentosrestantes_intentos", { intentosRestantes: fallo.intentosRestantes }) : "";
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
    <AppLayout activo="Pagos" rol={rol}>
      <header className="home-header firma-cabecera">
        <div>
          <h1>{proceso.estado === "FIRMADA" ? t("firmaPage.contrato_firmado") : t("firmaPage.firma_tu_contrato")}</h1>
          <p>
            {proceso.estado === "FIRMADA"
              ? proceso.poliza_id
                ? t("firmaPage.tu_firma_quedo_registrada_y")
                : t("firmaPage.tu_firma_quedo_registrada_estamos")
              : t("firmaPage.revisa_las_condiciones_de_tu")}
          </p>
        </div>
      </header>
      <div className="firma-contenido">
        <div className="firma-principal">

          {!proceso.documento_integro && (
            <p role="alert" className="firma-alerta">
              {t("firmaPage.el_contrato_no_coincide_con")}
            </p>
          )}

          <Contrato proceso={proceso} />

          {proceso.estado === "FIRMADA" && (
            <section className="firma-tarjeta firma-exito" aria-label={t("firmaPage.firma_registrada")}>
              <span className="material-symbols-outlined" aria-hidden="true">verified</span>
              <div>
                <strong>{t("firmaPage.firmado_el_fechahora", { fechaHora: fechaHora(proceso.firmado_en!) })}</strong>
                <small>{t("firmaPage.referencia_de_la_firma_referencia", { referencia_proveedor: proceso.referencia_proveedor })}</small>
              </div>
            </section>
          )}

          {proceso.estado === "FIRMADA" && proceso.poliza_id && (
            <section className="firma-tarjeta firma-exito firma-poliza" aria-label={t("firmaPage.poliza_emitida")}>
              <span className="material-symbols-outlined" aria-hidden="true">task_alt</span>
              <div>
                <strong>{t("firmaPage.tu_poliza_fue_emitida")}</strong>
                <small>
                  {t("firmaPage.te_enviaremos_un_correo_a", { email: proceso.contrato.titular.email })}
                </small>
              </div>
              <div className="firma-poliza-acciones">
                <button
                  type="button"
                  className="firma-boton-secundario"
                  onClick={() => void descargarPoliza()}
                  disabled={descargando}
                >
                  {descargando ? t("firmaPage.descargando") : t("firmaPage.descargar_poliza_pdf")}
                  <span className="material-symbols-outlined" aria-hidden="true">download</span>
                </button>
                <button
                  type="button"
                  className="firma-boton-primario"
                  onClick={() => navigate("/polizas")}
                >
                  {t("firmaPage.finalizar_e_ir_a_mis")}
                  <span className="material-symbols-outlined" aria-hidden="true">arrow_forward</span>
                </button>
              </div>
            </section>
          )}

          {proceso.estado === "FIRMADA" && !proceso.poliza_id && (
            <section className="firma-tarjeta firma-poliza" aria-label={t("firmaPage.poliza_en_preparacion")}>
              <span className="material-symbols-outlined firma-icono" aria-hidden="true">hourglass_top</span>
              <div>
                <strong>{t("firmaPage.estamos_preparando_tu_poliza")}</strong>
                <small>{t("firmaPage.puede_tardar_unos_segundos")}</small>
              </div>
              <button type="button" className="firma-boton-secundario" onClick={() => void actualizarPoliza()}>
                {t("firmaPage.actualizar")}
              </button>
            </section>
          )}

          {errorDescarga && <p role="alert" className="firma-alerta">{errorDescarga}</p>}

          {proceso.estado === "BLOQUEADA" && (
            <p role="alert" className="firma-alerta">
              {t("firmaPage.la_firma_se_bloqueo_por")}
            </p>
          )}

          {proceso.estado === "PENDIENTE" && (
            <section className="firma-tarjeta" aria-labelledby="titulo-firma">
              <span className="material-symbols-outlined firma-icono" aria-hidden="true">signature</span>
              <div className="firma-tarjeta-cuerpo">
                <h2 id="titulo-firma">{t("firmaPage.firma_electronica_del_contrato")}</h2>
                <label className="firma-autoriza">
                  <input
                    type="checkbox"
                    checked={autoriza}
                    onChange={(evento) => setAutoriza(evento.target.checked)}
                  />
                  {t("firmaPage.lei_el_contrato_y_autorizo")}
                </label>

                <fieldset className="firma-canal" disabled={!autoriza || enviando}>
                  <legend>{t("firmaPage.enviar_el_codigo_por")}</legend>
                  <label>
                    <input type="radio" name="canal" checked={canal === "SMS"} onChange={() => setCanal("SMS")} />
                    {t("firmaPage.sms_al_celular")}
                  </label>
                  <label>
                    <input type="radio" name="canal" checked={canal === "EMAIL"} onChange={() => setCanal("EMAIL")} />
                    {t("firmaPage.correo_electronico")}
                  </label>
                  <button
                    type="button"
                    className="firma-boton-secundario"
                    onClick={() => void enviarCodigo()}
                    disabled={espera > 0 || proceso.envios_restantes === 0}
                  >
                    {proceso.otp_destino ? t("firmaPage.reenviar_codigo") : t("firmaPage.enviar_codigo")}
                    {espera > 0 && ` (${espera} s)`}
                  </button>
                </fieldset>

                {codigoEnviado && (
                  <form className="firma-codigo" onSubmit={(evento) => void firmar(evento)}>
                    <p role="status">
                      {t("firmaPage.enviamos_un_codigo", { otp_destino: proceso.otp_destino })}
                      {proceso.otp_expira_en && t("firmaPage.valido_hasta", {
                        hora: new Date(proceso.otp_expira_en)
                          .toLocaleTimeString(localeActual(), { hour: "2-digit", minute: "2-digit" }),
                      })}
                    </p>
                    <label htmlFor="codigo-otp">{t("firmaPage.codigo_de_verificacion")}</label>
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
                      {t("firmaPage.firmar_contrato")}
                      <span className="material-symbols-outlined" aria-hidden="true">arrow_forward</span>
                    </button>
                  </form>
                )}
                {aviso && <p role="alert" className="firma-alerta">{aviso}</p>}
              </div>
            </section>
          )}

        </div>
        <Resumen proceso={proceso} />
      </div>
    </AppLayout>
  );
}

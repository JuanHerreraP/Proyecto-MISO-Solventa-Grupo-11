import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import RenovacionAutomatica from "../components/poliza/RenovacionAutomatica";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import {
  obtenerBilletera,
  obtenerCertificado,
  type Certificado,
  type PolizaResumen,
} from "../services/billetera.service";
import { descargarDocumentoPoliza } from "../services/poliza-documento.service";
import {
  listarClientesDeAsesor,
  obtenerPolizasDeCliente,
  type ClienteDeAsesor,
} from "../services/asesor.service";

import { t, localeActual } from "../i18n";

const ICONO_RAMO: Record<string, string> = {
  VIAJE: "flight_takeoff",
  PROTECCION_DISPOSITIVOS: "devices",
  VIDA: "favorite",
  PARAMETRICO: "thunderstorm",
};

// Ramos que se renuevan (HU22); los demás se contratan de nuevo cuando se necesitan.
const RAMOS_RENOVABLES = new Set(["VIDA", "PROTECCION_DISPOSITIVOS", "PARAMETRICO"]);

const ESTADOS: Record<string, string> = {
  get VIGENTE() { return t("polizasPage.vigente"); },
  get VENCIDA() { return t("polizasPage.vencida"); },
  get CANCELADA() { return t("polizasPage.cancelada"); },
};

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.split("-").map(Number);
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

export default function PolizasPage() {
  const navigate = useNavigate();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [polizas, setPolizas] = useState<PolizaResumen[] | null>(null);
  const [error, setError] = useState("");
  const [expandida, setExpandida] = useState<string | null>(null);
  const [certificados, setCertificados] = useState<Record<string, Certificado>>({});
  const [descargando, setDescargando] = useState<string | null>(null);
  const [errorDescarga, setErrorDescarga] = useState<Record<string, string>>({});
  const [clientes, setClientes] = useState<ClienteDeAsesor[]>([]);
  const [clienteId, setClienteId] = useState("");

  const cargarBilletera = useCallback(() => {
    return obtenerBilletera().then(
      (billetera) => { setPolizas(billetera.polizas); setError(""); },
      (fallo: Error) => { setError(fallo.message); },
    );
  }, []);

  const cargarPolizasDeCliente = useCallback((id: string) => {
    return obtenerPolizasDeCliente(id).then(
      (billetera) => { setPolizas(billetera.polizas); setError(""); },
      (fallo: Error) => { setError(fallo.message); },
    );
  }, []);

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => {
        if (!activo) return;
        setPerfil(datos);
        if (datos.rol === "ASESOR_VENTAS") {
          setPolizas([]);
          listarClientesDeAsesor().then(
            (lista) => { if (activo) setClientes(lista); },
            (fallo: Error) => { if (activo) setError(fallo.message); },
          );
        } else {
          void cargarBilletera();
        }
      },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    return () => { activo = false; };
  }, [navigate, cargarBilletera]);

  useEffect(() => {
    // Al volver a esta pantalla se actualiza la billetera visible sin cambiar el cliente elegido.
    const alVolver = () => {
      if (document.visibilityState !== "visible") return;
      if (perfil?.rol === "ASESOR_VENTAS" && clienteId) void cargarPolizasDeCliente(clienteId);
      else if (perfil?.rol !== "ASESOR_VENTAS") void cargarBilletera();
    };
    window.addEventListener("focus", alVolver);
    document.addEventListener("visibilitychange", alVolver);
    return () => {
      window.removeEventListener("focus", alVolver);
      document.removeEventListener("visibilitychange", alVolver);
    };
  }, [cargarBilletera, cargarPolizasDeCliente, perfil?.rol, clienteId]);

  const rol = perfil?.rol ?? null;
  const esAsesor = rol === "ASESOR_VENTAS";
  const cliente = clientes.find((actual) => actual.cliente_id === clienteId);

  function alternar(poliza: PolizaResumen) {
    const abrir = expandida !== poliza.poliza_id;
    setExpandida(abrir ? poliza.poliza_id : null);
    // Al abrir, trae el certificado una sola vez para mostrar el detalle completo.
    if (abrir && !esAsesor && !certificados[poliza.poliza_id]) {
      obtenerCertificado(poliza.poliza_id).then(
        (cert) => setCertificados((previo) => ({ ...previo, [poliza.poliza_id]: cert })),
        () => undefined,
      );
    }
  }

  async function descargar(polizaId: string) {
    setErrorDescarga((previo) => ({ ...previo, [polizaId]: "" }));
    setDescargando(polizaId);
    try {
      await descargarDocumentoPoliza(polizaId);
    } catch (fallo) {
      setErrorDescarga((previo) => ({ ...previo, [polizaId]: (fallo as Error).message }));
    } finally {
      setDescargando(null);
    }
  }

  return (
    <AppLayout activo="Mis pólizas" rol={rol}>
      <header className="home-header">
        <div>
          <h1>{esAsesor ? t("polizasPage.polizas_de_clientes") : t("polizasPage.mis_polizas")}</h1>
          <p>
            {esAsesor
              ? t("polizasPage.selecciona_un_cliente_para_gestionar")
              : t("polizasPage.consulta_tus_polizas_y_el")}
          </p>
        </div>
      </header>

      {error && <p role="alert" className="home-aviso">{error}</p>}

      {esAsesor && (
        <section className="home-panel asesor-polizas-selector" aria-labelledby="cliente-polizas">
          <div>
            <h2 id="cliente-polizas">{t("polizasPage.cliente_asegurado")}</h2>
            <p>{t("polizasPage.solo_podras_cancelar_polizas_originadas")}</p>
          </div>
          <div className="cotizar-campo">
            <label htmlFor="cliente">{t("polizasPage.selecciona_un_cliente")}</label>
            <select
              id="cliente"
              value={clienteId}
              onChange={(evento) => {
                const id = evento.target.value;
                setClienteId(id);
                setExpandida(null);
                setError("");
                if (!id) setPolizas([]);
                else {
                  setPolizas(null);
                  void cargarPolizasDeCliente(id);
                }
              }}
            >
              <option value="">{t("polizasPage.selecciona_una_opcion")}</option>
              {clientes.map((actual) => (
                <option key={actual.cliente_id} value={actual.cliente_id}>
                  {actual.nombre} {actual.apellido} · {actual.email}
                </option>
              ))}
            </select>
          </div>
          {clientes.length === 0 && (
            <p className="home-card-vacio">{t("polizasPage.aun_no_tienes_clientes_asociados")}</p>
          )}
        </section>
      )}

      <section aria-label={t("polizasPage.lista_de_polizas")} className="cotizaciones-lista">
        {polizas === null && !error && (!esAsesor || clienteId) && (
          <p role="status" className="home-card-vacio">{t("polizasPage.cargando_tus_polizas")}</p>
        )}
        {polizas?.length === 0 && (!esAsesor || Boolean(clienteId)) && (
          <div className="home-panel">
            <p className="home-card-vacio">{t("polizasPage.aun_no_tienes_polizas")}</p>
          </div>
        )}
        {polizas?.map((poliza) => {
          const abierta = expandida === poliza.poliza_id;
          const cert = certificados[poliza.poliza_id];
          return (
            <article key={poliza.poliza_id} className="cotizacion-item">
              <button
                type="button"
                className="cotizacion-cabecera"
                aria-expanded={abierta}
                onClick={() => alternar(poliza)}
              >
                <span className="cotizar-ramo-icono material-symbols-outlined" aria-hidden="true">
                  {ICONO_RAMO[poliza.ramo] ?? "shield"}
                </span>
                <span className="cotizacion-cabecera-texto">
                  <strong>{poliza.nombre_ramo}</strong>
                  <small>{poliza.numero_poliza}</small>
                </span>
                <span className={`home-chip ${poliza.activa ? "home-chip-verde" : "cotizacion-estado"}`}>
                  {ESTADOS[poliza.estado] ?? poliza.estado}
                </span>
                <span className="material-symbols-outlined cotizacion-chevron" aria-hidden="true">
                  {abierta ? "expand_less" : "expand_more"}
                </span>
              </button>

              {abierta && (
                <div className="cotizacion-detalle">
                  <div className="cotizar-detalle">
                    <span>{t("polizasPage.cobertura_principal")}</span>
                    <strong>{poliza.cobertura_principal}</strong>
                    {cert && (
                      <small>
                        {t("polizasPage.suma_asegurada_formatearmonto", { formatearMonto: formatearMonto(cert.suma_asegurada, cert.moneda) })}
                      </small>
                    )}
                  </div>

                  <dl className="cotizacion-datos">
                    <div>
                      <dt>{t("polizasPage.vigencia")}</dt>
                      <dd>
                        {formatearFecha(poliza.fecha_inicio)} — {formatearFecha(poliza.fecha_fin)}
                      </dd>
                    </div>
                    {cert && (
                      <>
                        <div>
                          <dt>{t("polizasPage.titular")}</dt>
                          <dd>{cert.titular}</dd>
                        </div>
                        <div>
                          <dt>{t("polizasPage.documento")}</dt>
                          <dd>{cert.documento_titular}</dd>
                        </div>
                        <div>
                          <dt>{t("polizasPage.prima_total")}</dt>
                          <dd>{formatearMonto(cert.prima_total, cert.moneda)}</dd>
                        </div>
                      </>
                    )}
                    <div>
                      <dt>{t("polizasPage.numero_de_poliza")}</dt>
                      <dd>{poliza.numero_poliza}</dd>
                    </div>
                  </dl>

                  {poliza.activa && RAMOS_RENOVABLES.has(poliza.ramo) && (
                    <RenovacionAutomatica
                      polizaId={poliza.poliza_id}
                      puedeRegistrarTarjeta={!esAsesor}
                    />
                  )}

                  <div className="poliza-acciones">
                    {poliza.activa && (
                      <>
                        {!esAsesor && (
                          <button
                            type="button"
                            className="cotizar-boton-secundario"
                            onClick={() => navigate(`/polizas/${encodeURIComponent(poliza.poliza_id)}/modificar`)}
                          >
                            {t("polizasPage.modificar_coberturas_y_beneficiarios")}
                          </button>
                        )}
                        <button
                          type="button"
                          className="poliza-boton-cancelar"
                          onClick={() => navigate(
                            `/polizas/${encodeURIComponent(poliza.poliza_id)}/cancelar`,
                            { state: cliente ? { clienteNombre: `${cliente.nombre} ${cliente.apellido}` } : null },
                          )}
                        >
                          {t("polizasPage.cancelar_poliza")}
                        </button>
                      </>
                    )}
                    <button
                      type="button"
                      className="cotizar-boton-secundario"
                      onClick={() => navigate(`/polizas/${encodeURIComponent(poliza.poliza_id)}/historial`)}
                    >
                      <span className="material-symbols-outlined" aria-hidden="true">history</span>
                      {t("polizasPage.ver_historial")}
                    </button>
                    <button
                      type="button"
                      className="cotizar-boton-primario"
                      onClick={() => void descargar(poliza.poliza_id)}
                      disabled={descargando === poliza.poliza_id}
                    >
                      <span className="material-symbols-outlined" aria-hidden="true">download</span>
                      {descargando === poliza.poliza_id ? t("polizasPage.descargando") : t("polizasPage.descargar_poliza_pdf")}
                    </button>
                  </div>
                  {errorDescarga[poliza.poliza_id] && (
                    <p role="alert" className="home-aviso">{errorDescarga[poliza.poliza_id]}</p>
                  )}
                </div>
              )}
            </article>
          );
        })}
      </section>
    </AppLayout>
  );
}

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

const ICONO_RAMO: Record<string, string> = {
  VIAJE: "flight_takeoff",
  PROTECCION_DISPOSITIVOS: "devices",
  VIDA: "favorite",
  PARAMETRICO: "thunderstorm",
};

// Ramos que se renuevan (HU22); los demás se contratan de nuevo cuando se necesitan.
const RAMOS_RENOVABLES = new Set(["VIDA", "PROTECCION_DISPOSITIVOS", "PARAMETRICO"]);

const ESTADOS: Record<string, string> = {
  VIGENTE: "Vigente",
  VENCIDA: "Vencida",
  CANCELADA: "Cancelada",
};

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.split("-").map(Number);
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
          <h1>{esAsesor ? "Pólizas de clientes" : "Mis pólizas"}</h1>
          <p>
            {esAsesor
              ? "Selecciona un cliente para gestionar una cancelación asistida."
              : "Consulta tus pólizas y el detalle de cada una."}
          </p>
        </div>
      </header>

      {error && <p role="alert" className="home-aviso">{error}</p>}

      {esAsesor && (
        <section className="home-panel asesor-polizas-selector" aria-labelledby="cliente-polizas">
          <div>
            <h2 id="cliente-polizas">Cliente asegurado</h2>
            <p>Solo podrás cancelar pólizas originadas en una venta asistida por ti.</p>
          </div>
          <div className="cotizar-campo">
            <label htmlFor="cliente">Selecciona un cliente</label>
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
              <option value="">Selecciona una opción</option>
              {clientes.map((actual) => (
                <option key={actual.cliente_id} value={actual.cliente_id}>
                  {actual.nombre} {actual.apellido} · {actual.email}
                </option>
              ))}
            </select>
          </div>
          {clientes.length === 0 && (
            <p className="home-card-vacio">Aún no tienes clientes asociados.</p>
          )}
        </section>
      )}

      <section aria-label="Lista de pólizas" className="cotizaciones-lista">
        {polizas === null && !error && (!esAsesor || clienteId) && (
          <p role="status" className="home-card-vacio">Cargando tus pólizas…</p>
        )}
        {polizas?.length === 0 && (!esAsesor || Boolean(clienteId)) && (
          <div className="home-panel">
            <p className="home-card-vacio">Aún no tienes pólizas.</p>
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
                    <span>Cobertura principal</span>
                    <strong>{poliza.cobertura_principal}</strong>
                    {cert && (
                      <small>
                        Suma asegurada: {formatearMonto(cert.suma_asegurada, cert.moneda)}
                      </small>
                    )}
                  </div>

                  <dl className="cotizacion-datos">
                    <div>
                      <dt>Vigencia</dt>
                      <dd>
                        {formatearFecha(poliza.fecha_inicio)} — {formatearFecha(poliza.fecha_fin)}
                      </dd>
                    </div>
                    {cert && (
                      <>
                        <div>
                          <dt>Titular</dt>
                          <dd>{cert.titular}</dd>
                        </div>
                        <div>
                          <dt>Documento</dt>
                          <dd>{cert.documento_titular}</dd>
                        </div>
                        <div>
                          <dt>Prima total</dt>
                          <dd>{formatearMonto(cert.prima_total, cert.moneda)}</dd>
                        </div>
                      </>
                    )}
                    <div>
                      <dt>Número de póliza</dt>
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
                            Modificar coberturas y beneficiarios
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
                          Cancelar póliza
                        </button>
                      </>
                    )}
                    <button
                      type="button"
                      className="cotizar-boton-secundario"
                      onClick={() => navigate(`/polizas/${encodeURIComponent(poliza.poliza_id)}/historial`)}
                    >
                      <span className="material-symbols-outlined" aria-hidden="true">history</span>
                      Ver historial
                    </button>
                    <button
                      type="button"
                      className="cotizar-boton-primario"
                      onClick={() => void descargar(poliza.poliza_id)}
                      disabled={descargando === poliza.poliza_id}
                    >
                      <span className="material-symbols-outlined" aria-hidden="true">download</span>
                      {descargando === poliza.poliza_id ? "Descargando…" : "Descargar póliza (PDF)"}
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

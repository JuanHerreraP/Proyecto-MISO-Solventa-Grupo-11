import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import {
  obtenerBilletera,
  obtenerCertificado,
  type Certificado,
  type PolizaResumen,
} from "../services/billetera.service";
import { descargarDocumentoPoliza } from "../services/poliza-documento.service";

const ICONO_RAMO: Record<string, string> = {
  VIAJE: "flight_takeoff",
  PROTECCION_DISPOSITIVOS: "devices",
  VIDA: "favorite",
  PARAMETRICO: "thunderstorm",
};

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

  const cargarBilletera = useCallback(() => {
    return obtenerBilletera().then(
      (billetera) => { setPolizas(billetera.polizas); setError(""); },
      (fallo: Error) => { setError(fallo.message); },
    );
  }, []);

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => { if (activo) setPerfil(datos); },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    void cargarBilletera();
    // Al volver a esta pantalla (por ejemplo, tras firmar y emitir una póliza nueva)
    // se vuelve a consultar la billetera para mostrarla sin recargar la página.
    const alVolver = () => {
      if (document.visibilityState === "visible") void cargarBilletera();
    };
    window.addEventListener("focus", alVolver);
    document.addEventListener("visibilitychange", alVolver);
    return () => {
      activo = false;
      window.removeEventListener("focus", alVolver);
      document.removeEventListener("visibilitychange", alVolver);
    };
  }, [navigate, cargarBilletera]);

  const rol = perfil?.rol ?? null;

  function alternar(poliza: PolizaResumen) {
    const abrir = expandida !== poliza.poliza_id;
    setExpandida(abrir ? poliza.poliza_id : null);
    // Al abrir, trae el certificado una sola vez para mostrar el detalle completo.
    if (abrir && !certificados[poliza.poliza_id]) {
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
          <h1>Mis pólizas</h1>
          <p>Consulta tus pólizas y el detalle de cada una.</p>
        </div>
      </header>

      {error && <p role="alert" className="home-aviso">{error}</p>}

      <section aria-label="Lista de pólizas" className="cotizaciones-lista">
        {polizas === null && !error && (
          <p role="status" className="home-card-vacio">Cargando tus pólizas…</p>
        )}
        {polizas?.length === 0 && (
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

                  <div className="poliza-acciones">
                    {poliza.activa && (
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

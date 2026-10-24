import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import { obtenerBilletera, type PolizaResumen } from "../services/billetera.service";

const ACCIONES = [
  { icono: "error", titulo: "Reportar un siniestro", detalle: "Con evidencia fotográfica", ruta: null },
  { icono: "schedule", titulo: "Consultar estado de siniestro", detalle: "Sigue tu reclamación", ruta: null },
  { icono: "request_quote", titulo: "Cotizar un nuevo seguro", detalle: "Viaje, vida, dispositivos y más", ruta: "/cotizar" },
] as const;

function iniciales(perfil: Perfil | null): string {
  const letras = `${perfil?.nombre?.[0] ?? ""}${perfil?.apellido?.[0] ?? ""}`;
  return letras.toUpperCase() || "S";
}

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString("es-CO", {
    day: "numeric", month: "short", year: "numeric",
  });
}

export default function HomePage() {
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [polizas, setPolizas] = useState<PolizaResumen[] | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => {
        if (!activo) return;
        setPerfil(datos);
        if (datos.rol === "CLIENTE") {
          obtenerBilletera().then(
            (billetera) => { if (activo) setPolizas(billetera.polizas); },
            () => { if (activo) setPolizas([]); },
          );
        }
      },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    return () => { activo = false; };
  }, [navigate]);

  const rol = perfil?.rol ?? null;
  const polizaActiva = polizas?.find((poliza) => poliza.activa);

  return (
    <AppLayout activo="Inicio" rol={rol}>
        <header className="home-header">
          <div>
            <h1>{perfil?.nombre ? `Hola, ${perfil.nombre}` : "Hola"}</h1>
            <p>Este es el resumen de tu cuenta en Solventa.</p>
          </div>
          <div className="home-user">
            <span className="material-symbols-outlined" aria-label="Notificaciones" role="img">notifications</span>
            <span className="home-avatar" aria-hidden="true">{iniciales(perfil)}</span>
          </div>
        </header>

        {location.state?.accesoDenegado && (
          <p role="alert" className="home-aviso">No tienes permiso para acceder a esa página.</p>
        )}

        <section className="home-cards" aria-label="Resumen">
          <article className="home-card">
            <h2>Póliza activa</h2>
            {polizaActiva ? (
              <>
                <p className="home-card-valor">{polizaActiva.nombre_ramo}</p>
                <p className="home-card-detalle">{polizaActiva.numero_poliza}</p>
                <span className="home-chip home-chip-verde">Vigente hasta {formatearFecha(polizaActiva.fecha_fin)}</span>
              </>
            ) : (
              <p className="home-card-vacio">Aún no tienes pólizas activas.</p>
            )}
          </article>
          <article className="home-card">
            <h2>Próximo pago</h2>
            <p className="home-card-vacio">Sin pagos programados.</p>
          </article>
          <article className="home-card">
            <h2>Siniestros abiertos</h2>
            <p className="home-card-vacio">No tienes siniestros en curso.</p>
          </article>
        </section>

        <div className="home-grid">
          <section className="home-panel" aria-labelledby="historial">
            <h2 id="historial">Historial reciente</h2>
            <table>
              <thead>
                <tr><th>Fecha</th><th>Movimiento</th><th>Referencia</th><th>Estado</th></tr>
              </thead>
              <tbody>
                <tr><td colSpan={4} className="home-card-vacio">Todavía no hay movimientos.</td></tr>
              </tbody>
            </table>
          </section>

          <section aria-labelledby="acciones">
            <h2 id="acciones" className="home-acciones-titulo">Acciones rápidas</h2>
            <div className="home-acciones">
              {ACCIONES.map(({ icono, titulo, detalle, ruta }) => (
                <button
                  key={titulo}
                  type="button"
                  className="home-accion"
                  disabled={ruta === null}
                  title={ruta === null ? "Próximamente" : undefined}
                  onClick={ruta ? () => navigate(ruta) : undefined}
                >
                  <span className="home-accion-icono material-symbols-outlined" aria-hidden="true">{icono}</span>
                  <span>
                    <strong>{titulo}</strong>
                    <small>{detalle}</small>
                  </span>
                </button>
              ))}
            </div>
          </section>
        </div>
    </AppLayout>
  );
}

import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import { obtenerBilletera, type PolizaResumen } from "../services/billetera.service";
import { obtenerHistorialPoliza } from "../services/historial-poliza.service";
import type { MovimientoPoliza, NaturalezaMonto, TipoMovimiento } from "../types/historial";
import {
  asociarCliente,
  listarClientesDeAsesor,
  type ClienteDeAsesor,
} from "../services/asesor.service";

const ACCIONES = [
  { icono: "error", titulo: "Reportar un siniestro", detalle: "Registra lo ocurrido", ruta: "/siniestros/nuevo" },
  { icono: "schedule", titulo: "Consultar estado de siniestro", detalle: "Sigue tu reclamación", ruta: null },
  { icono: "request_quote", titulo: "Cotizar un nuevo seguro", detalle: "Viaje, vida, dispositivos y más", ruta: "/cotizar" },
] as const;

const MOVIMIENTO_NOMBRE: Record<TipoMovimiento, string> = {
  EMISION: "Emisión de póliza",
  PAGO_PRIMA_INICIAL: "Pago de prima inicial",
  ENDOSO: "Modificación contractual",
  RENOVACION: "Renovación",
  CANCELACION: "Cancelación",
  DESEMBOLSO_INDEMNIZACION: "Pago de indemnización",
  REEMBOLSO: "Reembolso",
};

/** Movimiento del historial junto con la póliza a la que pertenece (vista de inicio, HU25). */
type MovimientoReciente = MovimientoPoliza & { nombre_ramo: string };

const MAX_RECIENTES = 5;

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

function formatearFechaMovimiento(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "numeric", month: "short", year: "numeric",
  });
}

/** Monto con signo según la perspectiva del cliente; "—" si el movimiento no tiene monto. */
function montoConSigno(movimiento: MovimientoPoliza): string {
  if (movimiento.monto === null) return "—";
  const valor = Number(movimiento.monto).toLocaleString("es-CO", {
    style: "currency",
    currency: movimiento.moneda ?? "COP",
    maximumFractionDigits: 0,
  });
  const naturaleza: NaturalezaMonto | null = movimiento.naturaleza_monto;
  if (naturaleza === "COBRO") return `-${valor}`;
  if (naturaleza === "REEMBOLSO" || naturaleza === "INDEMNIZACION") return `+${valor}`;
  return valor;
}

/**
 * Reúne los movimientos recientes de todas las pólizas del cliente (HU25) para la vista de
 * inicio. Cada póliza se consulta en paralelo; un fallo individual no rompe el listado.
 */
async function cargarRecientes(polizas: PolizaResumen[]): Promise<MovimientoReciente[]> {
  if (polizas.length === 0) return [];
  const resultados = await Promise.all(
    polizas.map((poliza) =>
      obtenerHistorialPoliza(poliza.poliza_id).then(
        (historial) =>
          historial.movimientos.map((m) => ({ ...m, nombre_ramo: poliza.nombre_ramo })),
        () => [] as MovimientoReciente[],
      ),
    ),
  );
  return resultados
    .flat()
    .sort((a, b) => new Date(b.fecha).getTime() - new Date(a.fecha).getTime())
    .slice(0, MAX_RECIENTES);
}

export default function HomePage() {
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [polizas, setPolizas] = useState<PolizaResumen[] | null>(null);
  const [movimientos, setMovimientos] = useState<MovimientoReciente[] | null>(null);
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
            (billetera) => {
              if (!activo) return;
              setPolizas(billetera.polizas);
              cargarRecientes(billetera.polizas).then(
                (recientes) => { if (activo) setMovimientos(recientes); },
                () => { if (activo) setMovimientos([]); },
              );
            },
            () => { if (activo) { setPolizas([]); setMovimientos([]); } },
          );
        }
      },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    return () => { activo = false; };
  }, [navigate]);

  const rol = perfil?.rol ?? null;

  if (rol === "ASESOR_VENTAS") {
    return <HomeAsesor perfil={perfil} />;
  }

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
                <tr><th>Fecha</th><th>Movimiento</th><th>Monto</th><th>Estado</th></tr>
              </thead>
              <tbody>
                {movimientos === null && (
                  <tr><td colSpan={4} className="home-card-vacio">Cargando movimientos…</td></tr>
                )}
                {movimientos !== null && movimientos.length === 0 && (
                  <tr><td colSpan={4} className="home-card-vacio">Todavía no hay movimientos.</td></tr>
                )}
                {movimientos?.map((movimiento) => (
                  <tr
                    key={movimiento.movimiento_id}
                    className="home-fila-clic"
                    tabIndex={0}
                    role="button"
                    aria-label={`Ver historial de ${movimiento.nombre_ramo}`}
                    onClick={() =>
                      navigate(`/polizas/${encodeURIComponent(movimiento.poliza_id)}/historial`)
                    }
                    onKeyDown={(evento) => {
                      if (evento.key === "Enter" || evento.key === " ") {
                        evento.preventDefault();
                        navigate(`/polizas/${encodeURIComponent(movimiento.poliza_id)}/historial`);
                      }
                    }}
                  >
                    <td>{formatearFechaMovimiento(movimiento.fecha)}</td>
                    <td>
                      <strong>{MOVIMIENTO_NOMBRE[movimiento.tipo] ?? movimiento.tipo}</strong>
                      <small className="home-fila-detalle">{movimiento.nombre_ramo}</small>
                    </td>
                    <td>{montoConSigno(movimiento)}</td>
                    <td>
                      {movimiento.estado && (
                        <span className="home-chip cotizacion-estado">{movimiento.estado}</span>
                      )}
                    </td>
                  </tr>
                ))}
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

/** Inicio del asesor de ventas: gestiona sus clientes y registra siniestros en su nombre. */
function HomeAsesor({ perfil }: { perfil: Perfil | null }) {
  const navigate = useNavigate();
  const [clientes, setClientes] = useState<ClienteDeAsesor[] | null>(null);
  const [error, setError] = useState("");
  const [email, setEmail] = useState("");
  const [asociando, setAsociando] = useState(false);
  const [errorAsociar, setErrorAsociar] = useState("");
  const [exito, setExito] = useState("");

  useEffect(() => {
    let activo = true;
    listarClientesDeAsesor().then(
      (lista) => { if (activo) setClientes(lista); },
      (fallo: Error) => { if (activo) setError(fallo.message); },
    );
    return () => { activo = false; };
  }, []);

  async function asociar(evento: React.FormEvent) {
    evento.preventDefault();
    if (email.trim() === "") return;
    setAsociando(true);
    setErrorAsociar("");
    setExito("");
    try {
      const cliente = await asociarCliente(email.trim());
      setClientes((previos) => [...(previos ?? []), cliente]);
      setExito(`Cliente ${cliente.nombre} ${cliente.apellido} asociado.`);
      setEmail("");
    } catch (fallo) {
      setErrorAsociar((fallo as Error).message);
    } finally {
      setAsociando(false);
    }
  }

  return (
    <AppLayout activo="Inicio" rol="ASESOR_VENTAS">
      <header className="home-header">
        <div>
          <h1>{perfil?.nombre ? `Hola, ${perfil.nombre}` : "Hola"}</h1>
          <p>Gestiona tus clientes y registra siniestros en su nombre.</p>
        </div>
        <div className="home-user">
          <span className="material-symbols-outlined" aria-label="Notificaciones" role="img">notifications</span>
          <span className="home-avatar" aria-hidden="true">{iniciales(perfil)}</span>
        </div>
      </header>

      <div className="home-grid">
        <section className="home-panel" aria-labelledby="mis-clientes">
          <h2 id="mis-clientes">Mis clientes</h2>
          {error && <p role="alert" className="home-aviso">{error}</p>}
          {clientes === null && !error && (
            <p role="status" className="home-card-vacio">Cargando tus clientes…</p>
          )}
          {clientes?.length === 0 && (
            <p className="home-card-vacio">Aún no tienes clientes asociados.</p>
          )}
          {clientes && clientes.length > 0 && (
            <ul className="home-clientes">
              {clientes.map((cliente) => (
                <li key={cliente.cliente_id} className="home-cliente">
                  <span className="material-symbols-outlined" aria-hidden="true">person</span>
                  <span className="home-cliente-texto">
                    <strong>{cliente.nombre} {cliente.apellido}</strong>
                    <small>{cliente.email}</small>
                  </span>
                  <button
                    type="button"
                    className="cotizar-boton-secundario"
                    onClick={() => navigate("/siniestros/nuevo")}
                  >
                    Registrar siniestro
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="asociar">
          <h2 id="asociar" className="home-acciones-titulo">Asociar un cliente</h2>
          <form onSubmit={asociar} className="home-panel" aria-label="Asociar cliente">
            <div className="cotizar-campo cotizar-campo-ancho">
              <label htmlFor="email-cliente">Correo del cliente</label>
              <input
                id="email-cliente"
                type="email"
                value={email}
                required
                placeholder="cliente@correo.com"
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            {errorAsociar && <p role="alert" className="home-aviso">{errorAsociar}</p>}
            {exito && <p role="status" className="home-exito">{exito}</p>}
            <div className="cotizar-acciones">
              <button
                type="submit"
                className="cotizar-boton-primario"
                disabled={asociando || email.trim() === ""}
              >
                {asociando ? "Asociando…" : "Asociar cliente"}
              </button>
            </div>
          </form>
        </section>
      </div>
    </AppLayout>
  );
}

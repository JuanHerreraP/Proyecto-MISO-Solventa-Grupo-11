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

import { t, localeActual } from "../i18n";

const ACCIONES = [
  { icono: "error", get titulo() { return t("homePage.reportar_un_siniestro"); }, get detalle() { return t("homePage.registra_lo_ocurrido"); }, ruta: "/siniestros/nuevo" },
  { icono: "schedule", get titulo() { return t("homePage.consultar_estado_de_siniestro"); }, get detalle() { return t("homePage.sigue_tu_reclamacion"); }, ruta: null },
  { icono: "request_quote", get titulo() { return t("homePage.cotizar_un_nuevo_seguro"); }, get detalle() { return t("homePage.viaje_vida_dispositivos_y_mas"); }, ruta: "/cotizar" },
] as const;

const MOVIMIENTO_NOMBRE: Record<TipoMovimiento, string> = {
  get EMISION() { return t("homePage.emision_de_poliza"); },
  get PAGO_PRIMA_INICIAL() { return t("homePage.pago_de_prima_inicial"); },
  get ENDOSO() { return t("homePage.modificacion_contractual"); },
  get RENOVACION() { return t("homePage.renovacion"); },
  get CANCELACION() { return t("homePage.cancelacion"); },
  get DESEMBOLSO_INDEMNIZACION() { return t("homePage.pago_de_indemnizacion"); },
  get REEMBOLSO() { return t("homePage.reembolso"); },
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
  return new Date(anio, mes - 1, dia).toLocaleDateString(localeActual(), {
    day: "numeric", month: "short", year: "numeric",
  });
}

function formatearFechaMovimiento(iso: string): string {
  return new Date(iso).toLocaleDateString(localeActual(), {
    day: "numeric", month: "short", year: "numeric",
  });
}

/** Monto con signo según la perspectiva del cliente; "—" si el movimiento no tiene monto. */
function montoConSigno(movimiento: MovimientoPoliza): string {
  if (movimiento.monto === null) return "—";
  const valor = Number(movimiento.monto).toLocaleString(localeActual(), {
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
            <h1>{perfil?.nombre ? t("homePage.hola_nombre", { nombre: perfil.nombre }) : t("homePage.hola")}</h1>
            <p>{t("homePage.este_es_el_resumen_de")}</p>
          </div>
          <div className="home-user">
            <span className="material-symbols-outlined" aria-label={t("homePage.notificaciones")} role="img">notifications</span>
            <span className="home-avatar" aria-hidden="true">{iniciales(perfil)}</span>
          </div>
        </header>

        {location.state?.accesoDenegado && (
          <p role="alert" className="home-aviso">{t("homePage.no_tienes_permiso_para_acceder")}</p>
        )}

        <section className="home-cards" aria-label={t("homePage.resumen")}>
          <article className="home-card">
            <h2>{t("homePage.poliza_activa")}</h2>
            {polizaActiva ? (
              <>
                <p className="home-card-valor">{polizaActiva.nombre_ramo}</p>
                <p className="home-card-detalle">{polizaActiva.numero_poliza}</p>
                <span className="home-chip home-chip-verde">{t("homePage.vigente_hasta_formatearfecha", { formatearFecha: formatearFecha(polizaActiva.fecha_fin) })}</span>
              </>
            ) : (
              <p className="home-card-vacio">{t("homePage.aun_no_tienes_polizas_activas")}</p>
            )}
          </article>
          <article className="home-card">
            <h2>{t("homePage.proximo_pago")}</h2>
            <p className="home-card-vacio">{t("homePage.sin_pagos_programados")}</p>
          </article>
          <article className="home-card">
            <h2>{t("homePage.siniestros_abiertos")}</h2>
            <p className="home-card-vacio">{t("homePage.no_tienes_siniestros_en_curso")}</p>
          </article>
        </section>

        <div className="home-grid">
          <section className="home-panel" aria-labelledby="historial">
            <h2 id="historial">{t("homePage.historial_reciente")}</h2>
            <table>
              <thead>
                <tr><th>{t("homePage.fecha")}</th><th>{t("homePage.movimiento")}</th><th>{t("homePage.monto")}</th><th>{t("homePage.estado")}</th></tr>
              </thead>
              <tbody>
                {movimientos === null && (
                  <tr><td colSpan={4} className="home-card-vacio">{t("homePage.cargando_movimientos")}</td></tr>
                )}
                {movimientos !== null && movimientos.length === 0 && (
                  <tr><td colSpan={4} className="home-card-vacio">{t("homePage.todavia_no_hay_movimientos")}</td></tr>
                )}
                {movimientos?.map((movimiento) => (
                  <tr
                    key={movimiento.movimiento_id}
                    className="home-fila-clic"
                    onClick={() =>
                      navigate(`/polizas/${encodeURIComponent(movimiento.poliza_id)}/historial`)
                    }
                  >
                    <td>{formatearFechaMovimiento(movimiento.fecha)}</td>
                    <td>
                      {/* Botón real (teclado y lector de pantalla); su nombre incluye el texto visible. */}
                      <button
                        type="button"
                        className="home-fila-enlace"
                        onClick={(evento) => {
                          evento.stopPropagation();
                          navigate(`/polizas/${encodeURIComponent(movimiento.poliza_id)}/historial`);
                        }}
                      >
                        <strong>{MOVIMIENTO_NOMBRE[movimiento.tipo] ?? movimiento.tipo}</strong>
                        <span className="sr-only"> · {t("homePage.ver_historial_de_nombre_ramo", { nombre_ramo: movimiento.nombre_ramo })}</span>
                      </button>
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
            <h2 id="acciones" className="home-acciones-titulo">{t("homePage.acciones_rapidas")}</h2>
            <div className="home-acciones">
              {ACCIONES.map(({ icono, titulo, detalle, ruta }) => (
                <button
                  key={titulo}
                  type="button"
                  className="home-accion"
                  disabled={ruta === null}
                  title={ruta === null ? t("homePage.proximamente") : undefined}
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
      setExito(t("homePage.cliente_nombre_apellido_asociado", { nombre: cliente.nombre, apellido: cliente.apellido }));
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
          <h1>{perfil?.nombre ? t("homePage.hola_nombre", { nombre: perfil.nombre }) : t("homePage.hola")}</h1>
          <p>{t("homePage.gestiona_tus_clientes_y_registra")}</p>
        </div>
        <div className="home-user">
          <span className="material-symbols-outlined" aria-label={t("homePage.notificaciones")} role="img">notifications</span>
          <span className="home-avatar" aria-hidden="true">{iniciales(perfil)}</span>
        </div>
      </header>

      <div className="home-grid">
        <section className="home-panel" aria-labelledby="mis-clientes">
          <h2 id="mis-clientes">{t("homePage.mis_clientes")}</h2>
          {error && <p role="alert" className="home-aviso">{error}</p>}
          {clientes === null && !error && (
            <p role="status" className="home-card-vacio">{t("homePage.cargando_tus_clientes")}</p>
          )}
          {clientes?.length === 0 && (
            <p className="home-card-vacio">{t("homePage.aun_no_tienes_clientes_asociados")}</p>
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
                    {t("homePage.registrar_siniestro")}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="asociar">
          <h2 id="asociar" className="home-acciones-titulo">{t("homePage.asociar_un_cliente")}</h2>
          <form onSubmit={asociar} className="home-panel" aria-label={t("homePage.asociar_cliente")}>
            <div className="cotizar-campo cotizar-campo-ancho">
              <label htmlFor="email-cliente">{t("homePage.correo_del_cliente")}</label>
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
                {asociando ? t("homePage.asociando") : t("homePage.asociar_cliente")}
              </button>
            </div>
          </form>
        </section>
      </div>
    </AppLayout>
  );
}

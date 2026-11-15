import { Fragment, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil } from "../services/auth.service";
import {
  listarPagos,
  listarPrimasPendientes,
  obtenerComprobante,
  type Comprobante,
  type PagoResumen,
  type PrimaPendiente,
} from "../services/pagos.service";

const METODOS = { TARJETA: "Tarjeta", PSE: "PSE" } as const;
const ESTADOS = { APROBADO: "Pagado", PENDIENTE: "Pendiente", RECHAZADO: "Rechazado" } as const;
const CONCEPTOS = { COMPRA: "Prima", RENOVACION: "Renovación" } as const;

interface ComprobanteAbierto {
  pagoId: string;
  datos?: Comprobante;
  error?: string;
}

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", { day: "numeric", month: "short", year: "numeric" });
}

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString("es-CO", {
    style: "currency", currency: moneda, maximumFractionDigits: 0,
  });
}

function describirPendiente(prima: PrimaPendiente): string {
  if (prima.tipo === "RENOVACION") {
    return `Renovación — póliza ${prima.numero_poliza ?? prima.poliza_id}`;
  }
  if (prima.tipo === "COTIZACION") {
    return `${prima.nombre_ramo} — cotización ${prima.cotizacion_id}`;
  }
  return `${prima.nombre_ramo} — contrato por firmar`;
}

export default function PagosPage() {
  const [rol, setRol] = useState<string | null>(null);
  const [pagos, setPagos] = useState<PagoResumen[] | null>(null);
  const [pendientes, setPendientes] = useState<PrimaPendiente[] | null>(null);
  const [error, setError] = useState("");
  const [errorPendientes, setErrorPendientes] = useState("");
  const [comprobante, setComprobante] = useState<ComprobanteAbierto | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (perfil) => { if (activo) setRol(perfil.rol); },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    listarPagos().then(
      (datos) => { if (activo) setPagos(datos); },
      (fallo: Error) => { if (activo) setError(fallo.message); },
    );
    listarPrimasPendientes().then(
      (datos) => { if (activo) setPendientes(datos); },
      (fallo: Error) => { if (activo) setErrorPendientes(fallo.message); },
    );
    return () => { activo = false; };
  }, [navigate]);

  // El contrato solo se ofrece mientras falta firmarlo: es lo que deja la póliza por emitir.
  const firmasPendientes = new Set(
    (pendientes ?? []).filter((p) => p.tipo === "FIRMA_PENDIENTE").map((p) => p.cotizacion_id),
  );

  function accionPendiente(prima: PrimaPendiente) {
    const id = encodeURIComponent(prima.cotizacion_id);
    navigate(prima.accion === "FIRMAR" ? `/firma/${id}` : `/cotizar?cotizacion=${id}`);
  }

  async function alternarComprobante(pagoId: string) {
    if (comprobante?.pagoId === pagoId) {
      setComprobante(null);
      return;
    }
    setComprobante({ pagoId });
    try {
      const datos = await obtenerComprobante(pagoId);
      setComprobante((actual) => (actual?.pagoId === pagoId ? { pagoId, datos } : actual));
    } catch (fallo) {
      const mensaje = (fallo as Error).message;
      setComprobante((actual) => (actual?.pagoId === pagoId ? { pagoId, error: mensaje } : actual));
    }
  }

  return (
    <AppLayout activo="Pagos" rol={rol}>
      <header className="home-header">
        <div>
          <h1>Pagos</h1>
          <p>Gestiona tu método de pago y consulta tu historial de cobros.</p>
        </div>
      </header>

      <section className="home-panel pagos-metodo" aria-label="Método de pago">
        <span className="home-accion-icono material-symbols-outlined pagos-metodo-icono" aria-hidden="true">credit_card</span>
        <div className="pagos-metodo-texto">
          <strong>Método de pago</strong>
          <small>Aún no hay un método de pago registrado.</small>
        </div>
        <button type="button" className="pagos-boton" disabled title="Próximamente">
          <span className="material-symbols-outlined" aria-hidden="true">edit</span>
          Actualizar método de pago
        </button>
      </section>

      <section className="home-panel" aria-labelledby="pendientes-pagos">
        <h2 id="pendientes-pagos">Pendientes de pago</h2>
        {errorPendientes && <p role="alert" className="home-aviso">{errorPendientes}</p>}
        <table>
          <thead>
            <tr><th>Concepto</th><th>Valor</th><th>Fecha límite</th><th>Acción</th></tr>
          </thead>
          <tbody>
            {pendientes?.length === 0 && (
              <tr><td colSpan={4} className="home-card-vacio">No tienes pagos pendientes.</td></tr>
            )}
            {pendientes?.map((prima) => (
              <tr key={`${prima.tipo}-${prima.referencia_id}`}>
                <td>
                  {describirPendiente(prima)}
                  {prima.mensaje && <small className="home-card-vacio"> {prima.mensaje}</small>}
                </td>
                <td>{formatearMonto(prima.monto, prima.moneda)}</td>
                <td>{prima.fecha_limite ? formatearFecha(prima.fecha_limite) : "—"}</td>
                <td>
                  <button type="button" className="pagos-enlace" onClick={() => accionPendiente(prima)}>
                    {prima.accion === "FIRMAR" ? "Firmar contrato" : "Pagar"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="home-panel" aria-labelledby="historial-pagos">
        <h2 id="historial-pagos">Historial de pagos</h2>
        {error && <p role="alert" className="home-aviso">{error}</p>}
        <table>
          <thead>
            <tr><th>Fecha</th><th>Concepto</th><th>Método</th><th>Monto</th><th>Estado</th><th>Acciones</th></tr>
          </thead>
          <tbody>
            {pagos?.length === 0 && (
              <tr><td colSpan={6} className="home-card-vacio">Todavía no tienes pagos.</td></tr>
            )}
            {pagos?.map((pago) => (
              <Fragment key={pago.pago_id}>
                <tr>
                  <td>{formatearFecha(pago.creado_en)}</td>
                  <td>{CONCEPTOS[pago.concepto] ?? "Prima"} — cotización {pago.cotizacion_id}</td>
                  <td>{METODOS[pago.metodo]}</td>
                  <td>{formatearMonto(pago.monto, pago.moneda)}</td>
                  <td className={`pagos-estado pagos-estado-${pago.estado.toLowerCase()}`}>{ESTADOS[pago.estado]}</td>
                  <td>
                    {pago.estado === "APROBADO" ? (
                      <>
                        <button
                          type="button"
                          className="pagos-enlace"
                          aria-expanded={comprobante?.pagoId === pago.pago_id}
                          onClick={() => alternarComprobante(pago.pago_id)}
                        >
                          Comprobante
                        </button>
                        {firmasPendientes.has(pago.cotizacion_id) && (
                          <button
                            type="button"
                            className="pagos-enlace"
                            onClick={() => navigate(`/firma/${encodeURIComponent(pago.cotizacion_id)}`)}
                          >
                            Contrato
                          </button>
                        )}
                      </>
                    ) : (
                      <span className="home-card-vacio">—</span>
                    )}
                  </td>
                </tr>
                {comprobante?.pagoId === pago.pago_id && (
                  <tr>
                    <td colSpan={6}>
                      {!comprobante.datos && !comprobante.error && (
                        <p role="status" className="home-card-vacio">Cargando el comprobante…</p>
                      )}
                      {comprobante.error && (
                        <p role="alert" className="home-aviso">{comprobante.error}</p>
                      )}
                      {comprobante.datos && (
                        <dl className="cotizacion-datos" aria-label="Comprobante de pago">
                          <div><dt>Comprobante</dt><dd>{comprobante.datos.numero}</dd></div>
                          <div><dt>Concepto</dt><dd>{comprobante.datos.descripcion}</dd></div>
                          <div>
                            <dt>Valor pagado</dt>
                            <dd>{formatearMonto(comprobante.datos.monto, comprobante.datos.moneda)}</dd>
                          </div>
                          <div><dt>Método</dt><dd>{METODOS[comprobante.datos.metodo]}</dd></div>
                          <div><dt>Fecha de pago</dt><dd>{formatearFecha(comprobante.datos.pagado_en)}</dd></div>
                          {comprobante.datos.referencia_pasarela && (
                            <div><dt>Referencia</dt><dd>{comprobante.datos.referencia_pasarela}</dd></div>
                          )}
                        </dl>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </section>
    </AppLayout>
  );
}

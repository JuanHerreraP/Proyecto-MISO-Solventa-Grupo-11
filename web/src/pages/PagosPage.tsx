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

import { t, localeActual } from "../i18n";

const METODOS = { get TARJETA() { return t("pagosPage.tarjeta"); }, PSE: "PSE" } as const;
const ESTADOS = { get APROBADO() { return t("pagosPage.pagado"); }, get PENDIENTE() { return t("pagosPage.pendiente"); }, get RECHAZADO() { return t("pagosPage.rechazado"); } } as const;
const CONCEPTOS = { get COMPRA() { return t("pagosPage.prima"); }, get RENOVACION() { return t("pagosPage.renovacion"); } } as const;

interface ComprobanteAbierto {
  pagoId: string;
  datos?: Comprobante;
  error?: string;
}

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString(localeActual(), { day: "numeric", month: "short", year: "numeric" });
}

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString(localeActual(), {
    style: "currency", currency: moneda, maximumFractionDigits: 0,
  });
}

function describirPendiente(prima: PrimaPendiente): string {
  if (prima.tipo === "RENOVACION") {
    return t("pagosPage.renovacion_poliza_valor", { valor: prima.numero_poliza ?? prima.poliza_id });
  }
  if (prima.tipo === "COTIZACION") {
    return t("pagosPage.nombre_ramo_cotizacion_cotizacion_id", { nombre_ramo: prima.nombre_ramo, cotizacion_id: prima.cotizacion_id });
  }
  return t("pagosPage.nombre_ramo_contrato_por_firmar", { nombre_ramo: prima.nombre_ramo });
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
          <h1>{t("pagosPage.pagos")}</h1>
          <p>{t("pagosPage.gestiona_tu_metodo_de_pago")}</p>
        </div>
      </header>

      <section className="home-panel pagos-metodo" aria-label={t("pagosPage.metodo_de_pago")}>
        <span className="home-accion-icono material-symbols-outlined pagos-metodo-icono" aria-hidden="true">credit_card</span>
        <div className="pagos-metodo-texto">
          <strong>{t("pagosPage.metodo_de_pago")}</strong>
          <small>{t("pagosPage.aun_no_hay_un_metodo")}</small>
        </div>
        <button type="button" className="pagos-boton" disabled title={t("pagosPage.proximamente")}>
          <span className="material-symbols-outlined" aria-hidden="true">edit</span>
          {t("pagosPage.actualizar_metodo_de_pago")}
        </button>
      </section>

      <section className="home-panel" aria-labelledby="pendientes-pagos">
        <h2 id="pendientes-pagos">{t("pagosPage.pendientes_de_pago")}</h2>
        {errorPendientes && <p role="alert" className="home-aviso">{errorPendientes}</p>}
        <table>
          <thead>
            <tr><th>{t("pagosPage.concepto")}</th><th>{t("pagosPage.valor")}</th><th>{t("pagosPage.fecha_limite")}</th><th>{t("pagosPage.accion")}</th></tr>
          </thead>
          <tbody>
            {pendientes?.length === 0 && (
              <tr><td colSpan={4} className="home-card-vacio">{t("pagosPage.no_tienes_pagos_pendientes")}</td></tr>
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
                    {prima.accion === "FIRMAR" ? t("pagosPage.firmar_contrato") : t("pagosPage.pagar")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="home-panel" aria-labelledby="historial-pagos">
        <h2 id="historial-pagos">{t("pagosPage.historial_de_pagos")}</h2>
        {error && <p role="alert" className="home-aviso">{error}</p>}
        <table>
          <thead>
            <tr><th>{t("pagosPage.fecha")}</th><th>{t("pagosPage.concepto")}</th><th>{t("pagosPage.metodo")}</th><th>{t("pagosPage.monto")}</th><th>{t("pagosPage.estado")}</th><th>{t("pagosPage.acciones")}</th></tr>
          </thead>
          <tbody>
            {pagos?.length === 0 && (
              <tr><td colSpan={6} className="home-card-vacio">{t("pagosPage.todavia_no_tienes_pagos")}</td></tr>
            )}
            {pagos?.map((pago) => (
              <Fragment key={pago.pago_id}>
                <tr>
                  <td>{formatearFecha(pago.creado_en)}</td>
                  <td>{CONCEPTOS[pago.concepto] ?? t("pagosPage.prima")} {t("pagosPage.cotizacion_cotizacion_id", { cotizacion_id: pago.cotizacion_id })}</td>
                  <td>{METODOS[pago.metodo]}</td>
                  <td>{formatearMonto(pago.monto, pago.moneda)}</td>
                  <td className={`pagos-estado pagos-estado-${pago.estado.toLowerCase()}`}>{ESTADOS[pago.estado]}</td>
                  <td>
                    {pago.estado === "APROBADO" ? (
                      <div className="pagos-acciones">
                        <button
                          type="button"
                          className="pagos-enlace"
                          aria-expanded={comprobante?.pagoId === pago.pago_id}
                          onClick={() => alternarComprobante(pago.pago_id)}
                        >
                          {t("pagosPage.comprobante")}
                        </button>
                        {firmasPendientes.has(pago.cotizacion_id) && (
                          <button
                            type="button"
                            className="pagos-enlace"
                            onClick={() => navigate(`/firma/${encodeURIComponent(pago.cotizacion_id)}`)}
                          >
                            {t("pagosPage.contrato")}
                          </button>
                        )}
                      </div>
                    ) : (
                      <span className="home-card-vacio">—</span>
                    )}
                  </td>
                </tr>
                {comprobante?.pagoId === pago.pago_id && (
                  <tr>
                    <td colSpan={6}>
                      {!comprobante.datos && !comprobante.error && (
                        <p role="status" className="home-card-vacio">{t("pagosPage.cargando_el_comprobante")}</p>
                      )}
                      {comprobante.error && (
                        <p role="alert" className="home-aviso">{comprobante.error}</p>
                      )}
                      {comprobante.datos && (
                        <dl className="cotizacion-datos" aria-label={t("pagosPage.comprobante_de_pago")}>
                          <div><dt>{t("pagosPage.comprobante")}</dt><dd>{comprobante.datos.numero}</dd></div>
                          <div><dt>{t("pagosPage.concepto")}</dt><dd>{comprobante.datos.descripcion}</dd></div>
                          <div>
                            <dt>{t("pagosPage.valor_pagado")}</dt>
                            <dd>{formatearMonto(comprobante.datos.monto, comprobante.datos.moneda)}</dd>
                          </div>
                          <div><dt>{t("pagosPage.metodo")}</dt><dd>{METODOS[comprobante.datos.metodo]}</dd></div>
                          <div><dt>{t("pagosPage.fecha_de_pago")}</dt><dd>{formatearFecha(comprobante.datos.pagado_en)}</dd></div>
                          {comprobante.datos.referencia_pasarela && (
                            <div><dt>{t("pagosPage.referencia")}</dt><dd>{comprobante.datos.referencia_pasarela}</dd></div>
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

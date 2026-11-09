import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil } from "../services/auth.service";
import { listarPagos, type PagoResumen } from "../services/pagos.service";

const METODOS = { TARJETA: "Tarjeta", PSE: "PSE" } as const;
const ESTADOS = { APROBADO: "Pagado", PENDIENTE: "Pendiente", RECHAZADO: "Rechazado" } as const;

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", { day: "numeric", month: "short", year: "numeric" });
}

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString("es-CO", {
    style: "currency", currency: moneda, maximumFractionDigits: 0,
  });
}

export default function PagosPage() {
  const [rol, setRol] = useState<string | null>(null);
  const [pagos, setPagos] = useState<PagoResumen[] | null>(null);
  const [error, setError] = useState("");
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
    return () => { activo = false; };
  }, [navigate]);

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

      <section className="home-panel" aria-labelledby="historial-pagos">
        <h2 id="historial-pagos">Historial de pagos</h2>
        {error && <p role="alert" className="home-aviso">{error}</p>}
        <table>
          <thead>
            <tr><th>Fecha</th><th>Concepto</th><th>Método</th><th>Monto</th><th>Estado</th><th>Contrato</th></tr>
          </thead>
          <tbody>
            {pagos?.length === 0 && (
              <tr><td colSpan={6} className="home-card-vacio">Todavía no tienes pagos.</td></tr>
            )}
            {pagos?.map((pago) => (
              <tr key={pago.pago_id}>
                <td>{formatearFecha(pago.creado_en)}</td>
                <td>Prima — cotización {pago.cotizacion_id}</td>
                <td>{METODOS[pago.metodo]}</td>
                <td>{formatearMonto(pago.monto, pago.moneda)}</td>
                <td className={`pagos-estado pagos-estado-${pago.estado.toLowerCase()}`}>{ESTADOS[pago.estado]}</td>
                <td>
                  {pago.estado === "APROBADO" ? (
                    <button
                      type="button"
                      className="pagos-enlace"
                      onClick={() => navigate(`/firma/${encodeURIComponent(pago.cotizacion_id)}`)}
                    >
                      Contrato
                    </button>
                  ) : (
                    <span className="home-card-vacio">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </AppLayout>
  );
}

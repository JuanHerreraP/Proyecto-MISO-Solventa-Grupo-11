import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { cerrarSesion } from "../services/session";
import {
  ROLES_ADMINISTRACION_SOCIOS,
  ROLES_CREAR_ASESOR,
  ROLES_OPERACIONES_SINIESTROS,
} from "../types/permisos";
import logoSolventa from "../assets/solventa-logo.png";
import "../styles/home.css";

const MENU = [
  { icono: "home", texto: "Inicio", ruta: "/home" },
  { icono: "description", texto: "Mis cotizaciones", ruta: "/cotizaciones" },
  { icono: "shield", texto: "Mis pólizas", ruta: "/polizas" },
  { icono: "error", texto: "Siniestros", ruta: "/siniestros" },
  { icono: "payments", texto: "Pagos", ruta: "/pagos" },
  { icono: "person", texto: "Perfil", ruta: null },
] as const;

type Props = {
  activo:
    | "Inicio"
    | "Pagos"
    | "Mis cotizaciones"
    | "Mis pólizas"
    | "Siniestros"
    | "Bandeja de siniestros";
  rol: string | null;
  children: ReactNode;
};

/** Barra lateral y contenedor común de las pantallas del cliente. */
export default function AppLayout({ activo, rol, children }: Props) {
  const navigate = useNavigate();
  const [errorSesion, setErrorSesion] = useState("");
  const puedeCrearSocios = ROLES_ADMINISTRACION_SOCIOS.some((permitido) => permitido === rol);
  const puedeCrearAsesor = ROLES_CREAR_ASESOR.some((permitido) => permitido === rol);
  const evaluaSiniestros = ROLES_OPERACIONES_SINIESTROS.some((permitido) => permitido === rol);

  return (
    <div className="home-layout">
      <aside className="home-sidebar">
        <div className="home-brand">
          <img src={logoSolventa} alt="" className="home-brand-logo" aria-hidden="true" />
          Solventa
        </div>
        <nav aria-label="Principal">
          {MENU.map(({ icono, texto, ruta }) => (
            <button
              key={texto}
              type="button"
              className="home-nav-item"
              aria-current={texto === activo ? "page" : undefined}
              disabled={ruta === null}
              title={ruta === null ? "Próximamente" : undefined}
              onClick={ruta ? () => navigate(ruta) : undefined}
            >
              <span className="material-symbols-outlined" aria-hidden="true">{icono}</span>
              {texto}
            </button>
          ))}
          {evaluaSiniestros && (
            <button
              type="button"
              className="home-nav-item"
              aria-current={activo === "Bandeja de siniestros" ? "page" : undefined}
              onClick={() => navigate("/operaciones/siniestros")}
            >
              <span className="material-symbols-outlined" aria-hidden="true">fact_check</span>
              Bandeja de siniestros
            </button>
          )}
          {puedeCrearSocios && (
            <button type="button" className="home-nav-item" onClick={() => navigate("/admin/socios/nuevo")}>
              <span className="material-symbols-outlined" aria-hidden="true">group_add</span>
              Crear un nuevo socio
            </button>
          )}
          {puedeCrearAsesor && (
            <button type="button" className="home-nav-item" onClick={() => navigate("/admin/asesores/nuevo")}>
              <span className="material-symbols-outlined" aria-hidden="true">support_agent</span>
              Crear un asesor de ventas
            </button>
          )}
        </nav>
        <button
          type="button"
          className="home-nav-item"
          onClick={() => {
            setErrorSesion("");
            void cerrarSesion().then(() => navigate("/login", { replace: true }))
              .catch(() => setErrorSesion("No fue posible cerrar la sesión. Inténtalo nuevamente."));
          }}
        >
          <span className="material-symbols-outlined" aria-hidden="true">logout</span>
          Cerrar sesión
        </button>
      </aside>
      <main className="home-main">
        {errorSesion && <p role="alert" className="home-aviso">{errorSesion}</p>}
        {children}
      </main>
    </div>
  );
}

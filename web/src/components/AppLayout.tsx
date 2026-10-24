import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { cerrarSesion } from "../services/session";
import { ROLES_ADMINISTRACION_SOCIOS } from "../types/permisos";
import logoSolventa from "../assets/solventa-logo.png";
import "../styles/home.css";

const MENU = [
  { icono: "home", texto: "Inicio", ruta: "/home" },
  { icono: "request_quote", texto: "Cotizar", ruta: "/cotizar" },
  { icono: "description", texto: "Mis pólizas", ruta: null },
  { icono: "error", texto: "Siniestros", ruta: null },
  { icono: "payments", texto: "Pagos", ruta: "/pagos" },
  { icono: "person", texto: "Perfil", ruta: null },
] as const;

type Props = { activo: "Inicio" | "Pagos" | "Cotizar"; rol: string | null; children: ReactNode };

/** Barra lateral y contenedor común de las pantallas del cliente. */
export default function AppLayout({ activo, rol, children }: Props) {
  const navigate = useNavigate();
  const [errorSesion, setErrorSesion] = useState("");
  const puedeCrearSocios = ROLES_ADMINISTRACION_SOCIOS.some((permitido) => permitido === rol);

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
          {puedeCrearSocios && (
            <button type="button" className="home-nav-item" onClick={() => navigate("/admin/socios/nuevo")}>
              <span className="material-symbols-outlined" aria-hidden="true">group_add</span>
              Crear un nuevo socio
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

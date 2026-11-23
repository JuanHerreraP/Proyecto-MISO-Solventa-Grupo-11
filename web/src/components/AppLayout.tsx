import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { cerrarSesion } from "../services/session";
import {
  ROLES_ADMINISTRACION_SOCIOS,
  ROLES_CREAR_ASESOR,
  ROLES_OPERACIONES_SINIESTROS,
  ROLES_AUDITORIA,
} from "../types/permisos";
import logoSolventa from "../assets/solventa-logo.png";
import "../styles/home.css";

import { t } from "../i18n";
import SelectorIdioma from "../i18n/SelectorIdioma";

// `id` coincide con la prop `activo` de las páginas; `clave` es el texto traducido del menú.
const MENU = [
  { id: "Inicio", icono: "home", clave: "appLayout.inicio", ruta: "/home" },
  { id: "Mis cotizaciones", icono: "description", clave: "appLayout.mis_cotizaciones", ruta: "/cotizaciones" },
  { id: "Mis pólizas", icono: "shield", clave: "appLayout.mis_polizas", ruta: "/polizas" },
  { id: "Siniestros", icono: "error", clave: "appLayout.siniestros", ruta: "/siniestros" },
  { id: "Pagos", icono: "payments", clave: "appLayout.pagos", ruta: "/pagos" },
  { id: "Perfil", icono: "person", clave: "appLayout.perfil", ruta: "/perfil" },
] as const;

type Props = {
  activo:
    | "Inicio"
    | "Pagos"
    | "Mis cotizaciones"
    | "Mis pólizas"
    | "Siniestros"
    | "Perfil"
    | "Bandeja de siniestros"
    | "Historial contractual";
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
  const esAuditoria = ROLES_AUDITORIA.some((permitido) => permitido === rol);

  return (
    <div className="home-layout">
      <aside className="home-sidebar">
        <div className="home-brand">
          <img src={logoSolventa} alt="" className="home-brand-logo" aria-hidden="true" />
          Solventa
        </div>
        <nav aria-label={t("appLayout.principal")}>
          {MENU.map(({ id, icono, clave, ruta }) => (
            <button
              key={id}
              type="button"
              className="home-nav-item"
              aria-current={id === activo ? "page" : undefined}
              disabled={ruta === null}
              title={ruta === null ? t("appLayout.proximamente") : undefined}
              onClick={ruta ? () => navigate(ruta) : undefined}
            >
              <span className="material-symbols-outlined" aria-hidden="true">{icono}</span>
              {t(clave)}
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
              {t("appLayout.bandeja_de_siniestros")}
            </button>
          )}
          {esAuditoria && (
            <button
              type="button"
              className="home-nav-item"
              aria-current={activo === "Historial contractual" ? "page" : undefined}
              onClick={() => navigate("/auditoria/historial")}
            >
              <span className="material-symbols-outlined" aria-hidden="true">manage_search</span>
              {t("appLayout.historial_contractual")}
            </button>
          )}
          {puedeCrearSocios && (
            <button type="button" className="home-nav-item" onClick={() => navigate("/admin/socios/nuevo")}>
              <span className="material-symbols-outlined" aria-hidden="true">group_add</span>
              {t("appLayout.crear_un_nuevo_socio")}
            </button>
          )}
          {puedeCrearAsesor && (
            <button type="button" className="home-nav-item" onClick={() => navigate("/admin/asesores/nuevo")}>
              <span className="material-symbols-outlined" aria-hidden="true">support_agent</span>
              {t("appLayout.crear_un_asesor_de_ventas")}
            </button>
          )}
          {puedeCrearAsesor && (
            <button type="button" className="home-nav-item" onClick={() => navigate("/admin/auditores/nuevo")}>
              <span className="material-symbols-outlined" aria-hidden="true">manage_search</span>
              {t("appLayout.crear_un_analista_de_cumplimiento")}
            </button>
          )}
        </nav>
        <SelectorIdioma className="home-selector-idioma" />
        <button
          type="button"
          className="home-nav-item"
          onClick={() => {
            setErrorSesion("");
            void cerrarSesion().then(() => navigate("/login", { replace: true }))
              .catch(() => setErrorSesion(t("appLayout.no_fue_posible_cerrar_la")));
          }}
        >
          <span className="material-symbols-outlined" aria-hidden="true">logout</span>
          {t("appLayout.cerrar_sesion")}
        </button>
      </aside>
      <main className="home-main">
        {errorSesion && <p role="alert" className="home-aviso">{errorSesion}</p>}
        {children}
      </main>
    </div>
  );
}

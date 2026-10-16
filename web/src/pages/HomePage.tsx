import { ROLES_ADMINISTRACION_SOCIOS } from "../types/permisos";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { cerrarSesion } from "../services/session";
import { obtenerPerfil } from "../services/auth.service";

export default function HomePage() {
  const [rol, setRol] = useState<string | null>(null);
  const [errorSesion, setErrorSesion] = useState("");
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (perfil) => { if (activo) setRol(perfil.rol); },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    return () => { activo = false; };
  }, [navigate]);

  const puedeCrearSocios = ROLES_ADMINISTRACION_SOCIOS.some((permitido) => permitido === rol);
  return (
    <main>
      <h1>
        Home
      </h1>
      <p>Pagina de inicio de Solventa</p>
      {location.state?.accesoDenegado && (
        <p role="alert">No tienes permiso para acceder a esa página.</p>
      )}
      <button type="button" onClick={() => {
        setErrorSesion("");
        void cerrarSesion().then(() => navigate("/login", { replace: true }))
          .catch(() => setErrorSesion("No fue posible cerrar la sesión. Inténtalo nuevamente."));
      }}>Cerrar sesión</button>
      {errorSesion && <p role="alert">{errorSesion}</p>}
      {puedeCrearSocios && (
        <button type="button" onClick={() => navigate("/admin/socios/nuevo")}>
          Crear un nuevo socio
        </button>
      )}
    </main>
  );
}

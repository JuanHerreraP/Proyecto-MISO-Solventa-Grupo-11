import RutaProtegida from "./components/auth/RutaProtegida";
import { ROLES_ADMINISTRACION_SOCIOS } from "./types/permisos";
import { useEffect, useState } from "react";
import { iniciarControlSesion, restaurarSesion } from "./services/session";
import {
  Navigate,
  useNavigate,
  Route,
  Routes,
} from "react-router-dom";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import HomePage from "./pages/HomePage";
import PagosPage from "./pages/PagosPage";
import CotizarPage from "./pages/CotizarPage";
import CotizacionesPage from "./pages/CotizacionesPage";
import SocioRegistrationPage from "./pages/SocioRegistrationPage";

function App() {
  const navigate = useNavigate();
  const [sesionLista, setSesionLista] = useState(false);
  useEffect(() => {
    let activo = true;
    void restaurarSesion().finally(() => { if (activo) setSesionLista(true); });
    return () => { activo = false; };
  }, []);
  useEffect(() => {
    const detener = iniciarControlSesion();
    const expirada = () => navigate("/login", { replace: true });
    window.addEventListener("sesion-expirada", expirada);
    return () => {
      detener();
      window.removeEventListener("sesion-expirada", expirada);
    };
  }, [navigate]);
  if (!sesionLista) return <p role="status">Cargando sesión…</p>;
  return (
    <Routes>
      <Route
        path="/"
        element={<Navigate to="/login" replace />}
      />

      <Route
        path="/login"
        element={<LoginPage />}
      />

      <Route
        path="/registro"
        element={<RegisterPage />}
      />

      <Route
        path="/home"
        element={<RutaProtegida><HomePage /></RutaProtegida>}
      />

      <Route
        path="/pagos"
        element={<RutaProtegida><PagosPage /></RutaProtegida>}
      />

      <Route
        path="/cotizar"
        element={<RutaProtegida><CotizarPage /></RutaProtegida>}
      />

      <Route
        path="/cotizaciones"
        element={<RutaProtegida><CotizacionesPage /></RutaProtegida>}
      />

      <Route
        path="/admin/socios/nuevo"
        element={
          <RutaProtegida roles={ROLES_ADMINISTRACION_SOCIOS}>
            <SocioRegistrationPage />
          </RutaProtegida>
        }
      />
    </Routes>
  );
}

export default App;

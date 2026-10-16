import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import HomePage from "./pages/HomePage";
import SocioRegistrationPage from "./pages/SocioRegistrationPage";

function App() {
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
        element={<HomePage />}
      />

      <Route
        path="/admin/socios/nuevo"
        element={<SocioRegistrationPage />}
      />
    </Routes>
  );
}

export default App;

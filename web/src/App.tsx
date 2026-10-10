import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import HomePage from "./pages/HomePage";

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
    </Routes>
  );
}

export default App;

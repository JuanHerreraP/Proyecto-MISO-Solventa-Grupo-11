import {
  type FormEvent,
  useState,
} from "react";

import {
  Link,
  useNavigate,
} from "react-router-dom";

import AuthLayout from "../components/auth/AuthLayout";
import { login } from "../services/auth.service";
import { guardarAccessToken, guardarSesion } from "../services/session";


import { t } from "../i18n";

export default function LoginPage() {
  const [email, setEmail] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState(false);

  const [loading, setLoading] =
    useState(false);

  const navigate = useNavigate();


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");
    setSuccess(false);
    setLoading(true);
    guardarAccessToken(null);

    try {
      const response = await login({
        email,
        password,
      });

      guardarSesion(response);

      setSuccess(true);
      navigate("/home");

    } catch (error) {
      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError(
          t("loginPage.no_fue_posible_iniciar_sesion"),
        );
      }
    } finally {
      setLoading(false);
    }
  }


  return (
    <AuthLayout>
      <div className="login-container">

        <h2>
          {t("loginPage.inicia_sesion")}
        </h2>

        <p className="login-subtitle">
          {t("loginPage.accede_a_tu_cuenta_de")}
        </p>


        <form
          className="login-form"
          onSubmit={handleSubmit}
        >

          <label htmlFor="email">
            {t("loginPage.correo_electronico")}
          </label>

          <input
            id="email"
            type="email"
            placeholder="maria.torres@correo.com"
            value={email}
            onChange={(event) =>
              setEmail(event.target.value)
            }
            required
          />


          <label htmlFor="password">
            {t("loginPage.contrasena")}
          </label>

          <input
            id="password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            required
          />


          <div className="login-actions">
            <button
              type="button"
              className="forgot-password"
            >
              {t("loginPage.olvidaste_tu_contrasena")}
            </button>
          </div>


          {error && (
            <div
              className="login-error"
              role="alert"
            >
              {error}
            </div>
          )}


          {success && (
            <div
              className="login-success"
              role="status"
            >
              {t("loginPage.inicio_de_sesion_exitoso")}
            </div>
          )}


          <button
            type="submit"
            className="primary-button"
            disabled={loading}
          >
            {loading
              ? t("loginPage.ingresando")
              : t("loginPage.iniciar_sesion")}
          </button>

        </form>


        <p className="register-link">
          {t("loginPage.nuevo_en_solventa")}{" "}
          <Link to="/registro">
            {t("loginPage.crea_tu_cuenta")}
          </Link>
        </p>

      </div>
    </AuthLayout>
  );
}

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

    try {
      const response = await login({
        email,
        password,
      });

      console.log(
        "Login exitoso:",
        response,
      );

      setSuccess(true);
      navigate("/home");

    } catch (error) {
      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError(
          "No fue posible iniciar sesión.",
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
          Inicia sesión
        </h2>

        <p className="login-subtitle">
          Accede a tu cuenta de Solventa para continuar
          con tu proceso.
        </p>


        <form
          className="login-form"
          onSubmit={handleSubmit}
        >

          <label htmlFor="email">
            Correo electrónico
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
            Contraseña
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
              ¿Olvidaste tu contraseña?
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
              Inicio de sesión exitoso.
            </div>
          )}


          <button
            type="submit"
            className="primary-button"
            disabled={loading}
          >
            {loading
              ? "Ingresando..."
              : "Iniciar sesión →"}
          </button>

        </form>


        <p className="register-link">
          ¿Nuevo en Solventa?{" "}
          <Link to="/registro">
            Crea tu cuenta
          </Link>
        </p>

      </div>
    </AuthLayout>
  );
}
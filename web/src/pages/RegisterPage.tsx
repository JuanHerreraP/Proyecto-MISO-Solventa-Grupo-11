import {
  type FormEvent,
  useState,
} from "react";

import {
  Link,
  useNavigate,
} from "react-router-dom";

import AuthLayout from "../components/auth/AuthLayout";
import { register } from "../services/auth.service";

import type {
  RegisterRequest,
} from "../types/auth";

export default function RegisterPage() {
  const navigate = useNavigate();

  const [form, setForm] =
    useState<RegisterRequest>({
      nombre: "",
      apellido: "",
      email: "",
      password: "",
      tipo_documento: "CC",
      numero_documento: "",
      fecha_nacimiento: "",
      acepta_validacion_identidad: false,
    });

  const [confirmPassword, setConfirmPassword] =
    useState("");

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  function actualizarCampo<
    K extends keyof RegisterRequest,
  >(
    campo: K,
    valor: RegisterRequest[K],
  ) {
    setForm((actual) => ({
      ...actual,
      [campo]: valor,
    }));
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (form.password.length < 8) {
      setError(
        "La contraseña debe tener mínimo 8 caracteres.",
      );
      return;
    }

    if (form.password !== confirmPassword) {
      setError(
        "Las contraseñas no coinciden.",
      );
      return;
    }

    if (!form.acepta_validacion_identidad) {
      setError(
        "Debes autorizar la validación de identidad para continuar.",
      );
      return;
    }

    setLoading(true);

    try {
      const response = await register(form);

      setSuccess(
        `Cuenta creada correctamente. Bienvenido, ${response.nombre}.`,
      );

      setTimeout(() => {
        navigate("/login");
      }, 1500);
    } catch (error) {
      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError(
          "No fue posible crear la cuenta.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Crea tu cuenta en menos de 3 minutos"
      description="Con tu cuenta podrás autorizar el uso de tu información financiera, ver tu perfil de riesgo y cotizar tu seguro de vida hipotecario al instante."
      benefits={[
        "Verificación de identidad segura",
        "Tus datos protegidos durante todo el proceso",
      ]}
    >
      <div className="register-container">
        <h2>Crear cuenta</h2>

        <p className="register-subtitle">
          Completa tus datos para comenzar tu proceso
          de contratación.
        </p>

        <form
          className="register-form"
          onSubmit={handleSubmit}
        >
          <div className="register-row">
            <div className="register-field">
              <label htmlFor="nombre">
                Nombre
              </label>

              <input
                id="nombre"
                type="text"
                placeholder="María Fernanda"
                value={form.nombre}
                onChange={(event) =>
                  actualizarCampo(
                    "nombre",
                    event.target.value,
                  )
                }
                required
              />
            </div>

            <div className="register-field">
              <label htmlFor="apellido">
                Apellido
              </label>

              <input
                id="apellido"
                type="text"
                placeholder="Torres"
                value={form.apellido}
                onChange={(event) =>
                  actualizarCampo(
                    "apellido",
                    event.target.value,
                  )
                }
                required
              />
            </div>
          </div>

          <div className="register-field">
            <label htmlFor="register-email">
              Correo electrónico
            </label>

            <input
              id="register-email"
              type="email"
              placeholder="maria.torres@correo.com"
              value={form.email}
              onChange={(event) =>
                actualizarCampo(
                  "email",
                  event.target.value,
                )
              }
              required
            />
          </div>

          <div className="register-row">
            <div className="register-field register-document-type">
              <label htmlFor="tipo-documento">
                Tipo documento
              </label>

              <select
                id="tipo-documento"
                value={form.tipo_documento}
                onChange={(event) =>
                  actualizarCampo(
                    "tipo_documento",
                    event.target.value,
                  )
                }
              >
                <option value="CC">
                  Cédula
                </option>

                <option value="CE">
                  Cédula extranjería
                </option>

                <option value="PAS">
                  Pasaporte
                </option>
              </select>
            </div>

            <div className="register-field">
              <label htmlFor="numero-documento">
                Número de documento
              </label>

              <input
                id="numero-documento"
                type="text"
                placeholder="1 020 456 789"
                value={form.numero_documento}
                onChange={(event) =>
                  actualizarCampo(
                    "numero_documento",
                    event.target.value,
                  )
                }
                required
              />
            </div>
          </div>

          <div className="register-field">
            <label htmlFor="fecha-nacimiento">
              Fecha de nacimiento
            </label>

            <input
              id="fecha-nacimiento"
              type="date"
              value={form.fecha_nacimiento}
              onChange={(event) =>
                actualizarCampo(
                  "fecha_nacimiento",
                  event.target.value,
                )
              }
              required
            />
          </div>

          <div className="register-field">
            <label htmlFor="register-password">
              Contraseña
            </label>

            <input
              id="register-password"
              type="password"
              placeholder="Mínimo 8 caracteres"
              value={form.password}
              onChange={(event) =>
                actualizarCampo(
                  "password",
                  event.target.value,
                )
              }
              minLength={8}
              required
            />
          </div>

          <div className="register-field">
            <label htmlFor="confirm-password">
              Confirmar contraseña
            </label>

            <input
              id="confirm-password"
              type="password"
              placeholder="Repite tu contraseña"
              value={confirmPassword}
              onChange={(event) =>
                setConfirmPassword(
                  event.target.value,
                )
              }
              required
            />
          </div>

          <label className="consent-checkbox">
            <input
              type="checkbox"
              checked={
                form.acepta_validacion_identidad
              }
              onChange={(event) =>
                actualizarCampo(
                  "acepta_validacion_identidad",
                  event.target.checked,
                )
              }
            />

            <span>
              Acepto los términos y condiciones y la política de tratamiento
              de datos de Solventa
            </span>
          </label>

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
              {success}
            </div>
          )}

          <button
            type="submit"
            className="primary-button"
            disabled={loading}
          >
            {loading
              ? "Validando identidad..."
              : "Crear cuenta y continuar →"}
          </button>
        </form>

        <p className="register-link">
          ¿Ya tienes cuenta?{" "}
          <Link to="/login">
            Inicia sesión
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
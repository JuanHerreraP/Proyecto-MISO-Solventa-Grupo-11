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

import { t } from "../i18n";

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
        t("registerPage.la_contrasena_debe_tener_minimo"),
      );
      return;
    }

    if (form.password !== confirmPassword) {
      setError(
        t("registerPage.las_contrasenas_no_coinciden"),
      );
      return;
    }

    if (!form.acepta_validacion_identidad) {
      setError(
        t("registerPage.debes_autorizar_la_validacion_de"),
      );
      return;
    }

    setLoading(true);

    try {
      const response = await register(form);

      setSuccess(
        t("registerPage.cuenta_creada_correctamente_bienvenido_nombre", { nombre: response.nombre }),
      );

      setTimeout(() => {
        navigate("/login");
      }, 1500);
    } catch (error) {
      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError(
          t("registerPage.no_fue_posible_crear_la"),
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title={t("registerPage.crea_tu_cuenta_en_menos")}
      description={t("registerPage.con_tu_cuenta_podras_autorizar")}
      benefits={[
        t("registerPage.verificacion_de_identidad_segura"),
        t("registerPage.tus_datos_protegidos_durante_todo"),
      ]}
    >
      <div className="register-container">
        <h2>{t("registerPage.crear_cuenta")}</h2>

        <p className="register-subtitle">
          {t("registerPage.completa_tus_datos_para_comenzar")}
        </p>

        <form
          className="register-form"
          onSubmit={handleSubmit}
        >
          <div className="register-row">
            <div className="register-field">
              <label htmlFor="nombre">
                {t("registerPage.nombre")}
              </label>

              <input
                id="nombre"
                type="text"
                placeholder={t("registerPage.maria_fernanda")}
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
                {t("registerPage.apellido")}
              </label>

              <input
                id="apellido"
                type="text"
                placeholder={t("registerPage.torres")}
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
              {t("registerPage.correo_electronico")}
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
                {t("registerPage.tipo_documento")}
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
                  {t("registerPage.cedula")}
                </option>

                <option value="CE">
                  {t("registerPage.cedula_extranjeria")}
                </option>

                <option value="PAS">
                  {t("registerPage.pasaporte")}
                </option>
              </select>
            </div>

            <div className="register-field">
              <label htmlFor="numero-documento">
                {t("registerPage.numero_de_documento")}
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
              {t("registerPage.fecha_de_nacimiento")}
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
              {t("registerPage.contrasena")}
            </label>

            <input
              id="register-password"
              type="password"
              placeholder={t("registerPage.minimo_8_caracteres")}
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
              {t("registerPage.confirmar_contrasena")}
            </label>

            <input
              id="confirm-password"
              type="password"
              placeholder={t("registerPage.repite_tu_contrasena")}
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
              {t("registerPage.acepto_los_terminos_y_condiciones")}
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
              ? t("registerPage.validando_identidad")
              : t("registerPage.crear_cuenta_y_continuar")}
          </button>
        </form>

        <p className="register-link">
          {t("registerPage.ya_tienes_cuenta")}{" "}
          <Link to="/login">
            {t("registerPage.inicia_sesion")}
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
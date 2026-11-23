import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import {
  crearAnalistaCumplimiento,
  type SolicitudCrearAnalista,
} from "../services/auditor.service";
import "../styles/socios.css";

import { t } from "../i18n";

const INITIAL_FORM: SolicitudCrearAnalista = {
  nombre: "",
  apellido: "",
  email: "",
  password: "",
  tipo_documento: "CC",
  numero_documento: "",
  fecha_nacimiento: "",
};

/** Alta de un analista de cumplimiento. Solo accesible para un manager (SERVICIO_INTERNO). */
export default function AuditorRegistrationPage() {
  const [form, setForm] = useState<SolicitudCrearAnalista>(INITIAL_FORM);
  const [confirmarPassword, setConfirmarPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [creado, setCreado] = useState<{ nombre: string; apellido: string; email: string } | null>(
    null,
  );

  function actualizar<K extends keyof SolicitudCrearAnalista>(
    campo: K,
    valor: SolicitudCrearAnalista[K],
  ) {
    setForm((actual) => ({ ...actual, [campo]: valor }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (form.password.length < 8) {
      setError(t("auditorRegistrationPage.la_contrasena_debe_tener_minimo"));
      return;
    }
    if (form.password !== confirmarPassword) {
      setError(t("auditorRegistrationPage.las_contrasenas_no_coinciden"));
      return;
    }

    setLoading(true);
    try {
      const analista = await crearAnalistaCumplimiento({
        ...form,
        nombre: form.nombre.trim(),
        apellido: form.apellido.trim(),
        email: form.email.trim(),
        tipo_documento: form.tipo_documento.trim().toUpperCase(),
        numero_documento: form.numero_documento.trim(),
      });
      setCreado({ nombre: analista.nombre, apellido: analista.apellido, email: analista.email });
    } catch (fallo) {
      setError(
        fallo instanceof Error ? fallo.message : t("auditorRegistrationPage.no_fue_posible_crear_el"),
      );
    } finally {
      setLoading(false);
    }
  }

  function reiniciar() {
    setForm(INITIAL_FORM);
    setConfirmarPassword("");
    setCreado(null);
    setError("");
  }

  return (
    <div className="socio-page">
      <header className="socio-header">
        <Link className="socio-brand" to="/home">
          <span className="material-symbols-outlined" aria-hidden="true">shield</span>
          <span>
            <strong>Solventa</strong>
            <span className="socio-brand-section"> {t("auditorRegistrationPage.administracion")}</span>
          </span>
        </Link>
        <Link className="socio-exit" to="/home">
          <span className="material-symbols-outlined" aria-hidden="true">logout</span>
          {t("auditorRegistrationPage.salir")}
        </Link>
      </header>

      <main className="socio-content">
        <div className="socio-title-row">
          <div>
            <h1>{t("auditorRegistrationPage.crear_analista_de_cumplimiento")}</h1>
            <p>
              {t("auditorRegistrationPage.registra_un_analista_de_cumplimiento")}
            </p>
          </div>
          <div className="socio-title-icon" aria-hidden="true">
            <span className="material-symbols-outlined">manage_search</span>
          </div>
        </div>

        {creado ? (
          <section className="socio-success" aria-live="polite">
            <div className="socio-success-icon">
              <span className="material-symbols-outlined" aria-hidden="true">check_circle</span>
            </div>
            <div>
              <span className="socio-eyebrow">{t("auditorRegistrationPage.alta_completada")}</span>
              <h2>{t("auditorRegistrationPage.analista_creado_correctamente")}</h2>
              <p>{t("auditorRegistrationPage.el_analista_ya_puede_iniciar")}</p>
              <dl className="socio-result-grid">
                <div>
                  <dt>{t("auditorRegistrationPage.nombre")}</dt>
                  <dd>{creado.nombre} {creado.apellido}</dd>
                </div>
                <div>
                  <dt>{t("auditorRegistrationPage.correo")}</dt>
                  <dd>{creado.email}</dd>
                </div>
                <div>
                  <dt>{t("auditorRegistrationPage.rol")}</dt>
                  <dd><span className="socio-status">ANALISTA_CUMPLIMIENTO</span></dd>
                </div>
              </dl>
              <button className="socio-secondary-button" type="button" onClick={reiniciar}>
                {t("auditorRegistrationPage.crear_otro_analista")}
              </button>
            </div>
          </section>
        ) : (
          <form className="socio-form" onSubmit={handleSubmit}>
            <section className="socio-card">
              <div className="socio-section-heading">
                <span className="material-symbols-outlined" aria-hidden="true">badge</span>
                <div>
                  <h2>{t("auditorRegistrationPage.datos_del_analista")}</h2>
                  <p>{t("auditorRegistrationPage.informacion_personal_y_documento_de")}</p>
                </div>
              </div>

              <div className="socio-form-grid">
                <label>
                  {t("auditorRegistrationPage.nombre")}
                  <input
                    name="nombre"
                    minLength={2}
                    maxLength={100}
                    placeholder={t("auditorRegistrationPage.maria")}
                    value={form.nombre}
                    onChange={(e) => actualizar("nombre", e.target.value)}
                    required
                  />
                </label>

                <label>
                  {t("auditorRegistrationPage.apellido")}
                  <input
                    name="apellido"
                    minLength={2}
                    maxLength={100}
                    placeholder={t("auditorRegistrationPage.torres")}
                    value={form.apellido}
                    onChange={(e) => actualizar("apellido", e.target.value)}
                    required
                  />
                </label>

                <label>
                  {t("auditorRegistrationPage.tipo_de_documento")}
                  <select
                    name="tipo_documento"
                    value={form.tipo_documento}
                    onChange={(e) => actualizar("tipo_documento", e.target.value)}
                    required
                  >
                    <option value="CC">{t("auditorRegistrationPage.cedula_de_ciudadania")}</option>
                    <option value="CE">{t("auditorRegistrationPage.cedula_de_extranjeria")}</option>
                    <option value="PA">{t("auditorRegistrationPage.pasaporte")}</option>
                  </select>
                </label>

                <label>
                  {t("auditorRegistrationPage.numero_de_documento")}
                  <input
                    name="numero_documento"
                    minLength={3}
                    maxLength={50}
                    placeholder="1012345678"
                    value={form.numero_documento}
                    onChange={(e) => actualizar("numero_documento", e.target.value)}
                    required
                  />
                </label>

                <label>
                  {t("auditorRegistrationPage.fecha_de_nacimiento")}
                  <input
                    name="fecha_nacimiento"
                    type="date"
                    value={form.fecha_nacimiento}
                    onChange={(e) => actualizar("fecha_nacimiento", e.target.value)}
                    required
                  />
                </label>
              </div>
            </section>

            <section className="socio-card">
              <div className="socio-section-heading">
                <span className="material-symbols-outlined" aria-hidden="true">lock</span>
                <div>
                  <h2>{t("auditorRegistrationPage.credenciales_de_acceso")}</h2>
                  <p>{t("auditorRegistrationPage.correo_y_contrasena_con_los")}</p>
                </div>
              </div>

              <div className="socio-form-grid">
                <label>
                  {t("auditorRegistrationPage.correo_corporativo")}
                  <input
                    name="email"
                    type="email"
                    minLength={5}
                    maxLength={254}
                    placeholder="maria.torres@solventa.com"
                    value={form.email}
                    onChange={(e) => actualizar("email", e.target.value)}
                    required
                  />
                </label>

                <label>
                  {t("auditorRegistrationPage.contrasena")}
                  <input
                    name="password"
                    type="password"
                    minLength={8}
                    maxLength={128}
                    placeholder={t("auditorRegistrationPage.minimo_8_caracteres")}
                    value={form.password}
                    onChange={(e) => actualizar("password", e.target.value)}
                    required
                  />
                </label>

                <label>
                  {t("auditorRegistrationPage.confirmar_contrasena")}
                  <input
                    name="confirmar_password"
                    type="password"
                    minLength={8}
                    maxLength={128}
                    placeholder={t("auditorRegistrationPage.repite_la_contrasena")}
                    value={confirmarPassword}
                    onChange={(e) => setConfirmarPassword(e.target.value)}
                    required
                  />
                </label>
              </div>
            </section>

            {error && (
              <div className="socio-error" role="alert">
                <span className="material-symbols-outlined" aria-hidden="true">error</span>
                {error}
              </div>
            )}

            <div className="socio-submit-row">
              <p>{t("auditorRegistrationPage.al_guardar_solventa_creara_la")}</p>
              <button className="socio-primary-button" type="submit" disabled={loading}>
                <span className="material-symbols-outlined" aria-hidden="true">person_add</span>
                {loading ? t("auditorRegistrationPage.creando") : t("auditorRegistrationPage.crear_analista")}
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}

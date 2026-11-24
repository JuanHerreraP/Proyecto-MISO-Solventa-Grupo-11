import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { crearAsesorVentas, type SolicitudCrearAsesor } from "../services/asesor.service";
import "../styles/socios.css";

import { t } from "../i18n";

const INITIAL_FORM: SolicitudCrearAsesor = {
  nombre: "",
  apellido: "",
  email: "",
  password: "",
  tipo_documento: "CC",
  numero_documento: "",
  fecha_nacimiento: "",
};

/** Alta de un asesor de ventas. Solo accesible para un manager (SERVICIO_INTERNO). */
export default function AsesorRegistrationPage() {
  const [form, setForm] = useState<SolicitudCrearAsesor>(INITIAL_FORM);
  const [confirmarPassword, setConfirmarPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [creado, setCreado] = useState<{ nombre: string; apellido: string; email: string } | null>(
    null,
  );

  function actualizar<K extends keyof SolicitudCrearAsesor>(
    campo: K,
    valor: SolicitudCrearAsesor[K],
  ) {
    setForm((actual) => ({ ...actual, [campo]: valor }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (form.password.length < 8) {
      setError(t("asesorRegistrationPage.la_contrasena_debe_tener_minimo"));
      return;
    }
    if (form.password !== confirmarPassword) {
      setError(t("asesorRegistrationPage.las_contrasenas_no_coinciden"));
      return;
    }

    setLoading(true);
    try {
      const asesor = await crearAsesorVentas({
        ...form,
        nombre: form.nombre.trim(),
        apellido: form.apellido.trim(),
        email: form.email.trim(),
        tipo_documento: form.tipo_documento.trim().toUpperCase(),
        numero_documento: form.numero_documento.trim(),
      });
      setCreado({ nombre: asesor.nombre, apellido: asesor.apellido, email: asesor.email });
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : t("asesorRegistrationPage.no_fue_posible_crear_el"));
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
            <span className="socio-brand-section"> {t("asesorRegistrationPage.administracion")}</span>
          </span>
        </Link>
        <Link className="socio-exit" to="/home">
          <span className="material-symbols-outlined" aria-hidden="true">logout</span>
          {t("asesorRegistrationPage.salir")}
        </Link>
      </header>

      <main className="socio-content">
        <div className="socio-title-row">
          <div>
            <h1>{t("asesorRegistrationPage.crear_asesor_de_ventas")}</h1>
            <p>
              {t("asesorRegistrationPage.registra_un_asesor_de_ventas")}
            </p>
          </div>
          <div className="socio-title-icon" aria-hidden="true">
            <span className="material-symbols-outlined">support_agent</span>
          </div>
        </div>

        {creado ? (
          <section className="socio-success" aria-live="polite">
            <div className="socio-success-icon">
              <span className="material-symbols-outlined" aria-hidden="true">check_circle</span>
            </div>
            <div>
              <span className="socio-eyebrow">{t("asesorRegistrationPage.alta_completada")}</span>
              <h2>{t("asesorRegistrationPage.asesor_creado_correctamente")}</h2>
              <p>{t("asesorRegistrationPage.el_asesor_ya_puede_iniciar")}</p>
              <dl className="socio-result-grid">
                <div>
                  <dt>{t("asesorRegistrationPage.nombre")}</dt>
                  <dd>{creado.nombre} {creado.apellido}</dd>
                </div>
                <div>
                  <dt>{t("asesorRegistrationPage.correo")}</dt>
                  <dd>{creado.email}</dd>
                </div>
                <div>
                  <dt>{t("asesorRegistrationPage.rol")}</dt>
                  <dd><span className="socio-status">ASESOR_VENTAS</span></dd>
                </div>
              </dl>
              <button className="socio-secondary-button" type="button" onClick={reiniciar}>
                {t("asesorRegistrationPage.crear_otro_asesor")}
              </button>
            </div>
          </section>
        ) : (
          <form className="socio-form" onSubmit={handleSubmit}>
            <section className="socio-card">
              <div className="socio-section-heading">
                <span className="material-symbols-outlined" aria-hidden="true">badge</span>
                <div>
                  <h2>{t("asesorRegistrationPage.datos_del_asesor")}</h2>
                  <p>{t("asesorRegistrationPage.informacion_personal_y_documento_de")}</p>
                </div>
              </div>

              <div className="socio-form-grid">
                <label>
                  {t("asesorRegistrationPage.nombre")}
                  <input
                    name="nombre"
                    minLength={2}
                    maxLength={100}
                    placeholder={t("asesorRegistrationPage.maria")}
                    value={form.nombre}
                    onChange={(e) => actualizar("nombre", e.target.value)}
                    required
                  />
                </label>

                <label>
                  {t("asesorRegistrationPage.apellido")}
                  <input
                    name="apellido"
                    minLength={2}
                    maxLength={100}
                    placeholder={t("asesorRegistrationPage.torres")}
                    value={form.apellido}
                    onChange={(e) => actualizar("apellido", e.target.value)}
                    required
                  />
                </label>

                <label>
                  {t("asesorRegistrationPage.tipo_de_documento")}
                  <select
                    name="tipo_documento"
                    value={form.tipo_documento}
                    onChange={(e) => actualizar("tipo_documento", e.target.value)}
                    required
                  >
                    <option value="CC">{t("asesorRegistrationPage.cedula_de_ciudadania")}</option>
                    <option value="CE">{t("asesorRegistrationPage.cedula_de_extranjeria")}</option>
                    <option value="PA">{t("asesorRegistrationPage.pasaporte")}</option>
                  </select>
                </label>

                <label>
                  {t("asesorRegistrationPage.numero_de_documento")}
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
                  {t("asesorRegistrationPage.fecha_de_nacimiento")}
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
                  <h2>{t("asesorRegistrationPage.credenciales_de_acceso")}</h2>
                  <p>{t("asesorRegistrationPage.correo_y_contrasena_con_los")}</p>
                </div>
              </div>

              <div className="socio-form-grid">
                <label>
                  {t("asesorRegistrationPage.correo_corporativo")}
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
                  {t("asesorRegistrationPage.contrasena")}
                  <input
                    name="password"
                    type="password"
                    minLength={8}
                    maxLength={128}
                    placeholder={t("asesorRegistrationPage.minimo_8_caracteres")}
                    value={form.password}
                    onChange={(e) => actualizar("password", e.target.value)}
                    required
                  />
                </label>

                <label>
                  {t("asesorRegistrationPage.confirmar_contrasena")}
                  <input
                    name="confirmar_password"
                    type="password"
                    minLength={8}
                    maxLength={128}
                    placeholder={t("asesorRegistrationPage.repite_la_contrasena")}
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
              <p>{t("asesorRegistrationPage.al_guardar_solventa_creara_la")}</p>
              <button className="socio-primary-button" type="submit" disabled={loading}>
                <span className="material-symbols-outlined" aria-hidden="true">person_add</span>
                {loading ? t("asesorRegistrationPage.creando") : t("asesorRegistrationPage.crear_asesor")}
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}

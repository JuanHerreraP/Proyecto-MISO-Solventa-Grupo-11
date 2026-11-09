import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import {
  crearAnalistaCumplimiento,
  type SolicitudCrearAnalista,
} from "../services/auditor.service";
import "../styles/socios.css";

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
      setError("La contraseña debe tener mínimo 8 caracteres.");
      return;
    }
    if (form.password !== confirmarPassword) {
      setError("Las contraseñas no coinciden.");
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
        fallo instanceof Error ? fallo.message : "No fue posible crear el analista de cumplimiento.",
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
            <span className="socio-brand-section"> · Administración</span>
          </span>
        </Link>
        <Link className="socio-exit" to="/home">
          <span className="material-symbols-outlined" aria-hidden="true">logout</span>
          Salir
        </Link>
      </header>

      <main className="socio-content">
        <div className="socio-title-row">
          <div>
            <h1>Crear analista de cumplimiento</h1>
            <p>
              Registra un analista de cumplimiento. Con su cuenta podrá consultar el historial
              contractual de cualquier póliza para auditoría.
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
              <span className="socio-eyebrow">Alta completada</span>
              <h2>Analista creado correctamente</h2>
              <p>El analista ya puede iniciar sesión con las credenciales configuradas.</p>
              <dl className="socio-result-grid">
                <div>
                  <dt>Nombre</dt>
                  <dd>{creado.nombre} {creado.apellido}</dd>
                </div>
                <div>
                  <dt>Correo</dt>
                  <dd>{creado.email}</dd>
                </div>
                <div>
                  <dt>Rol</dt>
                  <dd><span className="socio-status">ANALISTA_CUMPLIMIENTO</span></dd>
                </div>
              </dl>
              <button className="socio-secondary-button" type="button" onClick={reiniciar}>
                Crear otro analista
              </button>
            </div>
          </section>
        ) : (
          <form className="socio-form" onSubmit={handleSubmit}>
            <section className="socio-card">
              <div className="socio-section-heading">
                <span className="material-symbols-outlined" aria-hidden="true">badge</span>
                <div>
                  <h2>Datos del analista</h2>
                  <p>Información personal y documento de identidad.</p>
                </div>
              </div>

              <div className="socio-form-grid">
                <label>
                  Nombre
                  <input
                    name="nombre"
                    minLength={2}
                    maxLength={100}
                    placeholder="María"
                    value={form.nombre}
                    onChange={(e) => actualizar("nombre", e.target.value)}
                    required
                  />
                </label>

                <label>
                  Apellido
                  <input
                    name="apellido"
                    minLength={2}
                    maxLength={100}
                    placeholder="Torres"
                    value={form.apellido}
                    onChange={(e) => actualizar("apellido", e.target.value)}
                    required
                  />
                </label>

                <label>
                  Tipo de documento
                  <select
                    name="tipo_documento"
                    value={form.tipo_documento}
                    onChange={(e) => actualizar("tipo_documento", e.target.value)}
                    required
                  >
                    <option value="CC">Cédula de ciudadanía</option>
                    <option value="CE">Cédula de extranjería</option>
                    <option value="PA">Pasaporte</option>
                  </select>
                </label>

                <label>
                  Número de documento
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
                  Fecha de nacimiento
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
                  <h2>Credenciales de acceso</h2>
                  <p>Correo y contraseña con los que el analista iniciará sesión.</p>
                </div>
              </div>

              <div className="socio-form-grid">
                <label>
                  Correo corporativo
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
                  Contraseña
                  <input
                    name="password"
                    type="password"
                    minLength={8}
                    maxLength={128}
                    placeholder="Mínimo 8 caracteres"
                    value={form.password}
                    onChange={(e) => actualizar("password", e.target.value)}
                    required
                  />
                </label>

                <label>
                  Confirmar contraseña
                  <input
                    name="confirmar_password"
                    type="password"
                    minLength={8}
                    maxLength={128}
                    placeholder="Repite la contraseña"
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
              <p>Al guardar, Solventa creará la cuenta con el rol ANALISTA_CUMPLIMIENTO.</p>
              <button className="socio-primary-button" type="submit" disabled={loading}>
                <span className="material-symbols-outlined" aria-hidden="true">person_add</span>
                {loading ? "Creando..." : "Crear analista"}
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}

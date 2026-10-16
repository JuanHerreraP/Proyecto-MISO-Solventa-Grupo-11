import {
  type FormEvent,
  useState,
} from "react";
import { Link } from "react-router-dom";

import {
  generarCredencialesSocio,
  registrarSocio,
} from "../services/socios.service";
import type {
  CredencialesSocioEmitidas,
  EndpointSocio,
  RespuestaRegistroSocio,
  SolicitudRegistroSocio,
  TipoSeguro,
} from "../types/socios";
import "../styles/socios.css";

const INSURANCE_OPTIONS: Array<{
  value: TipoSeguro;
  label: string;
}> = [
  { value: "VIAJE", label: "Seguro de viaje" },
  {
    value: "PROTECCION_DISPOSITIVOS",
    label: "Protección de dispositivos",
  },
  { value: "MICROSEGURO_VIDA", label: "Microseguro de vida" },
  { value: "PARAMETRICO", label: "Seguro paramétrico" },
  { value: "PROTECCION_PAGOS", label: "Protección de pagos" },
];

const ENDPOINT_OPTIONS: Array<{
  value: EndpointSocio;
  label: string;
  description: string;
}> = [
  {
    value: "cotizaciones:crear",
    label: "Cotizar póliza",
    description: "Calcula una cotización con los datos y coberturas indicados.",
  },
  {
    value: "polizas:emitir",
    label: "Emitir póliza",
    description: "Genera una póliza a partir de una cotización aceptada.",
  },
];

const INITIAL_FORM: SolicitudRegistroSocio = {
  nit: "",
  razon_social: "",
  contactos_tecnicos: [
    {
      nombre: "",
      correo: "",
      telefono: "",
    },
  ],
  pais_operacion: "CO",
  tipos_seguros_autorizados: [],
  endpoints_autorizados: [],
};

export default function SocioRegistrationPage() {
  const [form, setForm] =
    useState<SolicitudRegistroSocio>(INITIAL_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [socioCreado, setSocioCreado] =
    useState<RespuestaRegistroSocio | null>(null);
  const [credenciales, setCredenciales] =
    useState<CredencialesSocioEmitidas | null>(null);
  const [generandoCredenciales, setGenerandoCredenciales] = useState(false);
  const [errorCredenciales, setErrorCredenciales] = useState("");
  const [valorCopiado, setValorCopiado] = useState("");

  function updateContact(
    index: number,
    field: "nombre" | "correo" | "telefono",
    value: string,
  ) {
    setForm((current) => ({
      ...current,
      contactos_tecnicos: current.contactos_tecnicos.map(
        (contact, contactIndex) =>
          contactIndex === index
            ? { ...contact, [field]: value }
            : contact,
      ),
    }));
  }

  function addContact() {
    setForm((current) => ({
      ...current,
      contactos_tecnicos: [
        ...current.contactos_tecnicos,
        { nombre: "", correo: "", telefono: "" },
      ],
    }));
  }

  function removeContact(index: number) {
    setForm((current) => ({
      ...current,
      contactos_tecnicos: current.contactos_tecnicos.filter(
        (_, contactIndex) => contactIndex !== index,
      ),
    }));
  }

  function toggleInsurance(value: TipoSeguro) {
    setForm((current) => ({
      ...current,
      tipos_seguros_autorizados:
        current.tipos_seguros_autorizados.includes(value)
          ? current.tipos_seguros_autorizados.filter(
              (item) => item !== value,
            )
          : [...current.tipos_seguros_autorizados, value],
    }));
  }

  function toggleEndpoint(value: EndpointSocio) {
    setForm((current) => ({
      ...current,
      endpoints_autorizados:
        current.endpoints_autorizados.includes(value)
          ? current.endpoints_autorizados.filter(
              (item) => item !== value,
            )
          : [...current.endpoints_autorizados, value],
    }));
  }

  async function aprovisionarCredenciales(socioId: string) {
    setGenerandoCredenciales(true);
    setErrorCredenciales("");

    try {
      const response = await generarCredencialesSocio(socioId);
      setCredenciales(response);
    } catch (credentialsError) {
      setErrorCredenciales(
        credentialsError instanceof Error
          ? credentialsError.message
          : "No fue posible generar las credenciales del socio.",
      );
    } finally {
      setGenerandoCredenciales(false);
    }
  }

  async function copiarValor(nombre: string, valor: string) {
    await navigator.clipboard.writeText(valor);
    setValorCopiado(nombre);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSocioCreado(null);
    setCredenciales(null);
    setErrorCredenciales("");

    if (form.tipos_seguros_autorizados.length === 0) {
      setError("Selecciona al menos un tipo de seguro autorizado.");
      return;
    }

    if (form.endpoints_autorizados.length === 0) {
      setError("Selecciona al menos un permiso de API.");
      return;
    }

    setLoading(true);

    try {
      const response = await registrarSocio({
        ...form,
        pais_operacion: form.pais_operacion.toUpperCase(),
        contactos_tecnicos: form.contactos_tecnicos.map((contact) => ({
          nombre: contact.nombre,
          correo: contact.correo,
          ...(contact.telefono
            ? { telefono: contact.telefono }
            : {}),
        })),
      });

      setSocioCreado(response);
      await aprovisionarCredenciales(response.socio_id);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "No fue posible registrar el socio.",
      );
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setForm(INITIAL_FORM);
    setSocioCreado(null);
    setCredenciales(null);
    setError("");
    setErrorCredenciales("");
    setValorCopiado("");
  }

  return (
    <div className="socio-page">
      <header className="socio-header">
        <Link className="socio-brand" to="/home">
          <span className="material-symbols-outlined" aria-hidden="true">
            shield
          </span>
          <span>
            <strong>Solventa</strong>
            <span className="socio-brand-section"> · Portal de socios</span>
          </span>
        </Link>

        <Link className="socio-exit" to="/login">
          <span className="material-symbols-outlined" aria-hidden="true">
            logout
          </span>
          Salir
        </Link>
      </header>

      <main className="socio-content">
        <div className="socio-title-row">
          <div>
            <h1>Registrar nuevo socio</h1>
            <p>
              Configura la información técnica y los permisos que el socio
              tendrá para integrar sus canales con Solventa.
            </p>
          </div>

          <div className="socio-title-icon" aria-hidden="true">
            <span className="material-symbols-outlined">handshake</span>
          </div>
        </div>

        {socioCreado ? (
          <section className="socio-success" aria-live="polite">
            <div className="socio-success-icon">
              <span className="material-symbols-outlined" aria-hidden="true">
                check_circle
              </span>
            </div>

            <div>
              <span className="socio-eyebrow">Registro completado</span>
              <h2>Socio registrado correctamente</h2>
              <p>
                La ficha técnica fue creada y el espacio lógico del socio quedó
                aprovisionado.
              </p>

              <dl className="socio-result-grid">
                <div>
                  <dt>Razón social</dt>
                  <dd>{socioCreado.razon_social}</dd>
                </div>
                <div>
                  <dt>Socio ID</dt>
                  <dd>{socioCreado.socio_id}</dd>
                </div>
                <div>
                  <dt>Tenant ID</dt>
                  <dd>{socioCreado.tenant_id}</dd>
                </div>
                <div>
                  <dt>Estado</dt>
                  <dd>
                    <span className="socio-status">
                      {socioCreado.estado}
                    </span>
                  </dd>
                </div>
              </dl>

              {generandoCredenciales && (
                <div className="socio-credentials-loading" role="status">
                  Generando credenciales de integración...
                </div>
              )}

              {credenciales && (
                <section className="socio-credentials" aria-labelledby="credentials-title">
                  <div className="socio-credentials-heading">
                    <span className="material-symbols-outlined" aria-hidden="true">
                      key
                    </span>
                    <div>
                      <h3 id="credentials-title">Credenciales de integración</h3>
                      <p>
                        Guarda estas credenciales ahora. Por seguridad, el
                        client secret no volverá a mostrarse.
                      </p>
                    </div>
                  </div>

                  <div className="socio-credentials-grid">
                    <div>
                      <span>Client ID</span>
                      <div className="socio-credential-value">
                        <code>{credenciales.client_id}</code>
                        <button
                          type="button"
                          onClick={() =>
                            copiarValor("Client ID", credenciales.client_id)
                          }
                          aria-label="Copiar Client ID"
                        >
                          <span className="material-symbols-outlined" aria-hidden="true">
                            content_copy
                          </span>
                        </button>
                      </div>
                    </div>

                    <div>
                      <span>Client secret</span>
                      <div className="socio-credential-value">
                        <code>{credenciales.client_secret}</code>
                        <button
                          type="button"
                          onClick={() =>
                            copiarValor(
                              "Client secret",
                              credenciales.client_secret,
                            )
                          }
                          aria-label="Copiar Client secret"
                        >
                          <span className="material-symbols-outlined" aria-hidden="true">
                            content_copy
                          </span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {valorCopiado && (
                    <p className="socio-copy-confirmation" role="status">
                      {valorCopiado} copiado.
                    </p>
                  )}
                </section>
              )}

              {errorCredenciales && (
                <div className="socio-credentials-error" role="alert">
                  <span className="material-symbols-outlined" aria-hidden="true">
                    warning
                  </span>
                  <div>
                    <p>{errorCredenciales}</p>
                    <button
                      type="button"
                      onClick={() => aprovisionarCredenciales(socioCreado.socio_id)}
                      disabled={generandoCredenciales}
                    >
                      Reintentar generación
                    </button>
                  </div>
                </div>
              )}

              <button
                className="socio-secondary-button"
                type="button"
                onClick={resetForm}
                disabled={generandoCredenciales}
              >
                Registrar otro socio
              </button>
            </div>
          </section>
        ) : (
          <form className="socio-form" onSubmit={handleSubmit}>
            <section className="socio-card">
              <div className="socio-section-heading">
                <span className="material-symbols-outlined" aria-hidden="true">
                  domain
                </span>
                <div>
                  <h2>Información de la organización</h2>
                  <p>Datos legales y país desde el que operará el socio.</p>
                </div>
              </div>

              <div className="socio-form-grid">
                <label>
                  NIT
                  <input
                    name="nit"
                    placeholder="900123456-7"
                    pattern="[0-9]+(-[0-9])?"
                    value={form.nit}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        nit: event.target.value,
                      }))
                    }
                    required
                  />
                  <small>Sin puntos ni separadores de miles.</small>
                </label>

                <label>
                  Razón social
                  <input
                    name="razon_social"
                    placeholder="Banco Andes S.A."
                    value={form.razon_social}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        razon_social: event.target.value,
                      }))
                    }
                    required
                  />
                </label>

                <label>
                  País de operación
                  <select
                    name="pais_operacion"
                    value={form.pais_operacion}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        pais_operacion: event.target.value,
                      }))
                    }
                    required
                  >
                    <option value="CO">Colombia</option>
                    <option value="MX">México</option>
                    <option value="PE">Perú</option>
                    <option value="CL">Chile</option>
                    <option value="AR">Argentina</option>
                  </select>
                </label>
              </div>
            </section>

            <section className="socio-card">
              <div className="socio-section-heading">
                <span className="material-symbols-outlined" aria-hidden="true">
                  contact_support
                </span>
                <div>
                  <h2>Contacto técnico</h2>
                  <p>Persona responsable de acompañar la integración.</p>
                </div>
              </div>

              <div className="socio-contacts">
                {form.contactos_tecnicos.map((contact, index) => (
                  <div className="socio-contact-row" key={`contact-${index}`}>
                    <div className="socio-form-grid socio-contact-grid">
                      <label>
                        Nombre completo
                        <input
                          name={`contacto_nombre_${index}`}
                          placeholder="María Torres"
                          value={contact.nombre}
                          onChange={(event) =>
                            updateContact(index, "nombre", event.target.value)
                          }
                          required
                        />
                      </label>

                      <label>
                        Correo corporativo
                        <input
                          name={`contacto_correo_${index}`}
                          type="email"
                          placeholder="maria.torres@bancoandes.com"
                          value={contact.correo}
                          onChange={(event) =>
                            updateContact(index, "correo", event.target.value)
                          }
                          required
                        />
                      </label>

                      <label>
                        <span>
                          Teléfono <span className="socio-optional">(Opcional)</span>
                        </span>
                        <input
                          name={`contacto_telefono_${index}`}
                          type="tel"
                          placeholder="+57 300 123 4567"
                          value={contact.telefono}
                          onChange={(event) =>
                            updateContact(index, "telefono", event.target.value)
                          }
                        />
                      </label>
                    </div>

                    {form.contactos_tecnicos.length > 1 && (
                      <button
                        className="socio-remove-contact"
                        type="button"
                        onClick={() => removeContact(index)}
                      >
                        <span className="material-symbols-outlined" aria-hidden="true">
                          delete
                        </span>
                        Eliminar contacto
                      </button>
                    )}
                  </div>
                ))}

                <button
                  className="socio-add-contact"
                  type="button"
                  onClick={addContact}
                >
                  <span className="material-symbols-outlined" aria-hidden="true">
                    add
                  </span>
                  Agregar otro contacto
                </button>
              </div>
            </section>

            <section className="socio-card">
              <div className="socio-section-heading">
                <span className="material-symbols-outlined" aria-hidden="true">
                  verified_user
                </span>
                <div>
                  <h2>Seguros autorizados</h2>
                  <p>Selecciona los productos que el socio podrá comercializar.</p>
                </div>
              </div>

              <div className="socio-choice-grid">
                {INSURANCE_OPTIONS.map((option) => (
                  <label className="socio-choice" key={option.value}>
                    <input
                      type="checkbox"
                      checked={form.tipos_seguros_autorizados.includes(
                        option.value,
                      )}
                      onChange={() => toggleInsurance(option.value)}
                    />
                    <span>{option.label}</span>
                  </label>
                ))}
              </div>
            </section>

            <section className="socio-card">
              <div className="socio-section-heading">
                <span className="material-symbols-outlined" aria-hidden="true">
                  api
                </span>
                <div>
                  <h2>Permisos de API</h2>
                  <p>
                    Asigna únicamente las operaciones necesarias para la
                    integración.
                  </p>
                </div>
              </div>

              <div className="socio-endpoint-list">
                {ENDPOINT_OPTIONS.map((option) => (
                  <label className="socio-endpoint" key={option.value}>
                    <input
                      type="checkbox"
                      checked={form.endpoints_autorizados.includes(option.value)}
                      onChange={() => toggleEndpoint(option.value)}
                    />
                    <span>
                      <strong>{option.label}</strong>
                      <small>{option.description}</small>
                    </span>
                  </label>
                ))}
              </div>
            </section>

            {error && (
              <div className="socio-error" role="alert">
                <span className="material-symbols-outlined" aria-hidden="true">
                  error
                </span>
                {error}
              </div>
            )}

            <div className="socio-submit-row">
              <p>
                Al guardar, Solventa creará la ficha técnica y aprovisionará el
                tenant lógico del socio.
              </p>
              <button
                className="socio-primary-button"
                type="submit"
                disabled={loading}
              >
                <span className="material-symbols-outlined" aria-hidden="true">
                  add_business
                </span>
                {loading ? "Registrando..." : "Registrar socio"}
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}

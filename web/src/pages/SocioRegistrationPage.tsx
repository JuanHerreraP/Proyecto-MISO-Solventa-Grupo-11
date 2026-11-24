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

import { t } from "../i18n";

const INSURANCE_OPTIONS: Array<{
  value: TipoSeguro;
  label: string;
}> = [
  { value: "VIAJE", get label() { return t("socioRegistrationPage.seguro_de_viaje"); } },
  {
    value: "PROTECCION_DISPOSITIVOS",
    get label() { return t("socioRegistrationPage.proteccion_de_dispositivos"); },
  },
  { value: "MICROSEGURO_VIDA", get label() { return t("socioRegistrationPage.microseguro_de_vida"); } },
  { value: "PARAMETRICO", get label() { return t("socioRegistrationPage.seguro_parametrico"); } },
  { value: "PROTECCION_PAGOS", get label() { return t("socioRegistrationPage.proteccion_de_pagos"); } },
];

const ENDPOINT_OPTIONS: Array<{
  value: EndpointSocio;
  label: string;
  description: string;
}> = [
  {
    value: "cotizaciones:crear",
    get label() { return t("socioRegistrationPage.cotizar_poliza"); },
    get description() { return t("socioRegistrationPage.calcula_una_cotizacion_con_los"); },
  },
  {
    value: "polizas:emitir",
    get label() { return t("socioRegistrationPage.emitir_poliza"); },
    get description() { return t("socioRegistrationPage.genera_una_poliza_a_partir"); },
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
          : t("socioRegistrationPage.no_fue_posible_generar_las"),
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
      setError(t("socioRegistrationPage.selecciona_al_menos_un_tipo"));
      return;
    }

    if (form.endpoints_autorizados.length === 0) {
      setError(t("socioRegistrationPage.selecciona_al_menos_un_permiso"));
      return;
    }

    setLoading(true);

    try {
      const response = await registrarSocio({
        ...form,
        nit: form.nit.trim(),
        razon_social: form.razon_social.trim(),
        pais_operacion: form.pais_operacion.toUpperCase(),
        contactos_tecnicos: form.contactos_tecnicos.map((contact) => ({
          nombre: contact.nombre.trim(),
          correo: contact.correo.trim(),
          ...(contact.telefono?.trim()
            ? { telefono: contact.telefono.trim() }
            : {}),
        })),
      });

      setSocioCreado(response);
      await aprovisionarCredenciales(response.socio_id);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : t("socioRegistrationPage.no_fue_posible_registrar_el"),
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
            <span className="socio-brand-section"> {t("socioRegistrationPage.portal_de_socios")}</span>
          </span>
        </Link>

        <Link className="socio-exit" to="/login">
          <span className="material-symbols-outlined" aria-hidden="true">
            logout
          </span>
          {t("socioRegistrationPage.salir")}
        </Link>
      </header>

      <main className="socio-content">
        <div className="socio-title-row">
          <div>
            <h1>{t("socioRegistrationPage.registrar_nuevo_socio")}</h1>
            <p>
              {t("socioRegistrationPage.configura_la_informacion_tecnica_y")}
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
              <span className="socio-eyebrow">{t("socioRegistrationPage.registro_completado")}</span>
              <h2>{t("socioRegistrationPage.socio_registrado_correctamente")}</h2>
              <p>
                {t("socioRegistrationPage.la_ficha_tecnica_fue_creada")}
              </p>

              <dl className="socio-result-grid">
                <div>
                  <dt>{t("socioRegistrationPage.razon_social")}</dt>
                  <dd>{socioCreado.razon_social}</dd>
                </div>
                <div>
                  <dt>{t("socioRegistrationPage.socio_id")}</dt>
                  <dd>{socioCreado.socio_id}</dd>
                </div>
                <div>
                  <dt>{t("socioRegistrationPage.tenant_id")}</dt>
                  <dd>{socioCreado.tenant_id}</dd>
                </div>
                <div>
                  <dt>{t("socioRegistrationPage.estado")}</dt>
                  <dd>
                    <span className="socio-status">
                      {socioCreado.estado}
                    </span>
                  </dd>
                </div>
              </dl>

              {generandoCredenciales && (
                <div className="socio-credentials-loading" role="status">
                  {t("socioRegistrationPage.generando_credenciales_de_integracion")}
                </div>
              )}

              {credenciales && (
                <section className="socio-credentials" aria-labelledby="credentials-title">
                  <div className="socio-credentials-heading">
                    <span className="material-symbols-outlined" aria-hidden="true">
                      key
                    </span>
                    <div>
                      <h3 id="credentials-title">{t("socioRegistrationPage.credenciales_de_integracion")}</h3>
                      <p>
                        {t("socioRegistrationPage.guarda_estas_credenciales_ahora_por")}
                      </p>
                    </div>
                  </div>

                  <div className="socio-credentials-grid">
                    <div>
                      <span>{t("socioRegistrationPage.client_id")}</span>
                      <div className="socio-credential-value">
                        <code>{credenciales.client_id}</code>
                        <button
                          type="button"
                          onClick={() =>
                            copiarValor(t("socioRegistrationPage.client_id"), credenciales.client_id)
                          }
                          aria-label={t("socioRegistrationPage.copiar_client_id")}
                        >
                          <span className="material-symbols-outlined" aria-hidden="true">
                            content_copy
                          </span>
                        </button>
                      </div>
                    </div>

                    <div>
                      <span>{t("socioRegistrationPage.client_secret")}</span>
                      <div className="socio-credential-value">
                        <code>{credenciales.client_secret}</code>
                        <button
                          type="button"
                          onClick={() =>
                            copiarValor(
                              t("socioRegistrationPage.client_secret"),
                              credenciales.client_secret,
                            )
                          }
                          aria-label={t("socioRegistrationPage.copiar_client_secret")}
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
                      {t("socioRegistrationPage.valor_copiado", { valor: valorCopiado })}
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
                      {t("socioRegistrationPage.reintentar_generacion")}
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
                {t("socioRegistrationPage.registrar_otro_socio")}
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
                  <h2>{t("socioRegistrationPage.informacion_de_la_organizacion")}</h2>
                  <p>{t("socioRegistrationPage.datos_legales_y_pais_desde")}</p>
                </div>
              </div>

              <div className="socio-form-grid">
                <label>
                  NIT
                  <input
                    name="nit"
                    minLength={5}
                    maxLength={20}
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
                  <small>{t("socioRegistrationPage.sin_puntos_ni_separadores_de")}</small>
                </label>

                <label>
                  {t("socioRegistrationPage.razon_social")}
                  <input
                    name="razon_social"
                    minLength={2}
                    maxLength={160}
                    placeholder={t("socioRegistrationPage.banco_andes_s_a")}
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
                  {t("socioRegistrationPage.pais_de_operacion")}
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
                    <option value="CO">{t("socioRegistrationPage.colombia")}</option>
                    <option value="MX">{t("socioRegistrationPage.mexico")}</option>
                    <option value="PE">{t("socioRegistrationPage.peru")}</option>
                    <option value="CL">{t("socioRegistrationPage.chile")}</option>
                    <option value="AR">{t("socioRegistrationPage.argentina")}</option>
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
                  <h2>{t("socioRegistrationPage.contacto_tecnico")}</h2>
                  <p>{t("socioRegistrationPage.persona_responsable_de_acompanar_la")}</p>
                </div>
              </div>

              <div className="socio-contacts">
                {form.contactos_tecnicos.map((contact, index) => (
                  <div className="socio-contact-row" key={`contact-${index}`}>
                    <div className="socio-form-grid socio-contact-grid">
                      <label>
                        {t("socioRegistrationPage.nombre_completo")}
                        <input
                          name={`contacto_nombre_${index}`}
                          minLength={2}
                          maxLength={120}
                          placeholder={t("socioRegistrationPage.maria_torres")}
                          value={contact.nombre}
                          onChange={(event) =>
                            updateContact(index, "nombre", event.target.value)
                          }
                          required
                        />
                      </label>

                      <label>
                        {t("socioRegistrationPage.correo_corporativo")}
                        <input
                          name={`contacto_correo_${index}`}
                          minLength={5}
                          maxLength={254}
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
                          {t("socioRegistrationPage.telefono")} <span className="socio-optional">{t("socioRegistrationPage.opcional")}</span>
                        </span>
                        <input
                          name={`contacto_telefono_${index}`}
                          type="tel"
                          minLength={7}
                          maxLength={20}
                          pattern={String.raw`\+?[0-9][0-9 \(\)\-]{5,18}[0-9]`}
                          title={t("socioRegistrationPage.usa_entre_7_y_20")}
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
                        {t("socioRegistrationPage.eliminar_contacto")}
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
                  {t("socioRegistrationPage.agregar_otro_contacto")}
                </button>
              </div>
            </section>

            <section className="socio-card">
              <div className="socio-section-heading">
                <span className="material-symbols-outlined" aria-hidden="true">
                  verified_user
                </span>
                <div>
                  <h2>{t("socioRegistrationPage.seguros_autorizados")}</h2>
                  <p>{t("socioRegistrationPage.selecciona_los_productos_que_el")}</p>
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
                  <h2>{t("socioRegistrationPage.permisos_de_api")}</h2>
                  <p>
                    {t("socioRegistrationPage.asigna_unicamente_las_operaciones_necesarias")}
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
                {t("socioRegistrationPage.al_guardar_solventa_creara_la")}
              </p>
              <button
                className="socio-primary-button"
                type="submit"
                disabled={loading}
              >
                <span className="material-symbols-outlined" aria-hidden="true">
                  add_business
                </span>
                {loading ? t("socioRegistrationPage.registrando") : t("socioRegistrationPage.registrar_socio")}
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}

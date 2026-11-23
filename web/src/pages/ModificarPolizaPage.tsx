import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import {
  confirmarEndoso,
  descargarEndoso,
  listarEndosos,
  obtenerOpciones,
  simularEndoso,
  type Beneficiario,
  type Endoso,
  type OpcionesModificacion,
  type PropuestaEndoso,
  type SolicitudModificacion,
} from "../services/endosos.service";
import "../styles/endosos.css";

import { localeActual, t } from "../i18n";

const TIPOS_DOCUMENTO = ["CC", "CE", "TI", "RC", "PA"] as const;

const CONCEPTO: Record<string, string> = {
  get COBRO() { return t("modificarPolizaPage.cobro_adicional"); },
  get DEVOLUCION() { return t("modificarPolizaPage.devolucion_a_tu_favor"); },
  get SIN_AJUSTE() { return t("modificarPolizaPage.sin_cambio_en_la_prima"); },
};

const TIPO_ENDOSO: Record<string, string> = {
  get BENEFICIARIOS() { return t("modificarPolizaPage.beneficiarios"); },
  get COBERTURAS() { return t("modificarPolizaPage.coberturas"); },
  get BENEFICIARIOS_Y_COBERTURAS() { return t("modificarPolizaPage.beneficiarios_y_coberturas"); },
};

type EstadoCobertura = { incluida: boolean; suma: string };

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString(localeActual(), {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: 0,
  });
}

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString(localeActual(), {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Lo que escribe el usuario ("50.000.000") queda en dígitos: la suma se edita en pesos enteros. */
function soloDigitos(escrito: string): string {
  return escrito.replace(/\D/g, "").replace(/^0+(?=\d)/, "");
}

/** Un monto de la API ("50000000.00") en dígitos, sin los centavos. */
function digitosDeMonto(monto: string): string {
  return soloDigitos(monto.split(".")[0]);
}

/** "50000000" -> "50.000.000", para leer la suma sin contar ceros. */
function conSeparadorDeMiles(digitos: string): string {
  return digitos ? Number(digitos).toLocaleString(localeActual(), { maximumFractionDigits: 0 }) : "";
}

function sinDecimalesInnecesarios(valor: string): string {
  return String(Number(valor));
}

function beneficiarioVacio(): Beneficiario {
  return { nombre_completo: "", tipo_documento: "CC", numero_documento: "", parentesco: "", porcentaje: "" };
}

/** Suma en centésimas para no arrastrar errores de punto flotante (33,33 + 33,33 + 33,34). */
function sumaPorcentajes(beneficiarios: Beneficiario[]): number {
  const centesimas = beneficiarios.reduce(
    (total, b) => total + Math.round((Number(b.porcentaje.replace(",", ".")) || 0) * 100),
    0,
  );
  return centesimas / 100;
}

function nuevaClave(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function ModificarPolizaPage() {
  const { polizaId = "" } = useParams();
  const navigate = useNavigate();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [opciones, setOpciones] = useState<OpcionesModificacion | null>(null);
  const [errorCarga, setErrorCarga] = useState("");
  const [coberturas, setCoberturas] = useState<Record<string, EstadoCobertura>>({});
  const [beneficiarios, setBeneficiarios] = useState<Beneficiario[]>([]);
  const [propuesta, setPropuesta] = useState<PropuestaEndoso | null>(null);
  const [clave, setClave] = useState("");
  const [aceptado, setAceptado] = useState(false);
  const [procesando, setProcesando] = useState<"simulando" | "confirmando" | null>(null);
  const [error, setError] = useState("");
  const [emitido, setEmitido] = useState<Endoso | null>(null);
  const [historial, setHistorial] = useState<Endoso[]>([]);
  const [errorDescarga, setErrorDescarga] = useState("");

  const cargar = useCallback(() => {
    return Promise.all([obtenerOpciones(polizaId), listarEndosos(polizaId)]).then(
      ([datos, endosos]) => {
        setOpciones(datos);
        setHistorial(endosos);
        setCoberturas(
          Object.fromEntries(
            datos.coberturas_disponibles.map((disponible) => {
              const actual = datos.coberturas_opcionales.find((c) => c.codigo === disponible.codigo);
              return [
                disponible.codigo,
                {
                  incluida: Boolean(actual),
                  suma: actual ? digitosDeMonto(actual.suma_asegurada) : "",
                },
              ];
            }),
          ),
        );
        setBeneficiarios(
          datos.beneficiarios.map((b) => ({ ...b, porcentaje: sinDecimalesInnecesarios(b.porcentaje) })),
        );
        setErrorCarga("");
      },
      (fallo: Error) => { setErrorCarga(fallo.message); },
    );
  }, [polizaId]);

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => { if (activo) setPerfil(datos); },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    void cargar();
    return () => { activo = false; };
  }, [navigate, cargar]);

  const totalPorcentaje = useMemo(() => sumaPorcentajes(beneficiarios), [beneficiarios]);

  /** Cualquier edición invalida el cálculo anterior: hay que volver a calcular el ajuste. */
  function editado() {
    setPropuesta(null);
    setAceptado(false);
    setError("");
    setEmitido(null);
  }

  function cambiarCobertura(codigo: string, cambio: Partial<EstadoCobertura>) {
    setCoberturas((previo) => ({ ...previo, [codigo]: { ...previo[codigo], ...cambio } }));
    editado();
  }

  function cambiarBeneficiario(indice: number, cambio: Partial<Beneficiario>) {
    setBeneficiarios((previo) => previo.map((b, i) => (i === indice ? { ...b, ...cambio } : b)));
    editado();
  }

  function solicitud(): SolicitudModificacion {
    if (!opciones) return {};
    const resultado: SolicitudModificacion = {
      coberturas_opcionales: opciones.coberturas_disponibles
        .filter((d) => coberturas[d.codigo]?.incluida)
        .map((d) => ({ codigo: d.codigo, suma_asegurada: coberturas[d.codigo].suma })),
    };
    if (opciones.admite_beneficiarios) {
      resultado.beneficiarios = beneficiarios.map((b) => ({
        ...b,
        nombre_completo: b.nombre_completo.trim(),
        numero_documento: b.numero_documento.trim(),
        parentesco: b.parentesco.trim(),
        porcentaje: b.porcentaje.replace(",", "."),
      }));
    }
    return resultado;
  }

  async function calcular() {
    setProcesando("simulando");
    setError("");
    try {
      setPropuesta(await simularEndoso(polizaId, solicitud()));
      setClave(nuevaClave());
      setAceptado(false);
    } catch (fallo) {
      setPropuesta(null);
      setError((fallo as Error).message);
    } finally {
      setProcesando(null);
    }
  }

  async function confirmar() {
    setProcesando("confirmando");
    setError("");
    try {
      const endoso = await confirmarEndoso(polizaId, solicitud(), clave);
      setPropuesta(null);
      setAceptado(false);
      await cargar();
      setEmitido(endoso);
    } catch (fallo) {
      setError((fallo as Error).message);
    } finally {
      setProcesando(null);
    }
  }

  async function descargar(endosoId: string) {
    setErrorDescarga("");
    try {
      await descargarEndoso(polizaId, endosoId);
    } catch (fallo) {
      setErrorDescarga((fallo as Error).message);
    }
  }

  const rol = perfil?.rol ?? null;
  const bloqueada = !opciones?.modificable || procesando !== null;
  const porcentajesValidos = beneficiarios.length === 0 || totalPorcentaje === 100;
  const sumasCompletas = (opciones?.coberturas_disponibles ?? []).every(
    (d) => !coberturas[d.codigo]?.incluida || coberturas[d.codigo].suma !== "",
  );

  return (
    <AppLayout activo="Mis pólizas" rol={rol}>
      <header className="home-header">
        <div>
          <h1>{t("modificarPolizaPage.modificar_poliza")}</h1>
          <p>
            {opciones
              ? `${opciones.nombre_ramo} · ${opciones.numero_poliza}`
              : t("modificarPolizaPage.ajusta_tus_coberturas_opcionales_y")}
          </p>
        </div>
        <button type="button" className="cotizar-boton-secundario" onClick={() => navigate("/polizas")}>
          {t("modificarPolizaPage.volver_a_mis_polizas")}
        </button>
      </header>

      {errorCarga && <p role="alert" className="home-aviso">{errorCarga}</p>}
      {!opciones && !errorCarga && <p role="status" className="home-card-vacio">{t("modificarPolizaPage.cargando_la_poliza")}</p>}

      {opciones && (
        <div className="endoso-pagina">
          {!opciones.modificable && (
            <p role="alert" className="home-aviso">
              {t("modificarPolizaPage.esta_poliza_ya_no_esta")}
            </p>
          )}

          {emitido && (
            <section className="home-panel" aria-label={t("modificarPolizaPage.endoso_emitido")}>
              <p className="cotizar-mensaje-ok" role="status">
                {t("modificarPolizaPage.listo_emitimos_el_endoso_no", { numero_endoso: emitido.numero_endoso })}
              </p>
              <button type="button" className="cotizar-boton-primario" onClick={() => void descargar(emitido.endoso_id)}>
                <span className="material-symbols-outlined" aria-hidden="true">download</span>
                {t("modificarPolizaPage.descargar_endoso_pdf")}
              </button>
            </section>
          )}

          <section className="home-panel endoso-seccion" aria-labelledby="titulo-coberturas">
            <h2 id="titulo-coberturas">{t("modificarPolizaPage.coberturas_opcionales")}</h2>
            <p>{t("modificarPolizaPage.incluye_ajusta_o_excluye_amparos")}</p>
            <p className="endoso-principal">
              {t("modificarPolizaPage.cobertura_principal")} <strong>{opciones.cobertura_principal.nombre}</strong>{" "}
              {t("modificarPolizaPage.por_monto", { monto: formatearMonto(opciones.cobertura_principal.suma_asegurada, opciones.moneda) })}
            </p>
            {opciones.coberturas_disponibles.length === 0 ? (
              <p className="home-card-vacio">{t("modificarPolizaPage.este_seguro_no_tiene_coberturas")}</p>
            ) : (
              <div className="endoso-coberturas">
                {opciones.coberturas_disponibles.map((disponible) => {
                  const estado = coberturas[disponible.codigo] ?? { incluida: false, suma: "" };
                  const idSuma = `suma-${disponible.codigo}`;
                  return (
                    <div
                      key={disponible.codigo}
                      className={`endoso-cobertura ${estado.incluida ? "endoso-cobertura-activa" : ""}`}
                    >
                      <label>
                        <input
                          type="checkbox"
                          checked={estado.incluida}
                          disabled={bloqueada}
                          onChange={(e) => cambiarCobertura(disponible.codigo, { incluida: e.target.checked })}
                        />
                        <span>
                          <strong>{disponible.nombre}</strong>
                          <small>{disponible.descripcion}</small>
                        </span>
                      </label>
                      <div className="cotizar-campo">
                        <label htmlFor={idSuma}>{t("modificarPolizaPage.suma_asegurada")}</label>
                        <input
                          id={idSuma}
                          aria-label={t("modificarPolizaPage.suma_asegurada_de_nombre", { nombre: disponible.nombre })}
                          type="text"
                          inputMode="numeric"
                          autoComplete="off"
                          placeholder={estado.incluida ? t("modificarPolizaPage.escribe_la_suma") : t("modificarPolizaPage.no_incluida")}
                          value={estado.incluida ? conSeparadorDeMiles(estado.suma) : ""}
                          disabled={bloqueada || !estado.incluida}
                          onChange={(e) => cambiarCobertura(disponible.codigo, { suma: soloDigitos(e.target.value) })}
                        />
                        <span className="cotizar-ayuda">
                          {t("modificarPolizaPage.entre_formatearmonto_y_formatearmonto2", { formatearMonto: formatearMonto(disponible.suma_minima, opciones.moneda), formatearMonto2: formatearMonto(disponible.suma_maxima, opciones.moneda) })}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {opciones.admite_beneficiarios && (
            <section className="home-panel endoso-seccion" aria-labelledby="titulo-beneficiarios">
              <h2 id="titulo-beneficiarios">{t("modificarPolizaPage.beneficiarios")}</h2>
              <p>{t("modificarPolizaPage.los_porcentajes_deben_sumar_exactamente")}</p>
              {beneficiarios.map((b, indice) => {
                const id = (campo: string) => `beneficiario-${indice}-${campo}`;
                const numero = indice + 1;
                return (
                  <fieldset key={indice} className="endoso-beneficiario" disabled={bloqueada} aria-label={t("modificarPolizaPage.beneficiario_numero", { numero: numero })}>
                    <div className="cotizar-campo">
                      <label htmlFor={id("nombre")}>{t("modificarPolizaPage.nombre_completo")}</label>
                      <input id={id("nombre")} value={b.nombre_completo} onChange={(e) => cambiarBeneficiario(indice, { nombre_completo: e.target.value })} />
                    </div>
                    <div className="cotizar-campo">
                      <label htmlFor={id("tipo")}>{t("modificarPolizaPage.tipo")}</label>
                      <select id={id("tipo")} value={b.tipo_documento} onChange={(e) => cambiarBeneficiario(indice, { tipo_documento: e.target.value })}>
                        {TIPOS_DOCUMENTO.map((tipo) => <option key={tipo} value={tipo}>{tipo}</option>)}
                      </select>
                    </div>
                    <div className="cotizar-campo">
                      <label htmlFor={id("documento")}>{t("modificarPolizaPage.documento")}</label>
                      <input id={id("documento")} value={b.numero_documento} onChange={(e) => cambiarBeneficiario(indice, { numero_documento: e.target.value })} />
                    </div>
                    <div className="cotizar-campo">
                      <label htmlFor={id("parentesco")}>{t("modificarPolizaPage.parentesco")}</label>
                      <input id={id("parentesco")} value={b.parentesco} onChange={(e) => cambiarBeneficiario(indice, { parentesco: e.target.value })} />
                    </div>
                    <div className="cotizar-campo">
                      <label htmlFor={id("porcentaje")}>{t("modificarPolizaPage.porcentaje")}</label>
                      <input id={id("porcentaje")} type="number" inputMode="decimal" min={0.01} max={100} step={0.01} value={b.porcentaje} onChange={(e) => cambiarBeneficiario(indice, { porcentaje: e.target.value })} />
                    </div>
                    <button
                      type="button"
                      className="endoso-quitar"
                      aria-label={t("modificarPolizaPage.quitar_beneficiario_numero", { numero: numero })}
                      onClick={() => { setBeneficiarios((previo) => previo.filter((_, i) => i !== indice)); editado(); }}
                    >
                      <span className="material-symbols-outlined" aria-hidden="true">delete</span>
                    </button>
                  </fieldset>
                );
              })}
              <div className="endoso-total">
                <button
                  type="button"
                  className="cotizar-boton-secundario"
                  disabled={bloqueada || beneficiarios.length >= opciones.max_beneficiarios}
                  onClick={() => { setBeneficiarios((previo) => [...previo, beneficiarioVacio()]); editado(); }}
                >
                  {t("modificarPolizaPage.agregar_beneficiario")}
                </button>
                {beneficiarios.length > 0 && (
                  <span className={porcentajesValidos ? "endoso-total-ok" : "endoso-total-error"} aria-live="polite">
                    {t("modificarPolizaPage.suman_tolocalestring", { porcentaje: totalPorcentaje.toLocaleString(localeActual()) })}
                  </span>
                )}
              </div>
            </section>
          )}

          {error && <p role="alert" className="home-aviso">{error}</p>}

          {!propuesta && (
            <div className="cotizar-acciones">
              <button
                type="button"
                className="cotizar-boton-primario"
                disabled={bloqueada || !porcentajesValidos || !sumasCompletas}
                onClick={() => void calcular()}
              >
                {procesando === "simulando" ? t("modificarPolizaPage.calculando") : t("modificarPolizaPage.calcular_ajuste_de_prima")}
              </button>
            </div>
          )}

          {propuesta && (
            <section className="home-panel endoso-seccion" aria-labelledby="titulo-propuesta">
              <h2 id="titulo-propuesta">{t("modificarPolizaPage.revisa_los_cambios")}</h2>
              <p>{t("modificarPolizaPage.rige_desde_el_formatearfecha_el", { formatearFecha: formatearFecha(propuesta.fecha_efecto), dias_restantes: propuesta.dias_restantes, dias_vigencia: propuesta.dias_vigencia })}</p>
              <ul className="endoso-cambios">
                {propuesta.cambios.map((cambio, i) => <li key={i}>{cambio.descripcion}</li>)}
              </ul>
              <dl className="cotizar-resumen">
                <div><dt>{t("modificarPolizaPage.prima_actual")}</dt><dd>{formatearMonto(propuesta.prima_anterior, propuesta.moneda)}</dd></div>
                <div>
                  <dt>{CONCEPTO[propuesta.concepto_ajuste]}</dt>
                  <dd>{formatearMonto(String(Math.abs(Number(propuesta.ajuste_prima))), propuesta.moneda)}</dd>
                </div>
                <div className="cotizar-resumen-total"><dt>{t("modificarPolizaPage.nueva_prima_total")}</dt><dd>{formatearMonto(propuesta.prima_nueva, propuesta.moneda)}</dd></div>
              </dl>
              <label className="endoso-aceptar">
                <input type="checkbox" checked={aceptado} onChange={(e) => setAceptado(e.target.checked)} />
                {t("modificarPolizaPage.acepto_estos_cambios_y_el")}
              </label>
              <div className="cotizar-acciones">
                <button type="button" className="cotizar-boton-secundario" disabled={procesando !== null} onClick={editado}>
                  {t("modificarPolizaPage.seguir_editando")}
                </button>
                <button
                  type="button"
                  className="cotizar-boton-primario"
                  disabled={!aceptado || procesando !== null}
                  onClick={() => void confirmar()}
                >
                  {procesando === "confirmando" ? t("modificarPolizaPage.emitiendo") : t("modificarPolizaPage.confirmar_y_emitir_endoso")}
                </button>
              </div>
            </section>
          )}

          <section className="home-panel endoso-seccion" aria-labelledby="titulo-historial">
            <h2 id="titulo-historial">{t("modificarPolizaPage.endosos_de_esta_poliza")}</h2>
            {historial.length === 0 ? (
              <p className="home-card-vacio">{t("modificarPolizaPage.esta_poliza_aun_no_tiene")}</p>
            ) : (
              <ul className="endoso-historial">
                {historial.map((endoso) => (
                  <li key={endoso.endoso_id}>
                    <span>
                      <strong>{t("modificarPolizaPage.endoso_no_numero_endoso_valor", { numero_endoso: endoso.numero_endoso, valor: TIPO_ENDOSO[endoso.tipo] ?? endoso.tipo })}</strong>
                      <small>
                        {formatearFecha(endoso.creado_en)} · {CONCEPTO[endoso.concepto_ajuste]}{" "}
                        {endoso.concepto_ajuste !== "SIN_AJUSTE" &&
                          formatearMonto(String(Math.abs(Number(endoso.ajuste_prima))), endoso.moneda)}
                      </small>
                    </span>
                    <button
                      type="button"
                      className="endoso-enlace"
                      aria-label={t("modificarPolizaPage.descargar_endoso_no_numero_endoso", { numero_endoso: endoso.numero_endoso })}
                      onClick={() => void descargar(endoso.endoso_id)}
                    >
                      <span className="material-symbols-outlined" aria-hidden="true">download</span>
                      PDF
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {errorDescarga && <p role="alert" className="home-aviso">{errorDescarga}</p>}
          </section>
        </div>
      )}
    </AppLayout>
  );
}

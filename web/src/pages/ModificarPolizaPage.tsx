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

const TIPOS_DOCUMENTO = ["CC", "CE", "TI", "RC", "PA"] as const;

const CONCEPTO: Record<string, string> = {
  COBRO: "Cobro adicional",
  DEVOLUCION: "Devolución a tu favor",
  SIN_AJUSTE: "Sin cambio en la prima",
};

const TIPO_ENDOSO: Record<string, string> = {
  BENEFICIARIOS: "Beneficiarios",
  COBERTURAS: "Coberturas",
  BENEFICIARIOS_Y_COBERTURAS: "Beneficiarios y coberturas",
};

type EstadoCobertura = { incluida: boolean; suma: string };

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString("es-CO", {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: 0,
  });
}

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString("es-CO", {
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
  return digitos ? Number(digitos).toLocaleString("es-CO", { maximumFractionDigits: 0 }) : "";
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
          <h1>Modificar póliza</h1>
          <p>
            {opciones
              ? `${opciones.nombre_ramo} · ${opciones.numero_poliza}`
              : "Ajusta tus coberturas opcionales y beneficiarios."}
          </p>
        </div>
        <button type="button" className="cotizar-boton-secundario" onClick={() => navigate("/polizas")}>
          Volver a mis pólizas
        </button>
      </header>

      {errorCarga && <p role="alert" className="home-aviso">{errorCarga}</p>}
      {!opciones && !errorCarga && <p role="status" className="home-card-vacio">Cargando la póliza…</p>}

      {opciones && (
        <div className="endoso-pagina">
          {!opciones.modificable && (
            <p role="alert" className="home-aviso">
              Esta póliza ya no está vigente, así que no admite cambios.
            </p>
          )}

          {emitido && (
            <section className="home-panel" aria-label="Endoso emitido">
              <p className="cotizar-mensaje-ok" role="status">
                Listo. Emitimos el endoso No. {emitido.numero_endoso} y ya rige sobre tu póliza.
              </p>
              <button type="button" className="cotizar-boton-primario" onClick={() => void descargar(emitido.endoso_id)}>
                <span className="material-symbols-outlined" aria-hidden="true">download</span>
                Descargar endoso (PDF)
              </button>
            </section>
          )}

          <section className="home-panel endoso-seccion" aria-labelledby="titulo-coberturas">
            <h2 id="titulo-coberturas">Coberturas opcionales</h2>
            <p>Incluye, ajusta o excluye amparos adicionales. El cambio se cobra o devuelve solo por los días que le quedan a la póliza.</p>
            <p className="endoso-principal">
              Cobertura principal: <strong>{opciones.cobertura_principal.nombre}</strong> por{" "}
              {formatearMonto(opciones.cobertura_principal.suma_asegurada, opciones.moneda)}
            </p>
            {opciones.coberturas_disponibles.length === 0 ? (
              <p className="home-card-vacio">Este seguro no tiene coberturas opcionales.</p>
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
                        <label htmlFor={idSuma}>Suma asegurada</label>
                        <input
                          id={idSuma}
                          aria-label={`Suma asegurada de ${disponible.nombre}`}
                          type="text"
                          inputMode="numeric"
                          autoComplete="off"
                          placeholder={estado.incluida ? "Escribe la suma" : "No incluida"}
                          value={estado.incluida ? conSeparadorDeMiles(estado.suma) : ""}
                          disabled={bloqueada || !estado.incluida}
                          onChange={(e) => cambiarCobertura(disponible.codigo, { suma: soloDigitos(e.target.value) })}
                        />
                        <span className="cotizar-ayuda">
                          Entre {formatearMonto(disponible.suma_minima, opciones.moneda)} y{" "}
                          {formatearMonto(disponible.suma_maxima, opciones.moneda)}
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
              <h2 id="titulo-beneficiarios">Beneficiarios</h2>
              <p>Los porcentajes deben sumar exactamente 100 %. Si no designas a nadie, la indemnización va a tus herederos legales.</p>
              {beneficiarios.map((b, indice) => {
                const id = (campo: string) => `beneficiario-${indice}-${campo}`;
                const numero = indice + 1;
                return (
                  <fieldset key={indice} className="endoso-beneficiario" disabled={bloqueada} aria-label={`Beneficiario ${numero}`}>
                    <div className="cotizar-campo">
                      <label htmlFor={id("nombre")}>Nombre completo</label>
                      <input id={id("nombre")} value={b.nombre_completo} onChange={(e) => cambiarBeneficiario(indice, { nombre_completo: e.target.value })} />
                    </div>
                    <div className="cotizar-campo">
                      <label htmlFor={id("tipo")}>Tipo</label>
                      <select id={id("tipo")} value={b.tipo_documento} onChange={(e) => cambiarBeneficiario(indice, { tipo_documento: e.target.value })}>
                        {TIPOS_DOCUMENTO.map((tipo) => <option key={tipo} value={tipo}>{tipo}</option>)}
                      </select>
                    </div>
                    <div className="cotizar-campo">
                      <label htmlFor={id("documento")}>Documento</label>
                      <input id={id("documento")} value={b.numero_documento} onChange={(e) => cambiarBeneficiario(indice, { numero_documento: e.target.value })} />
                    </div>
                    <div className="cotizar-campo">
                      <label htmlFor={id("parentesco")}>Parentesco</label>
                      <input id={id("parentesco")} value={b.parentesco} onChange={(e) => cambiarBeneficiario(indice, { parentesco: e.target.value })} />
                    </div>
                    <div className="cotizar-campo">
                      <label htmlFor={id("porcentaje")}>Porcentaje</label>
                      <input id={id("porcentaje")} type="number" inputMode="decimal" min={0.01} max={100} step={0.01} value={b.porcentaje} onChange={(e) => cambiarBeneficiario(indice, { porcentaje: e.target.value })} />
                    </div>
                    <button
                      type="button"
                      className="endoso-quitar"
                      aria-label={`Quitar beneficiario ${numero}`}
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
                  Agregar beneficiario
                </button>
                {beneficiarios.length > 0 && (
                  <span className={porcentajesValidos ? "endoso-total-ok" : "endoso-total-error"} aria-live="polite">
                    Suman {totalPorcentaje.toLocaleString("es-CO")} %
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
                {procesando === "simulando" ? "Calculando…" : "Calcular ajuste de prima"}
              </button>
            </div>
          )}

          {propuesta && (
            <section className="home-panel endoso-seccion" aria-labelledby="titulo-propuesta">
              <h2 id="titulo-propuesta">Revisa los cambios</h2>
              <p>Rige desde el {formatearFecha(propuesta.fecha_efecto)}. El ajuste corresponde a {propuesta.dias_restantes} de {propuesta.dias_vigencia} días de vigencia.</p>
              <ul className="endoso-cambios">
                {propuesta.cambios.map((cambio, i) => <li key={i}>{cambio.descripcion}</li>)}
              </ul>
              <dl className="cotizar-resumen">
                <div><dt>Prima actual</dt><dd>{formatearMonto(propuesta.prima_anterior, propuesta.moneda)}</dd></div>
                <div>
                  <dt>{CONCEPTO[propuesta.concepto_ajuste]}</dt>
                  <dd>{formatearMonto(String(Math.abs(Number(propuesta.ajuste_prima))), propuesta.moneda)}</dd>
                </div>
                <div className="cotizar-resumen-total"><dt>Nueva prima total</dt><dd>{formatearMonto(propuesta.prima_nueva, propuesta.moneda)}</dd></div>
              </dl>
              <label className="endoso-aceptar">
                <input type="checkbox" checked={aceptado} onChange={(e) => setAceptado(e.target.checked)} />
                Acepto estos cambios y el ajuste de prima. Entiendo que el endoso queda registrado a mi nombre.
              </label>
              <div className="cotizar-acciones">
                <button type="button" className="cotizar-boton-secundario" disabled={procesando !== null} onClick={editado}>
                  Seguir editando
                </button>
                <button
                  type="button"
                  className="cotizar-boton-primario"
                  disabled={!aceptado || procesando !== null}
                  onClick={() => void confirmar()}
                >
                  {procesando === "confirmando" ? "Emitiendo…" : "Confirmar y emitir endoso"}
                </button>
              </div>
            </section>
          )}

          <section className="home-panel endoso-seccion" aria-labelledby="titulo-historial">
            <h2 id="titulo-historial">Endosos de esta póliza</h2>
            {historial.length === 0 ? (
              <p className="home-card-vacio">Esta póliza aún no tiene endosos.</p>
            ) : (
              <ul className="endoso-historial">
                {historial.map((endoso) => (
                  <li key={endoso.endoso_id}>
                    <span>
                      <strong>Endoso No. {endoso.numero_endoso} · {TIPO_ENDOSO[endoso.tipo] ?? endoso.tipo}</strong>
                      <small>
                        {formatearFecha(endoso.creado_en)} · {CONCEPTO[endoso.concepto_ajuste]}{" "}
                        {endoso.concepto_ajuste !== "SIN_AJUSTE" &&
                          formatearMonto(String(Math.abs(Number(endoso.ajuste_prima))), endoso.moneda)}
                      </small>
                    </span>
                    <button
                      type="button"
                      className="endoso-enlace"
                      aria-label={`Descargar endoso No. ${endoso.numero_endoso}`}
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

import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import {
  crearCotizacion,
  obtenerCotizacion,
  obtenerRamos,
} from "../services/cotizaciones.service";
import { crearPago, obtenerPago, type Pago } from "../services/pagos.service";
import type {
  CampoRiesgo,
  Cotizacion,
  DefinicionRamo,
  RamoSeguro,
} from "../types/cotizaciones";

/** Icono de Material Symbols para cada ramo. */
const ICONO_RAMO: Record<RamoSeguro, string> = {
  VIAJE: "flight_takeoff",
  PROTECCION_DISPOSITIVOS: "devices",
  VIDA: "favorite",
  PARAMETRICO: "thunderstorm",
};

type Paso = "ramo" | "formulario" | "resultado" | "pago" | "confirmacion";

const METODOS_PAGO = [
  { valor: "TARJETA", etiqueta: "Tarjeta de crédito o débito", icono: "credit_card" },
  { valor: "PSE", etiqueta: "PSE (débito bancario)", icono: "account_balance" },
] as const;

type MetodoPago = (typeof METODOS_PAGO)[number]["valor"];

/** Bancos simulados para el flujo PSE (desarrollo). */
const BANCOS_PSE = [
  { codigo: "1007", nombre: "Bancolombia" },
  { codigo: "1051", nombre: "Davivienda" },
  { codigo: "1001", nombre: "Banco de Bogotá" },
  { codigo: "1023", nombre: "Banco de Occidente" },
  { codigo: "1062", nombre: "Banco Falabella" },
  { codigo: "1151", nombre: "Nequi" },
] as const;

function formatearMonto(monto: string, moneda: string): string {
  return Number(monto).toLocaleString("es-CO", {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: 0,
  });
}

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Convierte el valor del input al tipo que espera el backend para cada campo. */
function convertirValor(campo: CampoRiesgo, valor: string): unknown {
  if (valor === "") return undefined;
  if (campo.tipo === "ENTERO") return Number.parseInt(valor, 10);
  if (campo.tipo === "DECIMAL") return Number(valor);
  if (campo.tipo === "BOOLEANO") return valor === "true";
  return valor;
}

function tipoInput(campo: CampoRiesgo): string {
  if (campo.tipo === "FECHA") return "date";
  if (campo.tipo === "ENTERO" || campo.tipo === "DECIMAL") return "number";
  return "text";
}

/** Agrupa los dígitos del número de tarjeta en bloques de 4 para mostrarlos. */
function formatearNumeroTarjeta(valor: string): string {
  const digitos = valor.replace(/\D/g, "").slice(0, 16);
  return digitos.replace(/(.{4})/g, "$1 ").trim();
}

/** Formatea el vencimiento como MM/AA mientras se escribe. */
function formatearVencimiento(valor: string): string {
  const digitos = valor.replace(/\D/g, "").slice(0, 4);
  if (digitos.length <= 2) return digitos;
  return `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
}

/**
 * Simula la tokenización que haría el SDK de la pasarela: los datos sensibles de la
 * tarjeta nunca se envían al backend; se convierten en un token de un solo uso.
 * Para desarrollo, una tarjeta terminada en 0 fuerza un rechazo (como tarjeta sin fondos).
 */
function tokenizarTarjeta(numero: string): string {
  const digitos = numero.replace(/\D/g, "");
  const prefijo = digitos.endsWith("0") ? "tok_rechazado" : "tok_visa";
  const aleatorio = crypto.randomUUID().replace(/-/g, "").slice(0, 16);
  return `${prefijo}_${aleatorio}`;
}

export default function CotizarPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [ramos, setRamos] = useState<DefinicionRamo[] | null>(null);
  const [errorCarga, setErrorCarga] = useState("");

  const [paso, setPaso] = useState<Paso>("ramo");
  const [ramoSeleccionado, setRamoSeleccionado] = useState<DefinicionRamo | null>(null);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [cotizacion, setCotizacion] = useState<Cotizacion | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [errorForm, setErrorForm] = useState("");

  const [metodoPago, setMetodoPago] = useState<MetodoPago>("TARJETA");
  const [numeroTarjeta, setNumeroTarjeta] = useState("");
  const [vencimiento, setVencimiento] = useState("");
  const [cvv, setCvv] = useState("");
  const [codigoBanco, setCodigoBanco] = useState("");
  const [pagando, setPagando] = useState(false);
  const [errorPago, setErrorPago] = useState("");
  const [pago, setPago] = useState<Pago | null>(null);
  // Una llave por intento de pago: se mantiene mientras no cambie la cotización,
  // para que un reintento por red no genere un segundo cobro (HU13).
  const [idempotencyKey, setIdempotencyKey] = useState("");

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => { if (activo) setPerfil(datos); },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    obtenerRamos().then(
      (datos) => { if (activo) setRamos(datos); },
      (fallo: Error) => { if (activo) setErrorCarga(fallo.message); },
    );
    return () => { activo = false; };
  }, [navigate]);

  // Regreso desde el portal PSE: la URL trae ?pago=...; se consulta y se muestra el resultado.
  const pagoRetornoProcesado = useRef<string | null>(null);
  useEffect(() => {
    const pagoId = searchParams.get("pago");
    if (!pagoId || pagoRetornoProcesado.current === pagoId) return;
    pagoRetornoProcesado.current = pagoId;
    // Limpia los parámetros de la URL; la ref evita volver a procesar este mismo pago.
    setSearchParams({}, { replace: true });
    obtenerPago(pagoId).then(
      (datos) => {
        setPago(datos);
        setPaso("confirmacion");
        // Recupera la cotización para que "Reintentar pago" pueda volver a cobrarla.
        obtenerCotizacion(datos.cotizacion_id).then(
          (cot) => setCotizacion(cot),
          () => undefined,
        );
      },
      () => setErrorCarga("No fue posible consultar el resultado del pago."),
    );
  }, [searchParams, setSearchParams]);

  const rol = perfil?.rol ?? null;

  const faltanRequeridos = useMemo(() => {
    if (!ramoSeleccionado) return true;
    return ramoSeleccionado.campos.some(
      (campo) => campo.requerido && !valores[campo.codigo]?.trim(),
    );
  }, [ramoSeleccionado, valores]);

  function elegirRamo(ramo: DefinicionRamo) {
    setRamoSeleccionado(ramo);
    setValores(
      Object.fromEntries(
        ramo.campos.map((campo) => [campo.codigo, campo.tipo === "BOOLEANO" ? "false" : ""]),
      ),
    );
    setErrorForm("");
    setPaso("formulario");
  }

  function actualizarCampo(codigo: string, valor: string) {
    setValores((previo) => ({ ...previo, [codigo]: valor }));
  }

  async function enviarFormulario(evento: React.FormEvent) {
    evento.preventDefault();
    if (!ramoSeleccionado || !perfil?.id) {
      setErrorForm("No fue posible identificar tu cuenta. Inicia sesión nuevamente.");
      return;
    }

    const datosRiesgo: Record<string, unknown> = {};
    for (const campo of ramoSeleccionado.campos) {
      const convertido = convertirValor(campo, valores[campo.codigo] ?? "");
      if (convertido !== undefined) datosRiesgo[campo.codigo] = convertido;
    }

    setEnviando(true);
    setErrorForm("");
    try {
      const resultado = await crearCotizacion({
        cliente_id: perfil.id,
        ramo: ramoSeleccionado.ramo,
        datos_riesgo: datosRiesgo,
      });
      setCotizacion(resultado);
      setPaso("resultado");
    } catch (fallo) {
      setErrorForm((fallo as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  function reiniciar() {
    setRamoSeleccionado(null);
    setValores({});
    setCotizacion(null);
    setErrorForm("");
    setMetodoPago("TARJETA");
    setNumeroTarjeta("");
    setVencimiento("");
    setCvv("");
    setCodigoBanco("");
    setErrorPago("");
    setPago(null);
    setIdempotencyKey("");
    setPaso("ramo");
  }

  function irAPagar() {
    if (!cotizacion) return;
    // HU23: el cliente aceptó; se genera la llave de idempotencia de este intento.
    setErrorPago("");
    setPago(null);
    setIdempotencyKey(crypto.randomUUID());
    setPaso("pago");
  }

  async function procesarPago(evento: React.FormEvent) {
    evento.preventDefault();
    if (!cotizacion) return;

    setPagando(true);
    setErrorPago("");
    try {
      const resultado = await crearPago(
        {
          cotizacion_id: cotizacion.cotizacion_id,
          metodo: metodoPago,
          ...(metodoPago === "TARJETA"
            ? { token_tarjeta: tokenizarTarjeta(numeroTarjeta) }
            : {
                codigo_banco: codigoBanco,
                // Al volver del portal PSE, el banco nos regresa a esta página.
                url_retorno: `${window.location.origin}/cotizar`,
              }),
        },
        idempotencyKey,
      );
      // PSE: el cobro queda pendiente y el cliente debe ir al portal de su banco.
      if (metodoPago === "PSE" && resultado.url_redireccion) {
        window.location.href = resultado.url_redireccion;
        return;
      }
      setPago(resultado);
      setPaso("confirmacion");
    } catch (fallo) {
      setErrorPago((fallo as Error).message);
    } finally {
      setPagando(false);
    }
  }

  function reintentarPago() {
    // Nuevo intento tras un rechazo: llave nueva para no chocar con el pago rechazado.
    if (!cotizacion) return;
    setPago(null);
    setErrorPago("");
    setNumeroTarjeta("");
    setVencimiento("");
    setCvv("");
    setIdempotencyKey(crypto.randomUUID());
    setPaso("pago");
  }

  return (
    <AppLayout activo="Mis cotizaciones" rol={rol}>
      <header className="home-header">
        <div>
          <h1>Cotizar un nuevo seguro</h1>
          <p>
            {paso === "ramo" && "Elige el tipo de seguro que quieres cotizar."}
            {paso === "formulario" && "Completa los datos para calcular tu prima."}
            {paso === "resultado" && "Revisa tu cotización antes de continuar."}
            {paso === "pago" && "Elige cómo quieres pagar la prima inicial."}
            {paso === "confirmacion" && "Resultado de tu pago."}
          </p>
        </div>
      </header>

      {errorCarga && <p role="alert" className="home-aviso">{errorCarga}</p>}

      {/* Paso 1: selección de ramo */}
      {paso === "ramo" && (
        <section aria-label="Tipos de seguro" className="cotizar-ramos">
          {ramos === null && !errorCarga && (
            <p role="status" className="home-card-vacio">Cargando ramos disponibles…</p>
          )}
          <div className="cotizar-grid-ramos">
            {ramos?.map((ramo) => (
              <button
                key={ramo.ramo}
                type="button"
                className="cotizar-ramo-card"
                onClick={() => elegirRamo(ramo)}
              >
                <span className="cotizar-ramo-icono material-symbols-outlined" aria-hidden="true">
                  {ICONO_RAMO[ramo.ramo]}
                </span>
                <strong>{ramo.nombre}</strong>
                <small>{ramo.descripcion}</small>
                <span className="cotizar-ramo-cta">
                  Cotizar
                  <span className="material-symbols-outlined" aria-hidden="true">arrow_forward</span>
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Paso 2: formulario del ramo */}
      {paso === "formulario" && ramoSeleccionado && (
        <section className="home-panel cotizar-form-panel" aria-label="Datos del riesgo">
          <div className="cotizar-form-encabezado">
            <span className="cotizar-ramo-icono material-symbols-outlined" aria-hidden="true">
              {ICONO_RAMO[ramoSeleccionado.ramo]}
            </span>
            <div>
              <strong>{ramoSeleccionado.nombre}</strong>
              <small>{ramoSeleccionado.descripcion}</small>
            </div>
          </div>

          {errorForm && <p role="alert" className="home-aviso">{errorForm}</p>}

          <form onSubmit={enviarFormulario} className="cotizar-form">
            {ramoSeleccionado.campos.map((campo) => (
              <div className="cotizar-campo" key={campo.codigo}>
                <label htmlFor={campo.codigo}>
                  {campo.etiqueta}
                  {campo.unidad ? ` (${campo.unidad})` : ""}
                  {!campo.requerido && <span className="cotizar-opcional"> · opcional</span>}
                </label>

                {campo.tipo === "OPCION" ? (
                  <select
                    id={campo.codigo}
                    value={valores[campo.codigo] ?? ""}
                    required={campo.requerido}
                    onChange={(e) => actualizarCampo(campo.codigo, e.target.value)}
                  >
                    <option value="">Selecciona una opción</option>
                    {campo.opciones.map((opcion) => (
                      <option key={opcion} value={opcion}>{opcion}</option>
                    ))}
                  </select>
                ) : campo.tipo === "BOOLEANO" ? (
                  <select
                    id={campo.codigo}
                    value={valores[campo.codigo] ?? "false"}
                    onChange={(e) => actualizarCampo(campo.codigo, e.target.value)}
                  >
                    <option value="false">No</option>
                    <option value="true">Sí</option>
                  </select>
                ) : (
                  <input
                    id={campo.codigo}
                    type={tipoInput(campo)}
                    inputMode={campo.tipo === "DECIMAL" || campo.tipo === "ENTERO" ? "numeric" : undefined}
                    step={campo.tipo === "DECIMAL" ? "0.01" : undefined}
                    value={valores[campo.codigo] ?? ""}
                    required={campo.requerido}
                    onChange={(e) => actualizarCampo(campo.codigo, e.target.value)}
                  />
                )}
                <small className="cotizar-ayuda">{campo.descripcion}</small>
              </div>
            ))}

            <div className="cotizar-acciones">
              <button type="button" className="cotizar-boton-secundario" onClick={reiniciar}>
                Volver
              </button>
              <button
                type="submit"
                className="cotizar-boton-primario"
                disabled={enviando || faltanRequeridos}
              >
                {enviando ? "Calculando…" : "Continuar"}
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Paso 3: resultado de la cotización (HU23: aceptar o cancelar) */}
      {paso === "resultado" && cotizacion && (
        <section className="home-panel cotizar-resultado" aria-label="Resumen de la cotización">
          <div className="cotizar-resultado-encabezado">
            <span className="cotizar-ramo-icono material-symbols-outlined" aria-hidden="true">
              {ICONO_RAMO[cotizacion.ramo]}
            </span>
            <div>
              <strong>{ramoSeleccionado?.nombre ?? cotizacion.ramo}</strong>
              <small>Cotización {cotizacion.cotizacion_id}</small>
            </div>
            <span className="home-chip home-chip-verde">
              {cotizacion.estado === "VIGENTE" ? "Vigente" : cotizacion.estado}
            </span>
          </div>

          {cotizacion.cobertura_principal && (
            <div className="cotizar-detalle">
              <span>Cobertura principal</span>
              <strong>{cotizacion.cobertura_principal.nombre}</strong>
              {cotizacion.cobertura_principal.descripcion && (
                <small>{cotizacion.cobertura_principal.descripcion}</small>
              )}
            </div>
          )}

          <dl className="cotizar-resumen">
            {cotizacion.cobertura_principal && (
              <div>
                <dt>Suma asegurada</dt>
                <dd>
                  {formatearMonto(cotizacion.cobertura_principal.suma_asegurada, cotizacion.moneda)}
                </dd>
              </div>
            )}
            {cotizacion.vigente_hasta && (
              <div>
                <dt>Vigencia de la oferta</dt>
                <dd>Hasta el {formatearFecha(cotizacion.vigente_hasta)}</dd>
              </div>
            )}
            <div className="cotizar-resumen-total">
              <dt>Valor total de la prima</dt>
              <dd>
                {cotizacion.prima_total
                  ? formatearMonto(cotizacion.prima_total, cotizacion.moneda)
                  : "—"}
              </dd>
            </div>
          </dl>

          <div className="cotizar-acciones">
            <button type="button" className="cotizar-boton-secundario" onClick={reiniciar}>
              Cancelar
            </button>
            <button type="button" className="cotizar-boton-primario" onClick={irAPagar}>
              Aceptar y continuar
            </button>
          </div>
        </section>
      )}

      {/* Paso 4: pago de la prima (HU13) */}
      {paso === "pago" && cotizacion && (
        <section className="home-panel cotizar-resultado" aria-label="Pago de la prima">
          <div className="cotizar-resultado-encabezado">
            <span className="cotizar-ramo-icono material-symbols-outlined" aria-hidden="true">
              payments
            </span>
            <div>
              <strong>Pagar la prima</strong>
              <small>Cotización {cotizacion.cotizacion_id}</small>
            </div>
          </div>

          <dl className="cotizar-resumen">
            <div className="cotizar-resumen-total">
              <dt>Total a pagar</dt>
              <dd>
                {cotizacion.prima_total
                  ? formatearMonto(cotizacion.prima_total, cotizacion.moneda)
                  : "—"}
              </dd>
            </div>
          </dl>

          {errorPago && <p role="alert" className="home-aviso">{errorPago}</p>}

          <form onSubmit={procesarPago} className="cotizar-form">
            <fieldset className="cotizar-metodos" aria-label="Medio de pago">
              {METODOS_PAGO.map((opcion) => (
                <label
                  key={opcion.valor}
                  className={`cotizar-metodo ${metodoPago === opcion.valor ? "cotizar-metodo-activo" : ""}`}
                >
                  <input
                    type="radio"
                    name="metodo-pago"
                    value={opcion.valor}
                    checked={metodoPago === opcion.valor}
                    onChange={() => setMetodoPago(opcion.valor)}
                  />
                  <span className="material-symbols-outlined" aria-hidden="true">{opcion.icono}</span>
                  {opcion.etiqueta}
                </label>
              ))}
            </fieldset>

            {metodoPago === "TARJETA" ? (
              <>
                <div className="cotizar-campo cotizar-campo-ancho">
                  <label htmlFor="numero-tarjeta">Número de tarjeta</label>
                  <input
                    id="numero-tarjeta"
                    type="text"
                    inputMode="numeric"
                    value={numeroTarjeta}
                    required
                    autoComplete="cc-number"
                    placeholder="4111 1111 1111 1111"
                    onChange={(e) => setNumeroTarjeta(formatearNumeroTarjeta(e.target.value))}
                  />
                  <small className="cotizar-ayuda">
                    Los datos de la tarjeta se tokenizan y no se envían al servidor.
                  </small>
                </div>
                <div className="cotizar-campo">
                  <label htmlFor="vencimiento">Vencimiento (MM/AA)</label>
                  <input
                    id="vencimiento"
                    type="text"
                    inputMode="numeric"
                    value={vencimiento}
                    required
                    autoComplete="cc-exp"
                    placeholder="08/29"
                    onChange={(e) => setVencimiento(formatearVencimiento(e.target.value))}
                  />
                </div>
                <div className="cotizar-campo">
                  <label htmlFor="cvv">CVV</label>
                  <input
                    id="cvv"
                    type="text"
                    inputMode="numeric"
                    value={cvv}
                    required
                    autoComplete="cc-csc"
                    maxLength={4}
                    placeholder="123"
                    onChange={(e) => setCvv(e.target.value.replace(/\D/g, "").slice(0, 4))}
                  />
                </div>
              </>
            ) : (
              <div className="cotizar-campo cotizar-campo-ancho">
                <label htmlFor="codigo-banco">Banco</label>
                <select
                  id="codigo-banco"
                  value={codigoBanco}
                  required
                  onChange={(e) => setCodigoBanco(e.target.value)}
                >
                  <option value="">Selecciona tu banco</option>
                  {BANCOS_PSE.map((banco) => (
                    <option key={banco.codigo} value={banco.codigo}>{banco.nombre}</option>
                  ))}
                </select>
                <small className="cotizar-ayuda">
                  Serás llevado al portal de tu banco para confirmar el débito.
                </small>
              </div>
            )}

            <div className="cotizar-acciones">
              <button
                type="button"
                className="cotizar-boton-secundario"
                onClick={() => setPaso("resultado")}
                disabled={pagando}
              >
                Volver
              </button>
              <button type="submit" className="cotizar-boton-primario" disabled={pagando}>
                {pagando ? "Procesando…" : "Pagar prima"}
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Paso 5: confirmación del pago */}
      {paso === "confirmacion" && pago && (
        <section className="home-panel cotizar-resultado" aria-label="Confirmación del pago">
          <div className="cotizar-resultado-encabezado">
            <span
              className={`cotizar-ramo-icono material-symbols-outlined cotizar-pago-${pago.estado.toLowerCase()}`}
              aria-hidden="true"
            >
              {pago.estado === "APROBADO" ? "check_circle" : pago.estado === "PENDIENTE" ? "schedule" : "cancel"}
            </span>
            <div>
              <strong>
                {pago.estado === "APROBADO" && "Pago aprobado"}
                {pago.estado === "PENDIENTE" && "Pago pendiente"}
                {pago.estado === "RECHAZADO" && "Pago rechazado"}
              </strong>
              <small>Pago {pago.pago_id}</small>
            </div>
          </div>

          {pago.estado === "APROBADO" && (
            <p className="cotizar-mensaje-ok">
              Tu pago de {formatearMonto(pago.monto, pago.moneda)} fue aprobado. En un único flujo de
              compra, el siguiente paso es la firma del contrato y la emisión de tu póliza.
            </p>
          )}
          {pago.estado === "PENDIENTE" && (
            <p className="cotizar-mensaje-pendiente">
              Tu pago está pendiente de confirmación.
              {pago.url_redireccion && (
                <>
                  {" "}
                  <a href={pago.url_redireccion} target="_blank" rel="noreferrer">
                    Continúa en el portal de tu banco
                  </a>
                  .
                </>
              )}
            </p>
          )}
          {pago.estado === "RECHAZADO" && (
            <p className="cotizar-mensaje-error">
              Tu pago fue rechazado{pago.motivo_rechazo ? ` (${pago.motivo_rechazo})` : ""}. No se
              generó ninguna póliza. Puedes intentarlo de nuevo.
            </p>
          )}

          <div className="cotizar-acciones">
            {pago.estado === "RECHAZADO" ? (
              <>
                <button type="button" className="cotizar-boton-secundario" onClick={reiniciar}>
                  Cancelar
                </button>
                <button
                  type="button"
                  className="cotizar-boton-primario"
                  onClick={reintentarPago}
                  disabled={!cotizacion}
                >
                  Reintentar pago
                </button>
              </>
            ) : (
              <button
                type="button"
                className="cotizar-boton-primario"
                onClick={() => navigate("/home")}
              >
                Cerrar
              </button>
            )}
          </div>
        </section>
      )}
    </AppLayout>
  );
}

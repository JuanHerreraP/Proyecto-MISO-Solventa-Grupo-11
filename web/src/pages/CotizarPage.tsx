import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import {
  crearCotizacion,
  obtenerCotizacion,
  obtenerRamos,
} from "../services/cotizaciones.service";
import {
  crearPago,
  obtenerComprobante,
  obtenerPago,
  type Comprobante,
  type Pago,
} from "../services/pagos.service";
import type {
  CampoRiesgo,
  Cotizacion,
  DefinicionRamo,
  RamoSeguro,
} from "../types/cotizaciones";

import { t, localeActual } from "../i18n";

/** Icono de Material Symbols para cada ramo. */
const ICONO_RAMO: Record<RamoSeguro, string> = {
  VIAJE: "flight_takeoff",
  PROTECCION_DISPOSITIVOS: "devices",
  VIDA: "favorite",
  PARAMETRICO: "thunderstorm",
};

type Paso = "ramo" | "formulario" | "resultado" | "pago" | "confirmacion";

const METODOS_PAGO = [
  { valor: "TARJETA", get etiqueta() { return t("cotizarPage.tarjeta_de_credito_o_debito"); }, icono: "credit_card" },
  { valor: "PSE", get etiqueta() { return t("cotizarPage.pse_debito_bancario"); }, icono: "account_balance" },
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
  return Number(monto).toLocaleString(localeActual(), {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: 0,
  });
}

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleDateString(localeActual(), {
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
  const [comprobante, setComprobante] = useState<Comprobante | null>(null);

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
      () => setErrorCarga(t("cotizarPage.no_fue_posible_consultar_el")),
    );
  }, [searchParams, setSearchParams]);

  // Pagar una cotización que ya existe y quedó pendiente: /cotizar?cotizacion=ID (HU21).
  const cotizacionPendienteProcesada = useRef<string | null>(null);
  useEffect(() => {
    const cotizacionId = searchParams.get("cotizacion");
    if (!cotizacionId || cotizacionPendienteProcesada.current === cotizacionId) return;
    cotizacionPendienteProcesada.current = cotizacionId;
    setSearchParams({}, { replace: true });
    obtenerCotizacion(cotizacionId).then(
      (cot) => {
        const vigente =
          cot.estado === "VIGENTE" &&
          (!cot.vigente_hasta || new Date(cot.vigente_hasta) > new Date());
        if (!vigente) {
          setErrorCarga(t("cotizarPage.esta_cotizacion_ya_no_esta"));
          return;
        }
        setCotizacion(cot);
        setPago(null);
        setErrorPago("");
        setIdempotencyKey(crypto.randomUUID());
        setPaso("pago");
      },
      () => setErrorCarga(t("cotizarPage.no_fue_posible_consultar_la")),
    );
  }, [searchParams, setSearchParams]);

  // Con el pago aprobado se muestra su comprobante (HU21). Si no se puede consultar, se omite.
  useEffect(() => {
    if (pago?.estado !== "APROBADO") return;
    let activo = true;
    obtenerComprobante(pago.pago_id).then(
      (datos) => { if (activo) setComprobante(datos); },
      () => undefined,
    );
    return () => { activo = false; };
  }, [pago]);

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
      setErrorForm(t("cotizarPage.no_fue_posible_identificar_tu"));
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
          <h1>{t("cotizarPage.cotizar_un_nuevo_seguro")}</h1>
          <p>
            {paso === "ramo" && t("cotizarPage.elige_el_tipo_de_seguro")}
            {paso === "formulario" && t("cotizarPage.completa_los_datos_para_calcular")}
            {paso === "resultado" && t("cotizarPage.revisa_tu_cotizacion_antes_de")}
            {paso === "pago" && t("cotizarPage.elige_como_quieres_pagar_la")}
            {paso === "confirmacion" && t("cotizarPage.resultado_de_tu_pago")}
          </p>
        </div>
      </header>

      {errorCarga && <p role="alert" className="home-aviso">{errorCarga}</p>}

      {/* Paso 1: selección de ramo */}
      {paso === "ramo" && (
        <section aria-label={t("cotizarPage.tipos_de_seguro")} className="cotizar-ramos">
          {ramos === null && !errorCarga && (
            <p role="status" className="home-card-vacio">{t("cotizarPage.cargando_ramos_disponibles")}</p>
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
                  {t("cotizarPage.cotizar")}
                  <span className="material-symbols-outlined" aria-hidden="true">arrow_forward</span>
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Paso 2: formulario del ramo */}
      {paso === "formulario" && ramoSeleccionado && (
        <section className="home-panel cotizar-form-panel" aria-label={t("cotizarPage.datos_del_riesgo")}>
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
                  {!campo.requerido && <span className="cotizar-opcional"> · {t("cotizarPage.opcional")}</span>}
                </label>

                {campo.tipo === "OPCION" ? (
                  <select
                    id={campo.codigo}
                    value={valores[campo.codigo] ?? ""}
                    required={campo.requerido}
                    onChange={(e) => actualizarCampo(campo.codigo, e.target.value)}
                  >
                    <option value="">{t("cotizarPage.selecciona_una_opcion")}</option>
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
                    <option value="false">{t("cotizarPage.no")}</option>
                    <option value="true">{t("cotizarPage.si")}</option>
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
                {t("cotizarPage.volver")}
              </button>
              <button
                type="submit"
                className="cotizar-boton-primario"
                disabled={enviando || faltanRequeridos}
              >
                {enviando ? t("cotizarPage.calculando") : t("cotizarPage.continuar")}
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Paso 3: resultado de la cotización (HU23: aceptar o cancelar) */}
      {paso === "resultado" && cotizacion && (
        <section className="home-panel cotizar-resultado" aria-label={t("cotizarPage.resumen_de_la_cotizacion")}>
          <div className="cotizar-resultado-encabezado">
            <span className="cotizar-ramo-icono material-symbols-outlined" aria-hidden="true">
              {ICONO_RAMO[cotizacion.ramo]}
            </span>
            <div>
              <strong>{ramoSeleccionado?.nombre ?? cotizacion.ramo}</strong>
              <small>{t("cotizarPage.cotizacion_cotizacion_id", { cotizacion_id: cotizacion.cotizacion_id })}</small>
            </div>
            <span className="home-chip home-chip-verde">
              {cotizacion.estado === "VIGENTE" ? t("cotizarPage.vigente") : cotizacion.estado}
            </span>
          </div>

          {cotizacion.cobertura_principal && (
            <div className="cotizar-detalle">
              <span>{t("cotizarPage.cobertura_principal")}</span>
              <strong>{cotizacion.cobertura_principal.nombre}</strong>
              {cotizacion.cobertura_principal.descripcion && (
                <small>{cotizacion.cobertura_principal.descripcion}</small>
              )}
            </div>
          )}

          <dl className="cotizar-resumen">
            {cotizacion.cobertura_principal && (
              <div>
                <dt>{t("cotizarPage.suma_asegurada")}</dt>
                <dd>
                  {formatearMonto(cotizacion.cobertura_principal.suma_asegurada, cotizacion.moneda)}
                </dd>
              </div>
            )}
            {cotizacion.vigente_hasta && (
              <div>
                <dt>{t("cotizarPage.vigencia_de_la_oferta")}</dt>
                <dd>{t("cotizarPage.hasta_el_formatearfecha", { formatearFecha: formatearFecha(cotizacion.vigente_hasta) })}</dd>
              </div>
            )}
            <div className="cotizar-resumen-total">
              <dt>{t("cotizarPage.valor_total_de_la_prima")}</dt>
              <dd>
                {cotizacion.prima_total
                  ? formatearMonto(cotizacion.prima_total, cotizacion.moneda)
                  : "—"}
              </dd>
            </div>
          </dl>

          <div className="cotizar-acciones">
            <button type="button" className="cotizar-boton-secundario" onClick={reiniciar}>
              {t("cotizarPage.cancelar")}
            </button>
            <button type="button" className="cotizar-boton-primario" onClick={irAPagar}>
              {t("cotizarPage.aceptar_y_continuar")}
            </button>
          </div>
        </section>
      )}

      {/* Paso 4: pago de la prima (HU13) */}
      {paso === "pago" && cotizacion && (
        <section className="home-panel cotizar-resultado" aria-label={t("cotizarPage.pago_de_la_prima")}>
          <div className="cotizar-resultado-encabezado">
            <span className="cotizar-ramo-icono material-symbols-outlined" aria-hidden="true">
              payments
            </span>
            <div>
              <strong>{t("cotizarPage.pagar_la_prima")}</strong>
              <small>{t("cotizarPage.cotizacion_cotizacion_id", { cotizacion_id: cotizacion.cotizacion_id })}</small>
            </div>
          </div>

          <dl className="cotizar-resumen">
            <div className="cotizar-resumen-total">
              <dt>{t("cotizarPage.total_a_pagar")}</dt>
              <dd>
                {cotizacion.prima_total
                  ? formatearMonto(cotizacion.prima_total, cotizacion.moneda)
                  : "—"}
              </dd>
            </div>
          </dl>

          {errorPago && <p role="alert" className="home-aviso">{errorPago}</p>}

          <form onSubmit={procesarPago} className="cotizar-form">
            <fieldset className="cotizar-metodos" aria-label={t("cotizarPage.medio_de_pago")}>
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
                  <label htmlFor="numero-tarjeta">{t("cotizarPage.numero_de_tarjeta")}</label>
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
                    {t("cotizarPage.los_datos_de_la_tarjeta")}
                  </small>
                </div>
                <div className="cotizar-campo">
                  <label htmlFor="vencimiento">{t("cotizarPage.vencimiento_mm_aa")}</label>
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
                <label htmlFor="codigo-banco">{t("cotizarPage.banco")}</label>
                <select
                  id="codigo-banco"
                  value={codigoBanco}
                  required
                  onChange={(e) => setCodigoBanco(e.target.value)}
                >
                  <option value="">{t("cotizarPage.selecciona_tu_banco")}</option>
                  {BANCOS_PSE.map((banco) => (
                    <option key={banco.codigo} value={banco.codigo}>{banco.nombre}</option>
                  ))}
                </select>
                <small className="cotizar-ayuda">
                  {t("cotizarPage.seras_llevado_al_portal_de")}
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
                {t("cotizarPage.volver")}
              </button>
              <button type="submit" className="cotizar-boton-primario" disabled={pagando}>
                {pagando ? t("cotizarPage.procesando") : t("cotizarPage.pagar_prima")}
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Paso 5: confirmación del pago */}
      {paso === "confirmacion" && pago && (
        <section className="home-panel cotizar-resultado" aria-label={t("cotizarPage.confirmacion_del_pago")}>
          <div className="cotizar-resultado-encabezado">
            <span
              className={`cotizar-ramo-icono material-symbols-outlined cotizar-pago-${pago.estado.toLowerCase()}`}
              aria-hidden="true"
            >
              {pago.estado === "APROBADO" ? "check_circle" : pago.estado === "PENDIENTE" ? "schedule" : "cancel"}
            </span>
            <div>
              <strong>
                {pago.estado === "APROBADO" && t("cotizarPage.pago_aprobado")}
                {pago.estado === "PENDIENTE" && t("cotizarPage.pago_pendiente")}
                {pago.estado === "RECHAZADO" && t("cotizarPage.pago_rechazado")}
              </strong>
              <small>{t("cotizarPage.pago_pago_id", { pago_id: pago.pago_id })}</small>
            </div>
          </div>

          {pago.estado === "APROBADO" && (
            <p className="cotizar-mensaje-ok">
              {t("cotizarPage.tu_pago_de_formatearmonto_fue", { formatearMonto: formatearMonto(pago.monto, pago.moneda) })}{" "}
              {pago.concepto === "RENOVACION"
                ? t("cotizarPage.tu_poliza_fue_renovada")
                : t("cotizarPage.en_un_unico_flujo_de")}
            </p>
          )}
          {pago.estado === "APROBADO" && comprobante?.pago_id === pago.pago_id && (
            <dl className="cotizar-resumen" aria-label={t("cotizarPage.comprobante_de_pago")}>
              <div><dt>{t("cotizarPage.comprobante")}</dt><dd>{comprobante.numero}</dd></div>
              <div><dt>{t("cotizarPage.concepto")}</dt><dd>{comprobante.descripcion}</dd></div>
              <div>
                <dt>{t("cotizarPage.valor_pagado")}</dt>
                <dd>{formatearMonto(comprobante.monto, comprobante.moneda)}</dd>
              </div>
            </dl>
          )}
          {pago.estado === "PENDIENTE" && (
            <p className="cotizar-mensaje-pendiente">
              {t("cotizarPage.tu_pago_esta_pendiente_de")}
              {pago.url_redireccion && (
                <>
                  {" "}
                  <a href={pago.url_redireccion} target="_blank" rel="noreferrer">
                    {t("cotizarPage.continua_en_el_portal_de")}
                  </a>
                  .
                </>
              )}
            </p>
          )}
          {pago.estado === "RECHAZADO" && (
            <p className="cotizar-mensaje-error">
              {t("cotizarPage.tu_pago_fue_rechazado_valor", { valor: pago.motivo_rechazo ? ` (${pago.motivo_rechazo})` : "" })}
            </p>
          )}

          <div className="cotizar-acciones">
            {pago.estado === "RECHAZADO" ? (
              <>
                <button type="button" className="cotizar-boton-secundario" onClick={reiniciar}>
                  {t("cotizarPage.cancelar")}
                </button>
                <button
                  type="button"
                  className="cotizar-boton-primario"
                  onClick={reintentarPago}
                  disabled={!cotizacion}
                >
                  {t("cotizarPage.reintentar_pago")}
                </button>
              </>
            ) : pago.estado === "APROBADO" && pago.concepto === "RENOVACION" ? (
              <button
                type="button"
                className="cotizar-boton-primario"
                onClick={() => navigate("/polizas")}
              >
                {t("cotizarPage.ver_mis_polizas")}
              </button>
            ) : pago.estado === "APROBADO" ? (
              <button
                type="button"
                className="cotizar-boton-primario"
                onClick={() => navigate(`/firma/${encodeURIComponent(pago.cotizacion_id)}`)}
              >
                {t("cotizarPage.firmar_contrato")}
              </button>
            ) : (
              <button
                type="button"
                className="cotizar-boton-primario"
                onClick={() => navigate("/home")}
              >
                {t("cotizarPage.cerrar")}
              </button>
            )}
          </div>
        </section>
      )}
    </AppLayout>
  );
}

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import { obtenerBilletera, type PolizaResumen } from "../services/billetera.service";
import { crearSiniestro } from "../services/siniestros.service";
import {
  crearSiniestroAsistido,
  listarClientesDeAsesor,
  obtenerPolizasDeCliente,
  type ClienteDeAsesor,
} from "../services/asesor.service";
import type { Siniestro } from "../types/siniestros";

import { t, localeActual } from "../i18n";

const ICONO_RAMO: Record<string, string> = {
  VIAJE: "flight_takeoff",
  PROTECCION_DISPOSITIVOS: "devices",
  VIDA: "favorite",
  PARAMETRICO: "thunderstorm",
};

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString(localeActual(), {
    day: "numeric", month: "short", year: "numeric",
  });
}

const HOY = new Date().toISOString().slice(0, 10);

export default function ClaimRegistrationPage() {
  const navigate = useNavigate();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [polizas, setPolizas] = useState<PolizaResumen[] | null>(null);
  const [errorCarga, setErrorCarga] = useState("");

  // Solo para el asesor: lista de clientes atendidos y el cliente elegido.
  const [clientes, setClientes] = useState<ClienteDeAsesor[] | null>(null);
  const [clienteId, setClienteId] = useState("");

  const [polizaId, setPolizaId] = useState("");
  const [fechaEvento, setFechaEvento] = useState("");
  const [horaEvento, setHoraEvento] = useState("");
  const [lugar, setLugar] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [estimacion, setEstimacion] = useState("");

  const [enviando, setEnviando] = useState(false);
  const [errorEnvio, setErrorEnvio] = useState("");
  const [siniestro, setSiniestro] = useState<Siniestro | null>(null);

  const rol = perfil?.rol ?? null;
  const esAsesor = rol === "ASESOR_VENTAS";

  // Carga del perfil y, según el rol, de las pólizas del cliente o de la lista de clientes.
  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => {
        if (!activo) return;
        setPerfil(datos);
        if (datos.rol === "ASESOR_VENTAS") {
          listarClientesDeAsesor().then(
            (lista) => { if (activo) setClientes(lista); },
            (fallo: Error) => { if (activo) setErrorCarga(fallo.message); },
          );
        } else {
          obtenerBilletera().then(
            (billetera) => {
              if (activo) setPolizas(billetera.polizas.filter((p) => p.activa));
            },
            (fallo: Error) => { if (activo) setErrorCarga(fallo.message); },
          );
        }
      },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    return () => { activo = false; };
  }, [navigate]);

  // Cuando el asesor elige un cliente, se cargan las pólizas de ese cliente.
  useEffect(() => {
    if (!esAsesor || clienteId === "") return;
    let activo = true;
    obtenerPolizasDeCliente(clienteId).then(
      (billetera) => { if (activo) setPolizas(billetera.polizas.filter((p) => p.activa)); },
      (fallo: Error) => { if (activo) setErrorCarga(fallo.message); },
    );
    return () => { activo = false; };
  }, [esAsesor, clienteId]);

  const polizaSeleccionada = useMemo(
    () => polizas?.find((p) => p.poliza_id === polizaId) ?? null,
    [polizas, polizaId],
  );

  const descripcionValida = descripcion.trim().length >= 10;
  const estimacionValida = estimacion !== "" && Number(estimacion) >= 0;
  const clienteValido = !esAsesor || clienteId !== "";
  const puedeEnviar =
    clienteValido &&
    polizaId !== "" &&
    fechaEvento !== "" &&
    horaEvento !== "" &&
    lugar.trim() !== "" &&
    descripcionValida &&
    estimacionValida;

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!puedeEnviar) return;
    setEnviando(true);
    setErrorEnvio("");
    const base = {
      poliza_id: polizaId,
      fecha_evento: fechaEvento,
      hora_evento: horaEvento.length === 5 ? `${horaEvento}:00` : horaEvento,
      lugar: lugar.trim(),
      descripcion: descripcion.trim(),
      estimacion_danos: Number(estimacion),
    };
    try {
      const resultado = esAsesor
        ? await crearSiniestroAsistido({ ...base, cliente_id: clienteId })
        : await crearSiniestro(base);
      setSiniestro(resultado);
    } catch (fallo) {
      setErrorEnvio((fallo as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  // Confirmación tras el registro exitoso.
  if (siniestro) {
    return (
      <AppLayout activo="Siniestros" rol={rol}>
        <header className="home-header">
          <div>
            <h1>{t("claimRegistrationPage.siniestro_registrado")}</h1>
            <p>
              {esAsesor
                ? t("claimRegistrationPage.la_reclamacion_del_cliente_fue")
                : t("claimRegistrationPage.tu_reclamacion_fue_registrada_correctamente")}
            </p>
          </div>
        </header>
        <section className="home-panel cotizar-resultado" aria-label={t("claimRegistrationPage.confirmacion_del_siniestro")}>
          <div className="cotizar-resultado-encabezado">
            <span
              className="cotizar-ramo-icono material-symbols-outlined cotizar-pago-aprobado"
              aria-hidden="true"
            >
              check_circle
            </span>
            <div>
              <strong>{t("claimRegistrationPage.reclamacion_creada")}</strong>
              <small>{t("claimRegistrationPage.guarda_este_numero_para_hacer")}</small>
            </div>
          </div>
          <dl className="cotizar-resumen">
            <div>
              <dt>{t("claimRegistrationPage.numero_de_siniestro")}</dt>
              <dd>{siniestro.siniestro_id}</dd>
            </div>
            <div className="cotizar-resumen-total">
              <dt>{t("claimRegistrationPage.estado")}</dt>
              <dd>{t("claimRegistrationPage.registrado")}</dd>
            </div>
          </dl>
          <div className="cotizar-acciones">
            <button
              type="button"
              className="cotizar-boton-secundario"
              onClick={() => navigate("/home")}
            >
              {t("claimRegistrationPage.volver_al_inicio")}
            </button>
            <button
              type="button"
              className="cotizar-boton-primario"
              onClick={() => navigate("/siniestros")}
            >
              {t("claimRegistrationPage.ver_mis_siniestros")}
            </button>
          </div>
        </section>
      </AppLayout>
    );
  }

  return (
    <AppLayout activo="Siniestros" rol={rol}>
      <header className="home-header">
        <div>
          <h1>{esAsesor ? t("claimRegistrationPage.registrar_un_siniestro_asistido") : t("claimRegistrationPage.reportar_un_siniestro")}</h1>
          <p>
            {esAsesor
              ? t("claimRegistrationPage.selecciona_el_cliente_su_poliza")
              : t("claimRegistrationPage.selecciona_la_poliza_afectada_y")}
          </p>
        </div>
      </header>

      {errorCarga && <p role="alert" className="home-aviso">{errorCarga}</p>}

      <form onSubmit={enviar} className="home-panel cotizar-form-panel" aria-label={t("claimRegistrationPage.registro_de_siniestro")}>
        {/* Bloque 0: selección de cliente (solo asesor) */}
        {esAsesor && (
          <>
            <h2 className="cotizacion-subtitulo">{t("claimRegistrationPage.cliente")}</h2>
            {clientes === null && !errorCarga && (
              <p role="status" className="home-card-vacio">{t("claimRegistrationPage.cargando_tus_clientes")}</p>
            )}
            {clientes?.length === 0 && (
              <p className="home-card-vacio">
                {t("claimRegistrationPage.aun_no_tienes_clientes_asociados")}
              </p>
            )}
            {clientes && clientes.length > 0 && (
              <div className="cotizar-campo cotizar-campo-ancho">
                <label htmlFor="cliente">{t("claimRegistrationPage.cliente_que_atiendes")}</label>
                <select
                  id="cliente"
                  value={clienteId}
                  required
                  onChange={(e) => {
                    setClienteId(e.target.value);
                    setPolizas(null);
                    setPolizaId("");
                    setErrorCarga("");
                  }}
                >
                  <option value="">{t("claimRegistrationPage.selecciona_un_cliente")}</option>
                  {clientes.map((cliente) => (
                    <option key={cliente.cliente_id} value={cliente.cliente_id}>
                      {cliente.nombre} {cliente.apellido} · {cliente.email}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </>
        )}

        {/* Bloque 1: selección de póliza */}
        {(!esAsesor || clienteId !== "") && (
          <>
            <h2 className="cotizacion-subtitulo">{t("claimRegistrationPage.poliza_afectada")}</h2>
            {polizas === null && !errorCarga && (
              <p role="status" className="home-card-vacio">{t("claimRegistrationPage.cargando_polizas")}</p>
            )}
            {polizas?.length === 0 && (
              <p className="home-card-vacio">
                {esAsesor
                  ? t("claimRegistrationPage.el_cliente_no_tiene_polizas")
                  : t("claimRegistrationPage.no_tienes_polizas_vigentes_para")}
              </p>
            )}
            {polizas && polizas.length > 0 && (
              <div className="siniestro-polizas">
                {polizas.map((poliza) => (
                  <label
                    key={poliza.poliza_id}
                    className={`cotizar-metodo ${polizaId === poliza.poliza_id ? "cotizar-metodo-activo" : ""}`}
                  >
                    <input
                      type="radio"
                      name="poliza"
                      value={poliza.poliza_id}
                      checked={polizaId === poliza.poliza_id}
                      onChange={() => setPolizaId(poliza.poliza_id)}
                    />
                    <span className="material-symbols-outlined" aria-hidden="true">
                      {ICONO_RAMO[poliza.ramo] ?? "shield"}
                    </span>
                    <span className="siniestro-poliza-texto">
                      <strong>{poliza.nombre_ramo}</strong>
                      <small>{poliza.numero_poliza}</small>
                      <small>{t("claimRegistrationPage.cobertura_cobertura_principal", { cobertura_principal: poliza.cobertura_principal })}</small>
                      <small>{t("claimRegistrationPage.vigente_hasta_formatearfecha", { formatearFecha: formatearFecha(poliza.fecha_fin) })}</small>
                    </span>
                  </label>
                ))}
              </div>
            )}
          </>
        )}

        {/* Bloque 2: datos del evento */}
        <h2 className="cotizacion-subtitulo">{t("claimRegistrationPage.datos_del_evento")}</h2>
        {polizaSeleccionada && (
          <div className="cotizar-detalle" aria-label={t("claimRegistrationPage.poliza_seleccionada")}>
            <span>{t("claimRegistrationPage.poliza_seleccionada")}</span>
            <strong>{polizaSeleccionada.nombre_ramo}</strong>
            <small>{polizaSeleccionada.numero_poliza}</small>
          </div>
        )}
        <div className="cotizar-form">
          <div className="cotizar-campo">
            <label htmlFor="fecha-evento">{t("claimRegistrationPage.fecha_del_evento")}</label>
            <input
              id="fecha-evento"
              type="date"
              max={HOY}
              value={fechaEvento}
              required
              onChange={(e) => setFechaEvento(e.target.value)}
            />
          </div>
          <div className="cotizar-campo">
            <label htmlFor="hora-evento">{t("claimRegistrationPage.hora_del_evento")}</label>
            <input
              id="hora-evento"
              type="time"
              value={horaEvento}
              required
              onChange={(e) => setHoraEvento(e.target.value)}
            />
          </div>
          <div className="cotizar-campo cotizar-campo-ancho">
            <label htmlFor="lugar">{t("claimRegistrationPage.lugar")}</label>
            <input
              id="lugar"
              type="text"
              value={lugar}
              required
              placeholder={t("claimRegistrationPage.ej_aeropuerto_internacional_el_dorado")}
              onChange={(e) => setLugar(e.target.value)}
            />
          </div>
          <div className="cotizar-campo cotizar-campo-ancho">
            <label htmlFor="descripcion">{t("claimRegistrationPage.descripcion_detallada")}</label>
            <textarea
              id="descripcion"
              value={descripcion}
              required
              minLength={10}
              maxLength={2000}
              rows={4}
              placeholder={t("claimRegistrationPage.describe_lo_ocurrido_con_el")}
              onChange={(e) => setDescripcion(e.target.value)}
            />
            <small className="cotizar-ayuda">
              {t("claimRegistrationPage.minimo_10_caracteres_length_2000", { length: descripcion.trim().length })}
            </small>
          </div>
          <div className="cotizar-campo cotizar-campo-ancho">
            <label htmlFor="estimacion">{t("claimRegistrationPage.estimacion_preliminar_de_danos_cop")}</label>
            <input
              id="estimacion"
              type="number"
              inputMode="numeric"
              min={0}
              step="1"
              value={estimacion}
              required
              placeholder="0"
              onChange={(e) => setEstimacion(e.target.value)}
            />
            <small className="cotizar-ayuda">
              {t("claimRegistrationPage.valor_informativo_no_representa_el")}
            </small>
          </div>
        </div>

        {errorEnvio && <p role="alert" className="home-aviso">{errorEnvio}</p>}

        <div className="cotizar-acciones">
          <button type="button" className="cotizar-boton-secundario" onClick={() => navigate("/home")}>
            {t("claimRegistrationPage.cancelar")}
          </button>
          <button type="submit" className="cotizar-boton-primario" disabled={enviando || !puedeEnviar}>
            {enviando ? t("claimRegistrationPage.registrando") : t("claimRegistrationPage.registrar_siniestro")}
          </button>
        </div>
      </form>
    </AppLayout>
  );
}

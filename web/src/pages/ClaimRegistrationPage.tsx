import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import { obtenerBilletera, type PolizaResumen } from "../services/billetera.service";
import { crearSiniestro } from "../services/siniestros.service";
import type { Siniestro } from "../types/siniestros";

const ICONO_RAMO: Record<string, string> = {
  VIAJE: "flight_takeoff",
  PROTECCION_DISPOSITIVOS: "devices",
  VIDA: "favorite",
  PARAMETRICO: "thunderstorm",
};

function formatearFecha(iso: string): string {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString("es-CO", {
    day: "numeric", month: "short", year: "numeric",
  });
}

const HOY = new Date().toISOString().slice(0, 10);

export default function ClaimRegistrationPage() {
  const navigate = useNavigate();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [polizas, setPolizas] = useState<PolizaResumen[] | null>(null);
  const [errorCarga, setErrorCarga] = useState("");

  const [polizaId, setPolizaId] = useState("");
  const [fechaEvento, setFechaEvento] = useState("");
  const [horaEvento, setHoraEvento] = useState("");
  const [lugar, setLugar] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [estimacion, setEstimacion] = useState("");

  const [enviando, setEnviando] = useState(false);
  const [errorEnvio, setErrorEnvio] = useState("");
  const [siniestro, setSiniestro] = useState<Siniestro | null>(null);

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => { if (activo) setPerfil(datos); },
      () => { if (activo) navigate("/login", { replace: true }); },
    );
    obtenerBilletera().then(
      (billetera) => {
        if (activo) setPolizas(billetera.polizas.filter((p) => p.activa));
      },
      (fallo: Error) => { if (activo) setErrorCarga(fallo.message); },
    );
    return () => { activo = false; };
  }, [navigate]);

  const rol = perfil?.rol ?? null;
  const polizaSeleccionada = useMemo(
    () => polizas?.find((p) => p.poliza_id === polizaId) ?? null,
    [polizas, polizaId],
  );

  const descripcionValida = descripcion.trim().length >= 10;
  const estimacionValida = estimacion !== "" && Number(estimacion) >= 0;
  const puedeEnviar =
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
    try {
      const resultado = await crearSiniestro({
        poliza_id: polizaId,
        fecha_evento: fechaEvento,
        hora_evento: horaEvento.length === 5 ? `${horaEvento}:00` : horaEvento,
        lugar: lugar.trim(),
        descripcion: descripcion.trim(),
        estimacion_danos: Number(estimacion),
      });
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
            <h1>Siniestro registrado</h1>
            <p>Tu reclamación fue registrada correctamente.</p>
          </div>
        </header>
        <section className="home-panel cotizar-resultado" aria-label="Confirmación del siniestro">
          <div className="cotizar-resultado-encabezado">
            <span
              className="cotizar-ramo-icono material-symbols-outlined cotizar-pago-aprobado"
              aria-hidden="true"
            >
              check_circle
            </span>
            <div>
              <strong>Reclamación creada</strong>
              <small>Guarda este número para hacer seguimiento.</small>
            </div>
          </div>
          <dl className="cotizar-resumen">
            <div>
              <dt>Número de siniestro</dt>
              <dd>{siniestro.siniestro_id}</dd>
            </div>
            <div className="cotizar-resumen-total">
              <dt>Estado</dt>
              <dd>Registrado</dd>
            </div>
          </dl>
          <div className="cotizar-acciones">
            <button
              type="button"
              className="cotizar-boton-secundario"
              onClick={() => navigate("/home")}
            >
              Volver al inicio
            </button>
            <button
              type="button"
              className="cotizar-boton-primario"
              onClick={() => navigate("/siniestros")}
            >
              Ver mis siniestros
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
          <h1>Reportar un siniestro</h1>
          <p>Selecciona la póliza afectada y describe lo ocurrido.</p>
        </div>
      </header>

      {errorCarga && <p role="alert" className="home-aviso">{errorCarga}</p>}

      <form onSubmit={enviar} className="home-panel cotizar-form-panel" aria-label="Registro de siniestro">
        {/* Bloque 1: selección de póliza */}
        <h2 className="cotizacion-subtitulo">Póliza afectada</h2>
        {polizas === null && !errorCarga && (
          <p role="status" className="home-card-vacio">Cargando tus pólizas…</p>
        )}
        {polizas?.length === 0 && (
          <p className="home-card-vacio">No tienes pólizas vigentes para reportar un siniestro.</p>
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
                  <small>Cobertura: {poliza.cobertura_principal}</small>
                  <small>Vigente hasta {formatearFecha(poliza.fecha_fin)}</small>
                </span>
              </label>
            ))}
          </div>
        )}

        {/* Bloque 2: datos del evento */}
        <h2 className="cotizacion-subtitulo">Datos del evento</h2>
        {polizaSeleccionada && (
          <div className="cotizar-detalle" aria-label="Póliza seleccionada">
            <span>Póliza seleccionada</span>
            <strong>{polizaSeleccionada.nombre_ramo}</strong>
            <small>{polizaSeleccionada.numero_poliza}</small>
          </div>
        )}
        <div className="cotizar-form">
          <div className="cotizar-campo">
            <label htmlFor="fecha-evento">Fecha del evento</label>
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
            <label htmlFor="hora-evento">Hora del evento</label>
            <input
              id="hora-evento"
              type="time"
              value={horaEvento}
              required
              onChange={(e) => setHoraEvento(e.target.value)}
            />
          </div>
          <div className="cotizar-campo cotizar-campo-ancho">
            <label htmlFor="lugar">Lugar</label>
            <input
              id="lugar"
              type="text"
              value={lugar}
              required
              placeholder="Ej. Aeropuerto Internacional El Dorado"
              onChange={(e) => setLugar(e.target.value)}
            />
          </div>
          <div className="cotizar-campo cotizar-campo-ancho">
            <label htmlFor="descripcion">Descripción detallada</label>
            <textarea
              id="descripcion"
              value={descripcion}
              required
              minLength={10}
              maxLength={2000}
              rows={4}
              placeholder="Describe lo ocurrido con el mayor detalle posible."
              onChange={(e) => setDescripcion(e.target.value)}
            />
            <small className="cotizar-ayuda">
              Mínimo 10 caracteres ({descripcion.trim().length}/2000).
            </small>
          </div>
          <div className="cotizar-campo cotizar-campo-ancho">
            <label htmlFor="estimacion">Estimación preliminar de daños (COP)</label>
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
              Valor informativo; no representa el monto definitivo de indemnización.
            </small>
          </div>
        </div>

        {errorEnvio && <p role="alert" className="home-aviso">{errorEnvio}</p>}

        <div className="cotizar-acciones">
          <button type="button" className="cotizar-boton-secundario" onClick={() => navigate("/home")}>
            Cancelar
          </button>
          <button type="submit" className="cotizar-boton-primario" disabled={enviando || !puedeEnviar}>
            {enviando ? "Registrando…" : "Registrar siniestro"}
          </button>
        </div>
      </form>
    </AppLayout>
  );
}

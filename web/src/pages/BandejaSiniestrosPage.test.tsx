import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import {
  aprobarSiniestro,
  ErrorDesembolso,
  obtenerBandeja,
  rechazarSiniestro,
  reintentarDesembolso,
  type SiniestroBandeja,
} from "../services/desembolsos.service";
import BandejaSiniestrosPage from "./BandejaSiniestrosPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));
vi.mock("../services/desembolsos.service", async (original) => ({
  ...(await original<typeof import("../services/desembolsos.service")>()),
  obtenerBandeja: vi.fn(),
  aprobarSiniestro: vi.fn(),
  rechazarSiniestro: vi.fn(),
  reintentarDesembolso: vi.fn(),
}));

const SINIESTRO: SiniestroBandeja = {
  siniestro_id: "SIN-1",
  poliza_id: "POL-1",
  cliente_id: "CLI-1",
  origen: "MANUAL",
  estado: "REGISTRADO",
  fecha_evento: "2026-10-20",
  lugar: "Aeropuerto El Dorado",
  descripcion: "El vuelo fue cancelado y hubo gastos adicionales.",
  estimacion_danos: "850000.00",
  moneda: "COP",
  registrado_en: "2026-10-20T23:00:00Z",
  monto_aprobado: null,
  evaluado_por: null,
  evaluado_en: null,
  motivo_rechazo: null,
  desembolso: null,
};

const APROBADO: SiniestroBandeja = {
  ...SINIESTRO,
  estado: "APROBADO",
  monto_aprobado: "850000.00",
  evaluado_por: "OPE-1",
  desembolso: {
    desembolso_id: "DES-1", siniestro_id: "SIN-1", poliza_id: "POL-1", monto: "850000.00",
    moneda: "COP", medio: "CUENTA_BANCARIA", destino: "Bancolombia ahorros ****5678",
    estado: "PENDIENTE", intento: 1, referencia_transaccion: null, codigo_retiro: null,
    motivo_fallo: "RED_NO_DISPONIBLE", creado_en: "2026-10-21T15:00:00Z", completado_en: null,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "OPE-1", rol: "OPERACIONES_SINIESTROS" });
  vi.mocked(obtenerBandeja).mockResolvedValue([SINIESTRO]);
});

function montar() {
  render(
    <MemoryRouter initialEntries={["/operaciones/siniestros"]}>
      <Routes>
        <Route path="/operaciones/siniestros" element={<BandejaSiniestrosPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

it("arranca mostrando los siniestros por evaluar", async () => {
  montar();

  expect(await screen.findByText(/Aeropuerto El Dorado/)).toBeInTheDocument();
  expect(obtenerBandeja).toHaveBeenCalledWith("REGISTRADO");
  expect(screen.getByRole("button", { name: "Por evaluar" })).toHaveAttribute("aria-pressed", "true");
});

it("aprueba con el monto propuesto y recarga la bandeja", async () => {
  vi.mocked(aprobarSiniestro).mockResolvedValue(APROBADO);
  const usuario = userEvent.setup();
  montar();

  await usuario.click(await screen.findByRole("button", { name: /Aeropuerto El Dorado/ }));
  expect(screen.getByLabelText("Monto a indemnizar")).toHaveValue(850000);
  await usuario.click(screen.getByRole("button", { name: "Aprobar y desembolsar" }));

  expect(aprobarSiniestro).toHaveBeenCalledWith("SIN-1", "850000");
  expect(await screen.findByText("Siniestro aprobado. Se ordenó el desembolso.")).toBeInTheDocument();
  expect(obtenerBandeja).toHaveBeenCalledTimes(2);
});

it("el rechazo exige un motivo", async () => {
  vi.mocked(rechazarSiniestro).mockResolvedValue({ ...SINIESTRO, estado: "RECHAZADO" });
  const usuario = userEvent.setup();
  montar();

  await usuario.click(await screen.findByRole("button", { name: /Aeropuerto El Dorado/ }));
  const rechazar = screen.getByRole("button", { name: "Rechazar siniestro" });
  expect(rechazar).toBeDisabled();
  await usuario.type(screen.getByLabelText("Motivo"), "Evento no cubierto");
  await usuario.click(rechazar);

  expect(rechazarSiniestro).toHaveBeenCalledWith("SIN-1", "Evento no cubierto");
});

it("muestra el error del servidor al aprobar", async () => {
  vi.mocked(aprobarSiniestro).mockRejectedValue(
    new ErrorDesembolso("El monto supera la suma asegurada.", "MONTO_INVALIDO", 422),
  );
  const usuario = userEvent.setup();
  montar();

  await usuario.click(await screen.findByRole("button", { name: /Aeropuerto El Dorado/ }));
  await usuario.click(screen.getByRole("button", { name: "Aprobar y desembolsar" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("El monto supera la suma asegurada.");
});

it("un desembolso pendiente ofrece reintentar", async () => {
  vi.mocked(obtenerBandeja).mockResolvedValue([APROBADO]);
  vi.mocked(reintentarDesembolso).mockResolvedValue({ ...APROBADO.desembolso!, estado: "COMPLETADA" });
  const usuario = userEvent.setup();
  montar();

  await usuario.click(await screen.findByRole("button", { name: "Aprobados" }));
  await usuario.click(await screen.findByRole("button", { name: /Aeropuerto El Dorado/ }));

  expect(screen.getByText("Pendiente")).toBeInTheDocument();
  expect(screen.getByText("La red de pagos no respondió; se reintentará.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Aprobar y desembolsar" })).not.toBeInTheDocument();
  await usuario.click(screen.getByRole("button", { name: "Reintentar desembolso" }));

  expect(reintentarDesembolso).toHaveBeenCalledWith("SIN-1");
  expect(obtenerBandeja).toHaveBeenLastCalledWith("APROBADO");
});

it("indica cuando no hay siniestros", async () => {
  vi.mocked(obtenerBandeja).mockResolvedValue([]);
  montar();

  expect(await screen.findByText("No hay siniestros en esta vista.")).toBeInTheDocument();
});

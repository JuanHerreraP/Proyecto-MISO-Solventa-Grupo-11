import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import { obtenerBilletera, type PolizaResumen } from "../services/billetera.service";
import { crearSiniestro } from "../services/siniestros.service";
import type { Siniestro } from "../types/siniestros";
import ClaimRegistrationPage from "./ClaimRegistrationPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/billetera.service", () => ({ obtenerBilletera: vi.fn() }));
vi.mock("../services/siniestros.service", () => ({ crearSiniestro: vi.fn() }));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));

const VIGENTE: PolizaResumen = {
  poliza_id: "POL-1", numero_poliza: "SOL-VJ-0001", ramo: "VIAJE",
  nombre_ramo: "Seguro de viaje", estado: "VIGENTE", activa: true,
  fecha_inicio: "2026-10-01", fecha_fin: "2026-11-30", cobertura_principal: "Asistencia",
};
const INACTIVA: PolizaResumen = {
  poliza_id: "POL-2", numero_poliza: "SOL-VD-0002", ramo: "VIDA",
  nombre_ramo: "Seguro de vida", estado: "VENCIDA", activa: false,
  fecha_inicio: "2024-01-01", fecha_fin: "2024-12-31", cobertura_principal: "Vida",
};

const SINIESTRO: Siniestro = {
  siniestro_id: "SIN-abc123", cliente_id: "CLI-1", poliza_id: "POL-1",
  origen: "MANUAL", estado: "REGISTRADO", fecha_evento: "2026-10-20",
  hora_evento: "18:30:00", lugar: "El Dorado", descripcion: "Vuelo cancelado por clima.",
  estimacion_danos: "850000.00", moneda: "COP", registrado_por: "CLI-1",
  registrado_en: "2026-10-24T23:30:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "CLI-1", rol: "CLIENTE" });
  vi.mocked(obtenerBilletera).mockResolvedValue({
    polizas: [VIGENTE, INACTIVA], total_vigentes: 1, total_inactivas: 1,
  });
});

function montar() {
  render(
    <MemoryRouter initialEntries={["/siniestros/nuevo"]}>
      <Routes>
        <Route path="/siniestros/nuevo" element={<ClaimRegistrationPage />} />
        <Route path="/home" element={<h1>Inicio</h1>} />
        <Route path="/login" element={<h1>Inicia sesión</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

async function llenarFormulario() {
  await userEvent.click(await screen.findByRole("radio", { name: /Seguro de viaje/ }));
  await userEvent.type(screen.getByLabelText("Fecha del evento"), "2026-10-20");
  await userEvent.type(screen.getByLabelText("Hora del evento"), "18:30");
  await userEvent.type(screen.getByLabelText("Lugar"), "El Dorado");
  await userEvent.type(
    screen.getByLabelText("Descripción detallada"),
    "El vuelo fue cancelado por mal clima.",
  );
  await userEvent.type(
    screen.getByLabelText("Estimación preliminar de daños (COP)"),
    "850000",
  );
}

it("renderiza el formulario y los bloques principales", async () => {
  montar();
  expect(await screen.findByText("Póliza afectada")).toBeInTheDocument();
  expect(screen.getByText("Datos del evento")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Registrar siniestro" })).toBeInTheDocument();
});

it("carga solo las pólizas activas y oculta las inactivas", async () => {
  montar();
  expect(await screen.findByRole("radio", { name: /Seguro de viaje/ })).toBeInTheDocument();
  expect(screen.queryByText("Seguro de vida")).not.toBeInTheDocument();
});

it("mantiene deshabilitado el envío hasta completar los campos obligatorios", async () => {
  montar();
  await screen.findByText("Póliza afectada");
  expect(screen.getByRole("button", { name: "Registrar siniestro" })).toBeDisabled();
});

it("envía el request y muestra el estado de carga y la confirmación", async () => {
  let resolver: (s: Siniestro) => void = () => {};
  vi.mocked(crearSiniestro).mockReturnValue(
    new Promise<Siniestro>((r) => { resolver = r; }),
  );
  montar();
  await llenarFormulario();
  await userEvent.click(screen.getByRole("button", { name: "Registrar siniestro" }));

  expect(await screen.findByRole("button", { name: "Registrando…" })).toBeInTheDocument();
  expect(crearSiniestro).toHaveBeenCalledWith(
    expect.objectContaining({ poliza_id: "POL-1", hora_evento: "18:30:00", estimacion_danos: 850000 }),
  );

  resolver(SINIESTRO);
  expect(await screen.findByText("Siniestro registrado")).toBeInTheDocument();
  expect(screen.getByText("SIN-abc123")).toBeInTheDocument();
  expect(screen.getByText("Registrado")).toBeInTheDocument();
});

it("muestra el error del backend", async () => {
  vi.mocked(crearSiniestro).mockRejectedValue(
    new Error("La póliza no está vigente; no es posible registrar el siniestro."),
  );
  montar();
  await llenarFormulario();
  await userEvent.click(screen.getByRole("button", { name: "Registrar siniestro" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("La póliza no está vigente");
});

it("permite volver al inicio tras el registro", async () => {
  vi.mocked(crearSiniestro).mockResolvedValue(SINIESTRO);
  montar();
  await llenarFormulario();
  await userEvent.click(screen.getByRole("button", { name: "Registrar siniestro" }));
  await userEvent.click(await screen.findByRole("button", { name: "Volver al inicio" }));
  await waitFor(() =>
    expect(screen.getByRole("heading", { name: "Inicio" })).toBeInTheDocument(),
  );
});

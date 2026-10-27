import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import { obtenerBilletera, type PolizaResumen } from "../services/billetera.service";
import { listarSiniestros } from "../services/siniestros.service";
import type { Siniestro } from "../types/siniestros";
import SiniestrosPage from "./SiniestrosPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/billetera.service", () => ({ obtenerBilletera: vi.fn() }));
vi.mock("../services/siniestros.service", () => ({ listarSiniestros: vi.fn() }));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));

const POLIZA: PolizaResumen = {
  poliza_id: "POL-1", numero_poliza: "SOL-VJ-0001", ramo: "VIAJE",
  nombre_ramo: "Seguro de viaje", estado: "VIGENTE", activa: true,
  fecha_inicio: "2026-10-01", fecha_fin: "2026-11-30", cobertura_principal: "Asistencia",
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
    polizas: [POLIZA], total_vigentes: 1, total_inactivas: 0,
  });
});

function montar() {
  render(
    <MemoryRouter initialEntries={["/siniestros"]}>
      <Routes>
        <Route path="/siniestros" element={<SiniestrosPage />} />
        <Route path="/siniestros/nuevo" element={<h1>Nuevo siniestro</h1>} />
        <Route path="/login" element={<h1>Inicia sesión</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

it("lista los siniestros del cliente con la póliza asociada", async () => {
  vi.mocked(listarSiniestros).mockResolvedValue([SINIESTRO]);
  montar();
  expect(await screen.findByText("Seguro de viaje")).toBeInTheDocument();
  expect(screen.getByText("Registrado")).toBeInTheDocument();
});

it("despliega el detalle del siniestro al hacer clic", async () => {
  vi.mocked(listarSiniestros).mockResolvedValue([SINIESTRO]);
  montar();
  await userEvent.click(await screen.findByRole("button", { name: /Seguro de viaje/ }));

  expect(await screen.findByText("Vuelo cancelado por clima.")).toBeInTheDocument();
  expect(screen.getByText("SIN-abc123")).toBeInTheDocument();
  expect(screen.getByText("El Dorado")).toBeInTheDocument();
});

it("indica cuando no hay siniestros", async () => {
  vi.mocked(listarSiniestros).mockResolvedValue([]);
  montar();
  expect(await screen.findByText("Aún no tienes siniestros registrados.")).toBeInTheDocument();
});

it("informa el error si no puede consultar", async () => {
  vi.mocked(listarSiniestros).mockRejectedValue(
    new Error("No fue posible consultar tus siniestros."),
  );
  montar();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "No fue posible consultar tus siniestros.",
  );
});

it("permite ir a reportar un nuevo siniestro", async () => {
  vi.mocked(listarSiniestros).mockResolvedValue([]);
  montar();
  await userEvent.click(await screen.findByRole("button", { name: "Reportar siniestro" }));
  expect(await screen.findByRole("heading", { name: "Nuevo siniestro" })).toBeInTheDocument();
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import { obtenerBilletera, type PolizaResumen } from "../services/billetera.service";
import { listarDesembolsos, obtenerCuenta, type Desembolso } from "../services/desembolsos.service";
import { listarSiniestros } from "../services/siniestros.service";
import type { Siniestro } from "../types/siniestros";
import SiniestrosPage from "./SiniestrosPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/billetera.service", () => ({ obtenerBilletera: vi.fn() }));
vi.mock("../services/siniestros.service", () => ({ listarSiniestros: vi.fn() }));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));
vi.mock("../services/desembolsos.service", async (original) => ({
  ...(await original<typeof import("../services/desembolsos.service")>()),
  listarDesembolsos: vi.fn(),
  obtenerCuenta: vi.fn(),
}));

const POLIZA: PolizaResumen = {
  poliza_id: "POL-1", numero_poliza: "SOL-VJ-0001", ramo: "VIAJE",
  nombre_ramo: "Seguro de viaje", estado: "VIGENTE", activa: true,
  fecha_inicio: "2026-10-01", fecha_fin: "2026-11-30", cobertura_principal: "Asistencia",
  emitida_en: "2026-10-01T12:00:00Z",
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
  vi.mocked(listarDesembolsos).mockResolvedValue([]);
  vi.mocked(obtenerCuenta).mockResolvedValue(null);
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

const DESEMBOLSO: Desembolso = {
  desembolso_id: "DES-1", siniestro_id: "SIN-abc123", poliza_id: "POL-1", monto: "850000.00",
  moneda: "COP", medio: "CODIGO_RETIRO", destino: "Código de retiro", estado: "COMPLETADA",
  intento: 1, referencia_transaccion: "RET-ABC123", codigo_retiro: "48213907",
  motivo_fallo: null, creado_en: "2026-10-25T15:00:00Z", completado_en: "2026-10-25T15:00:00Z",
};

it("muestra la indemnización aprobada con su código de retiro", async () => {
  vi.mocked(listarSiniestros).mockResolvedValue([
    { ...SINIESTRO, estado: "APROBADO", monto_aprobado: "850000.00" },
  ]);
  vi.mocked(listarDesembolsos).mockResolvedValue([DESEMBOLSO]);
  montar();
  await userEvent.click(await screen.findByRole("button", { name: /Seguro de viaje/ }));

  expect(screen.getByText("Completada")).toBeInTheDocument();
  expect(screen.getByLabelText("Código de retiro")).toHaveTextContent("48213907");
  expect(screen.getByText(/Transacción RET-ABC123/)).toBeInTheDocument();
});

it("muestra el motivo de un siniestro rechazado", async () => {
  vi.mocked(listarSiniestros).mockResolvedValue([
    { ...SINIESTRO, estado: "RECHAZADO", motivo_rechazo: "El evento no está cubierto." },
  ]);
  montar();
  await userEvent.click(await screen.findByRole("button", { name: /Seguro de viaje/ }));

  expect(screen.getByText("El evento no está cubierto.")).toBeInTheDocument();
});

it("ofrece registrar la cuenta para recibir indemnizaciones", async () => {
  vi.mocked(listarSiniestros).mockResolvedValue([]);
  montar();

  expect(await screen.findByRole("heading", { name: "Cuenta para recibir indemnizaciones" }))
    .toBeInTheDocument();
});

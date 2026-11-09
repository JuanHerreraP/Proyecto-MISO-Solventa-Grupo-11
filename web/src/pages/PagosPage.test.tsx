import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import { listarPagos } from "../services/pagos.service";
import PagosPage from "./PagosPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/pagos.service", () => ({ listarPagos: vi.fn() }));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ rol: "CLIENTE" });
});

function pagos() {
  render(<MemoryRouter initialEntries={["/pagos"]}><Routes>
    <Route path="/pagos" element={<PagosPage />} />
    <Route path="/home" element={<h1>Inicio</h1>} />
    <Route path="/login" element={<h1>Inicia sesión</h1>} />
  </Routes></MemoryRouter>);
}

it("muestra el historial de pagos del cliente", async () => {
  vi.mocked(listarPagos).mockResolvedValue([
    {
      pago_id: "p1", cotizacion_id: "COT-001", metodo: "TARJETA", monto: "94500.00", moneda: "COP",
      estado: "APROBADO", motivo_rechazo: null, creado_en: "2026-09-17T15:00:00Z",
    },
    {
      pago_id: "p2", cotizacion_id: "COT-002", metodo: "PSE", monto: "91200.00", moneda: "COP",
      estado: "RECHAZADO", motivo_rechazo: "FONDOS_INSUFICIENTES", creado_en: "2026-08-17T15:00:00Z",
    },
  ]);
  pagos();
  expect(await screen.findByText("Prima — cotización COT-001")).toBeInTheDocument();
  expect(screen.getByText("Pagado")).toBeInTheDocument();
  expect(screen.getByText("Rechazado")).toBeInTheDocument();
  expect(screen.getByText("Tarjeta")).toBeInTheDocument();
  expect(screen.getByText("PSE")).toBeInTheDocument();
});

it("indica cuando todavía no hay pagos", async () => {
  vi.mocked(listarPagos).mockResolvedValue([]);
  pagos();
  expect(await screen.findByText("Todavía no tienes pagos.")).toBeInTheDocument();
});

it("informa el error si no puede consultar los pagos", async () => {
  vi.mocked(listarPagos).mockRejectedValue(new Error("No fue posible consultar tus pagos."));
  pagos();
  expect(await screen.findByRole("alert")).toHaveTextContent("No fue posible consultar tus pagos.");
});

it("vuelve a Inicio desde la barra lateral", async () => {
  vi.mocked(listarPagos).mockResolvedValue([]);
  pagos();
  await userEvent.click(await screen.findByRole("button", { name: /Inicio/ }));
  expect(await screen.findByRole("heading", { name: "Inicio" })).toBeInTheDocument();
});

it("abre el contrato para firmar desde un pago aprobado", async () => {
  vi.mocked(listarPagos).mockResolvedValue([
    {
      pago_id: "p1", cotizacion_id: "COT-001", metodo: "TARJETA", monto: "94500.00", moneda: "COP",
      estado: "APROBADO", motivo_rechazo: null, creado_en: "2026-09-17T15:00:00Z",
    },
    {
      pago_id: "p2", cotizacion_id: "COT-002", metodo: "PSE", monto: "91200.00", moneda: "COP",
      estado: "PENDIENTE", motivo_rechazo: null, creado_en: "2026-08-17T15:00:00Z",
    },
  ]);
  render(<MemoryRouter initialEntries={["/pagos"]}><Routes>
    <Route path="/pagos" element={<PagosPage />} />
    <Route path="/firma/:cotizacionId" element={<h1>Firma</h1>} />
  </Routes></MemoryRouter>);

  const enlaces = await screen.findAllByRole("button", { name: "Contrato" });
  expect(enlaces).toHaveLength(1);
  await userEvent.click(enlaces[0]);
  expect(await screen.findByRole("heading", { name: "Firma" })).toBeInTheDocument();
});

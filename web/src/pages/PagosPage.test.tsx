import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import {
  listarPagos,
  listarPrimasPendientes,
  obtenerComprobante,
  type PagoResumen,
  type PrimaPendiente,
} from "../services/pagos.service";
import PagosPage from "./PagosPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/pagos.service", () => ({
  listarPagos: vi.fn(),
  listarPrimasPendientes: vi.fn(),
  obtenerComprobante: vi.fn(),
}));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ rol: "CLIENTE" });
  vi.mocked(listarPrimasPendientes).mockResolvedValue([]);
});

function pago(cambios: Partial<PagoResumen> = {}): PagoResumen {
  return {
    pago_id: "p1", cotizacion_id: "COT-001", metodo: "TARJETA", monto: "94500.00", moneda: "COP",
    estado: "APROBADO", motivo_rechazo: null, creado_en: "2026-09-17T15:00:00Z",
    concepto: "COMPRA", ...cambios,
  };
}

function prima(cambios: Partial<PrimaPendiente> = {}): PrimaPendiente {
  return {
    tipo: "COTIZACION", accion: "PAGAR", referencia_id: "COT-009", cotizacion_id: "COT-009",
    poliza_id: null, numero_poliza: null, ramo: "VIDA", nombre_ramo: "Microseguro de vida",
    monto: "89000.00", moneda: "COP", fecha_limite: "2026-12-01T15:00:00Z", mensaje: null,
    ...cambios,
  };
}

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
      estado: "APROBADO", motivo_rechazo: null, creado_en: "2026-09-17T15:00:00Z", concepto: "COMPRA",
    },
    {
      pago_id: "p2", cotizacion_id: "COT-002", metodo: "PSE", monto: "91200.00", moneda: "COP",
      estado: "RECHAZADO", motivo_rechazo: "FONDOS_INSUFICIENTES", creado_en: "2026-08-17T15:00:00Z",
      concepto: "COMPRA",
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

it("ofrece el contrato solo si falta firmarlo", async () => {
  vi.mocked(listarPagos).mockResolvedValue([
    pago({ pago_id: "p1", cotizacion_id: "COT-001" }),
    pago({ pago_id: "p2", cotizacion_id: "COT-002" }),
    pago({ pago_id: "p3", cotizacion_id: "COT-003", estado: "PENDIENTE" }),
  ]);
  vi.mocked(listarPrimasPendientes).mockResolvedValue([
    prima({ tipo: "FIRMA_PENDIENTE", accion: "FIRMAR", cotizacion_id: "COT-001", referencia_id: "COT-001" }),
  ]);
  render(<MemoryRouter initialEntries={["/pagos"]}><Routes>
    <Route path="/pagos" element={<PagosPage />} />
    <Route path="/firma/:cotizacionId" element={<h1>Firma</h1>} />
  </Routes></MemoryRouter>);

  // Solo el pago de la cotización con la firma pendiente muestra "Contrato".
  const contratos = await screen.findAllByRole("button", { name: "Contrato" });
  expect(contratos).toHaveLength(1);
  expect(screen.getAllByRole("button", { name: "Comprobante" })).toHaveLength(2);
  await userEvent.click(contratos[0]);
  expect(await screen.findByRole("heading", { name: "Firma" })).toBeInTheDocument();
});

it("no ofrece el contrato cuando no hay firmas pendientes", async () => {
  vi.mocked(listarPagos).mockResolvedValue([pago()]);
  pagos();
  expect(await screen.findByRole("button", { name: "Comprobante" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Contrato" })).not.toBeInTheDocument();
});

it("distingue en el historial una renovación de una compra", async () => {
  vi.mocked(listarPagos).mockResolvedValue([
    pago({ pago_id: "p1", concepto: "RENOVACION", cotizacion_id: "COT-REN" }),
    pago({ pago_id: "p2", concepto: "COMPRA", cotizacion_id: "COT-001" }),
  ]);
  pagos();
  expect(await screen.findByText("Renovación — cotización COT-REN")).toBeInTheDocument();
  expect(screen.getByText("Prima — cotización COT-001")).toBeInTheDocument();
});

it("lista los pagos pendientes con su valor, fecha límite y acción", async () => {
  vi.mocked(listarPagos).mockResolvedValue([]);
  vi.mocked(listarPrimasPendientes).mockResolvedValue([
    prima({
      tipo: "RENOVACION", referencia_id: "REN-1", cotizacion_id: "COT-REN",
      poliza_id: "POL-1", numero_poliza: "SOL-2026-0001", monto: "420000.00",
    }),
    prima(),
    prima({
      tipo: "FIRMA_PENDIENTE", accion: "FIRMAR", referencia_id: "COT-010", cotizacion_id: "COT-010",
      fecha_limite: null, mensaje: "Firma tu contrato en el portal web para emitir tu póliza.",
    }),
  ]);
  pagos();

  expect(await screen.findByText("Renovación — póliza SOL-2026-0001")).toBeInTheDocument();
  expect(screen.getByText("$ 420.000")).toBeInTheDocument();
  expect(screen.getByText("Microseguro de vida — cotización COT-009")).toBeInTheDocument();
  expect(screen.getByText("Microseguro de vida — contrato por firmar")).toBeInTheDocument();
  expect(screen.getByText(/Firma tu contrato en el portal web/)).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "Pagar" })).toHaveLength(2);
  expect(screen.getByRole("button", { name: "Firmar contrato" })).toBeInTheDocument();
});

it("paga una prima pendiente yendo al pago de su cotización", async () => {
  vi.mocked(listarPagos).mockResolvedValue([]);
  vi.mocked(listarPrimasPendientes).mockResolvedValue([prima()]);
  render(<MemoryRouter initialEntries={["/pagos"]}><Routes>
    <Route path="/pagos" element={<PagosPage />} />
    <Route path="/cotizar" element={<DestinoConBusqueda />} />
  </Routes></MemoryRouter>);

  await userEvent.click(await screen.findByRole("button", { name: "Pagar" }));
  expect(await screen.findByText("?cotizacion=COT-009")).toBeInTheDocument();
});

it("firma el contrato desde un pendiente de firma", async () => {
  vi.mocked(listarPagos).mockResolvedValue([]);
  vi.mocked(listarPrimasPendientes).mockResolvedValue([
    prima({ tipo: "FIRMA_PENDIENTE", accion: "FIRMAR", cotizacion_id: "COT-010", fecha_limite: null }),
  ]);
  render(<MemoryRouter initialEntries={["/pagos"]}><Routes>
    <Route path="/pagos" element={<PagosPage />} />
    <Route path="/firma/:cotizacionId" element={<h1>Firma</h1>} />
  </Routes></MemoryRouter>);

  await userEvent.click(await screen.findByRole("button", { name: "Firmar contrato" }));
  expect(await screen.findByRole("heading", { name: "Firma" })).toBeInTheDocument();
});

it("indica cuando no hay pagos pendientes", async () => {
  vi.mocked(listarPagos).mockResolvedValue([]);
  pagos();
  expect(await screen.findByText("No tienes pagos pendientes.")).toBeInTheDocument();
});

it("informa el error si no puede consultar los pagos pendientes", async () => {
  vi.mocked(listarPagos).mockResolvedValue([]);
  vi.mocked(listarPrimasPendientes).mockRejectedValue(
    new Error("No fue posible consultar tus pagos pendientes."),
  );
  pagos();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "No fue posible consultar tus pagos pendientes.",
  );
});

it("muestra y oculta el comprobante de un pago aprobado", async () => {
  vi.mocked(listarPagos).mockResolvedValue([pago()]);
  vi.mocked(obtenerComprobante).mockResolvedValue({
    comprobante_id: "CMP-p1", numero: "CP-20260917-ABCD1234", pago_id: "p1",
    cotizacion_id: "COT-001", concepto: "COMPRA", descripcion: "Prima de Microseguro de vida",
    poliza_id: null, numero_poliza: null, nombre_ramo: "Microseguro de vida", monto: "94500.00",
    moneda: "COP", metodo: "TARJETA", referencia_pasarela: "PSP-1",
    pagado_en: "2026-09-17T15:00:00Z", emitido_en: "2026-09-17T15:00:01Z",
  });
  pagos();

  const boton = await screen.findByRole("button", { name: "Comprobante" });
  await userEvent.click(boton);
  expect(await screen.findByText("CP-20260917-ABCD1234")).toBeInTheDocument();
  expect(screen.getByText("Prima de Microseguro de vida")).toBeInTheDocument();
  expect(screen.getByText("PSP-1")).toBeInTheDocument();
  expect(obtenerComprobante).toHaveBeenCalledWith("p1");

  await userEvent.click(boton);
  expect(screen.queryByText("CP-20260917-ABCD1234")).not.toBeInTheDocument();
});

it("avisa si no puede consultar el comprobante", async () => {
  vi.mocked(listarPagos).mockResolvedValue([pago()]);
  vi.mocked(obtenerComprobante).mockRejectedValue(new Error("No fue posible consultar el comprobante."));
  pagos();

  await userEvent.click(await screen.findByRole("button", { name: "Comprobante" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("No fue posible consultar el comprobante.");
});

function DestinoConBusqueda() {
  return <p>{useLocation().search}</p>;
}

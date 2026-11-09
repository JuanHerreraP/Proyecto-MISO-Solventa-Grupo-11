import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import {
  obtenerHistorialPoliza,
  resolverPolizaAuditoria,
} from "../services/historial-poliza.service";
import type { HistorialPoliza } from "../types/historial";
import type { PolizaResuelta } from "../types/historial-poliza";
import ConsultaHistorialContractualPage from "./ConsultaHistorialContractualPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));
vi.mock("../services/historial-poliza.service", () => ({
  obtenerHistorialPoliza: vi.fn(),
  resolverPolizaAuditoria: vi.fn(),
}));

const RESUELTA: PolizaResuelta = {
  poliza_id: "POL-1",
  numero_poliza: "SOLV-VID-2026-000152",
  cliente_id: "CLIENTE-123",
  nombre_ramo: "Seguro de vida",
  estado: "VIGENTE",
};

const HISTORIAL: HistorialPoliza = {
  poliza_id: "POL-1",
  numero_poliza: "SOLV-VID-2026-000152",
  cliente_id: "CLIENTE-123",
  nombre_ramo: "Seguro de vida",
  estado: "VIGENTE",
  movimientos: [
    {
      movimiento_id: "END-002",
      poliza_id: "POL-1",
      categoria: "CONTRACTUAL",
      tipo: "ENDOSO",
      fecha: "2026-11-08T15:40:22Z",
      descripcion: "Endoso #2",
      referencia: "END-002",
      referencia_externa: null,
      estado: "COMPLETADO",
      monto: "25000.00",
      moneda: "COP",
      naturaleza_monto: "AJUSTE",
      cambios: [
        {
          tipo: "BENEFICIARIO_MODIFICADO",
          descripcion: "Se actualizan los datos de María Pérez.",
          antes: { porcentaje: "50.00" },
          despues: { porcentaje: "60.00" },
        },
      ],
      consentimiento: {
        explicito: true,
        tipo: "CONFIRMACION_ENDOSO",
        usuario_id: "USR-123",
        rol: "CLIENTE",
        fecha: "2026-11-08T15:40:22Z",
        huella_solicitud: "84f2c93d",
      },
      ajuste_prima: {
        prima_anterior: "125000.00",
        ajuste: "25000.00",
        prima_nueva: "150000.00",
        moneda: "COP",
      },
      auditoria: {
        usuario_id: "USR-123",
        rol: "CLIENTE",
        ip_solicitante: "192.168.1.25",
        user_agent: "Mozilla Firefox",
        huella_solicitud: "84f2c93d",
        creado_en: "2026-11-08T15:40:22Z",
      },
    },
    {
      movimiento_id: "PAY-001",
      poliza_id: "POL-1",
      categoria: "FINANCIERO",
      tipo: "PAGO_PRIMA_INICIAL",
      fecha: "2026-10-20T14:00:00Z",
      descripcion: "Pago de prima inicial",
      referencia: "PAY-001",
      referencia_externa: "PSP-889021",
      estado: "APROBADO",
      monto: "125000.00",
      moneda: "COP",
      naturaleza_monto: "COBRO",
      cambios: [],
      consentimiento: null,
    },
    {
      movimiento_id: "POL-1-EMISION",
      poliza_id: "POL-1",
      categoria: "POLIZA",
      tipo: "EMISION",
      fecha: "2026-10-20T13:00:00Z",
      descripcion: "Póliza emitida",
      referencia: "SOLV-VID-2026-000152",
      referencia_externa: null,
      estado: "COMPLETADO",
      monto: null,
      moneda: null,
      naturaleza_monto: null,
      cambios: [],
      consentimiento: null,
    },
  ],
};

function montar() {
  return render(
    <MemoryRouter>
      <ConsultaHistorialContractualPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "AUD-1", rol: "ANALISTA_CUMPLIMIENTO" });
});

it("muestra el formulario con un único campo de póliza", async () => {
  montar();
  expect(await screen.findByLabelText("Póliza")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Consultar historial" }),
  ).toBeInTheDocument();
});

it("exige el campo póliza y no consulta si está vacío", async () => {
  montar();
  await userEvent.click(await screen.findByRole("button", { name: "Consultar historial" }));
  expect(
    screen.getByText("Ingresa el identificador o número de la póliza."),
  ).toBeInTheDocument();
  expect(resolverPolizaAuditoria).not.toHaveBeenCalled();
  expect(obtenerHistorialPoliza).not.toHaveBeenCalled();
});

it("aplica trim al identificador antes de resolver la póliza", async () => {
  vi.mocked(resolverPolizaAuditoria).mockResolvedValue(RESUELTA);
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue(HISTORIAL);
  montar();
  await userEvent.type(await screen.findByLabelText("Póliza"), "  POL-1  ");
  await userEvent.click(screen.getByRole("button", { name: "Consultar historial" }));
  expect(resolverPolizaAuditoria).toHaveBeenCalledWith("POL-1");
  expect(obtenerHistorialPoliza).toHaveBeenCalledWith("POL-1");
});

it("renderiza el historial en orden descendente con datos financieros", async () => {
  vi.mocked(resolverPolizaAuditoria).mockResolvedValue(RESUELTA);
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue(HISTORIAL);
  montar();
  await userEvent.type(await screen.findByLabelText("Póliza"), "POL-1");
  await userEvent.click(screen.getByRole("button", { name: "Consultar historial" }));

  // Metadatos de la póliza.
  expect(await screen.findByText("Seguro de vida")).toBeInTheDocument();
  expect(screen.getByText("CLIENTE-123")).toBeInTheDocument();
  expect(screen.getByText("VIGENTE")).toBeInTheDocument();

  const lista = screen.getByRole("region", { name: "Historial de movimientos" });
  const titulos = within(lista)
    .getAllByText(/Modificación contractual|Pago de prima inicial|Emisión de póliza/, {
      selector: ".cotizacion-cabecera-texto strong",
    })
    .map((e) => e.textContent);
  expect(titulos).toEqual([
    "Modificación contractual",
    "Pago de prima inicial",
    "Emisión de póliza",
  ]);

  // Referencia financiera de la pasarela, monto y estado del pago.
  expect(within(lista).getByText("PSP-889021")).toBeInTheDocument();
  expect(within(lista).getByText("APROBADO")).toBeInTheDocument();
});

it("muestra loading mientras consulta", async () => {
  let resolver: (valor: PolizaResuelta) => void = () => {};
  vi.mocked(resolverPolizaAuditoria).mockReturnValue(
    new Promise<PolizaResuelta>((r) => { resolver = r; }),
  );
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue(HISTORIAL);
  montar();
  await userEvent.type(await screen.findByLabelText("Póliza"), "POL-1");
  await userEvent.click(screen.getByRole("button", { name: "Consultar historial" }));
  expect(await screen.findByText("Cargando historial…")).toBeInTheDocument();
  resolver(RESUELTA);
});

it("muestra el detalle contractual: antes/después, consentimiento y auditoría", async () => {
  vi.mocked(resolverPolizaAuditoria).mockResolvedValue(RESUELTA);
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue(HISTORIAL);
  montar();
  await userEvent.type(await screen.findByLabelText("Póliza"), "POL-1");
  await userEvent.click(screen.getByRole("button", { name: "Consultar historial" }));

  await screen.findByText("Seguro de vida");
  await userEvent.click(screen.getAllByRole("button", { name: "Ver detalle" })[0]);

  // Linaje antes/después.
  expect(screen.getByText("porcentaje: 50.00")).toBeInTheDocument();
  expect(screen.getByText("porcentaje: 60.00")).toBeInTheDocument();
  // Consentimiento explícito.
  expect(
    screen.getByText("Consentimiento: aceptación explícita registrada"),
  ).toBeInTheDocument();
  // Información de auditoría.
  expect(screen.getByText("Información de auditoría")).toBeInTheDocument();
  expect(screen.getByText("192.168.1.25")).toBeInTheDocument();
  expect(screen.getByText("Mozilla Firefox")).toBeInTheDocument();
  expect(screen.getByText("84f2c93d")).toBeInTheDocument();
});

it("muestra el mensaje de póliza no encontrada", async () => {
  vi.mocked(resolverPolizaAuditoria).mockRejectedValue(
    new Error("No encontramos la póliza."),
  );
  montar();
  await userEvent.type(await screen.findByLabelText("Póliza"), "POL-999");
  await userEvent.click(screen.getByRole("button", { name: "Consultar historial" }));
  expect(await screen.findByText("No encontramos la póliza.")).toBeInTheDocument();
  expect(obtenerHistorialPoliza).not.toHaveBeenCalled();
});

it("muestra un error del servidor", async () => {
  vi.mocked(resolverPolizaAuditoria).mockResolvedValue(RESUELTA);
  vi.mocked(obtenerHistorialPoliza).mockRejectedValue(
    new Error("No fue posible consultar el historial de la póliza."),
  );
  montar();
  await userEvent.type(await screen.findByLabelText("Póliza"), "POL-1");
  await userEvent.click(screen.getByRole("button", { name: "Consultar historial" }));
  expect(
    await screen.findByText("No fue posible consultar el historial de la póliza."),
  ).toBeInTheDocument();
});

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import { obtenerHistorialPoliza } from "../services/historial-poliza.service";
import type { HistorialPoliza } from "../types/historial";
import HistorialPolizaPage from "./HistorialPolizaPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/historial-poliza.service", () => ({ obtenerHistorialPoliza: vi.fn() }));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));

const HISTORIAL: HistorialPoliza = {
  poliza_id: "POL-1",
  numero_poliza: "SOLV-VIA-2026-00152",
  movimientos: [
    {
      movimiento_id: "DES-001",
      poliza_id: "POL-1",
      categoria: "FINANCIERO",
      tipo: "DESEMBOLSO_INDEMNIZACION",
      fecha: "2026-11-07T14:30:00Z",
      descripcion: "Pago de indemnización por siniestro",
      referencia: "DES-001",
      referencia_externa: "TRF-889900",
      estado: "COMPLETADA",
      monto: "850000.00",
      moneda: "COP",
      naturaleza_monto: "INDEMNIZACION",
      cambios: [],
      consentimiento: null,
    },
    {
      movimiento_id: "END-001-002",
      poliza_id: "POL-1",
      categoria: "CONTRACTUAL",
      tipo: "ENDOSO",
      fecha: "2026-11-04T15:40:00Z",
      descripcion: "Endoso #2",
      referencia: "END-001-002",
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
        usuario_id: "USR-1",
        rol: "CLIENTE",
        fecha: "2026-11-04T15:40:00Z",
        huella_solicitud: "abc",
      },
    },
    {
      movimiento_id: "PAY-001",
      poliza_id: "POL-1",
      categoria: "FINANCIERO",
      tipo: "PAGO_PRIMA_INICIAL",
      fecha: "2026-10-20T13:45:00Z",
      descripcion: "Pago de prima inicial",
      referencia: "PAY-001",
      referencia_externa: "PSP-88910",
      estado: "APROBADO",
      monto: "125000.00",
      moneda: "COP",
      naturaleza_monto: "COBRO",
      cambios: [],
      consentimiento: null,
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "CLI-1", rol: "CLIENTE" });
});

function montar() {
  render(
    <MemoryRouter initialEntries={["/polizas/POL-1/historial"]}>
      <Routes>
        <Route path="/polizas/:polizaId/historial" element={<HistorialPolizaPage />} />
        <Route path="/polizas" element={<h1>Mis pólizas</h1>} />
        <Route path="/login" element={<h1>Inicia sesión</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

it("carga el historial y muestra el número de póliza", async () => {
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue(HISTORIAL);
  montar();
  expect(await screen.findByText("SOLV-VIA-2026-00152")).toBeInTheDocument();
  expect(obtenerHistorialPoliza).toHaveBeenCalledWith("POL-1");
});

it("muestra los movimientos en el orden recibido (más reciente arriba)", async () => {
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue(HISTORIAL);
  montar();
  await screen.findByText("Pago de indemnización");
  const tarjetas = screen.getAllByText(
    /^(Pago de indemnización|Modificación contractual|Pago de prima inicial)$/,
  );
  expect(tarjetas[0]).toHaveTextContent("Pago de indemnización");
  expect(tarjetas[1]).toHaveTextContent("Modificación contractual");
  expect(tarjetas[2]).toHaveTextContent("Pago de prima inicial");
});

it("muestra el monto con signo y la referencia de la pasarela del pago", async () => {
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue(HISTORIAL);
  const { container } = render(
    <MemoryRouter initialEntries={["/polizas/POL-1/historial"]}>
      <Routes>
        <Route path="/polizas/:polizaId/historial" element={<HistorialPolizaPage />} />
      </Routes>
    </MemoryRouter>,
  );
  await screen.findAllByText("Pago de prima inicial");
  // El cobro se muestra en negativo; se eliminan símbolos y separadores para comparar.
  const texto = (container.textContent ?? "").normalize("NFKC").replace(/[\s$.]/g, "");
  expect(texto).toContain("-125000");
  expect(screen.getByText("PSP-88910")).toBeInTheDocument();
  expect(screen.getByText("APROBADO")).toBeInTheDocument();
});

it("la indemnización se muestra en positivo con su referencia", async () => {
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue(HISTORIAL);
  montar();
  await screen.findByText("Pago de indemnización");
  const montos = screen.getAllByText((texto) => /\+\D*850\D?000/.test(texto));
  expect(montos.length).toBeGreaterThan(0);
  expect(screen.getByText("TRF-889900")).toBeInTheDocument();
});

it("muestra el consentimiento del endoso y el linaje antes/después al abrir el detalle", async () => {
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue(HISTORIAL);
  montar();
  await screen.findByText("Modificación contractual");
  expect(screen.getByText(/Consentimiento: confirmado por el cliente/)).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Ver detalle" }));
  expect(await screen.findByText("Se actualizan los datos de María Pérez.")).toBeInTheDocument();
  const cambio = screen.getByText("Se actualizan los datos de María Pérez.").closest(".historial-cambio") as HTMLElement;
  expect(within(cambio).getByText("porcentaje: 50.00")).toBeInTheDocument();
  expect(within(cambio).getByText("porcentaje: 60.00")).toBeInTheDocument();
});

it("muestra 'Sin referencia externa' cuando el movimiento financiero no la tiene", async () => {
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue({
    ...HISTORIAL,
    movimientos: [{ ...HISTORIAL.movimientos[2], referencia_externa: null }],
  });
  montar();
  expect(await screen.findByText("Sin referencia externa")).toBeInTheDocument();
});

it("muestra el estado vacío cuando no hay movimientos", async () => {
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue({
    poliza_id: "POL-1",
    numero_poliza: "SOLV-VIA-2026-00152",
    movimientos: [],
  });
  montar();
  expect(
    await screen.findByText("Todavía no hay movimientos registrados para esta póliza."),
  ).toBeInTheDocument();
});

it("muestra el error y permite reintentar", async () => {
  vi.mocked(obtenerHistorialPoliza)
    .mockRejectedValueOnce(new Error("No fue posible consultar el historial de la póliza."))
    .mockResolvedValueOnce(HISTORIAL);
  montar();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "No fue posible consultar el historial de la póliza.",
  );
  await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
  expect(await screen.findByText("Pago de indemnización")).toBeInTheDocument();
});

it("no muestra información sensible (huella, usuario_id) en la vista", async () => {
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue(HISTORIAL);
  const { container } = render(
    <MemoryRouter initialEntries={["/polizas/POL-1/historial"]}>
      <Routes>
        <Route path="/polizas/:polizaId/historial" element={<HistorialPolizaPage />} />
      </Routes>
    </MemoryRouter>,
  );
  await screen.findByText("Modificación contractual");
  await userEvent.click(screen.getByRole("button", { name: "Ver detalle" }));
  expect(container.textContent).not.toContain("abc");
  expect(container.textContent).not.toContain("huella");
});

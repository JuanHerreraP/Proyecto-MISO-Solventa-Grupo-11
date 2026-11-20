import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import {
  confirmarCancelacion,
  consultarCancelacion,
  type CondicionesCancelacion,
} from "../services/cancelaciones.service";
import CancelarPolizaPage from "./CancelarPolizaPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/cancelaciones.service", () => ({
  consultarCancelacion: vi.fn(),
  confirmarCancelacion: vi.fn(),
}));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));

const CONDICIONES: CondicionesCancelacion = {
  poliza_id: "POL-1",
  numero_poliza: "SOL-001",
  cancelable: true,
  bloqueos: [],
  fecha_efecto: "2026-11-15",
  dias_totales: 30,
  dias_no_transcurridos: 15,
  prima_total: "84000.00",
  saldo_estimado: "42000.00",
  moneda: "COP",
  consecuencias: ["La cobertura termina de inmediato."],
  motivos: [
    { codigo: "YA_NO_LA_NECESITO", etiqueta: "Ya no la necesito" },
    { codigo: "OTRO", etiqueta: "Otro motivo" },
  ],
  cancelacion: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "CLI-1", rol: "CLIENTE" });
  vi.mocked(consultarCancelacion).mockResolvedValue(CONDICIONES);
});

function montar() {
  render(
    <MemoryRouter initialEntries={["/polizas/POL-1/cancelar"]}>
      <Routes>
        <Route path="/polizas/:polizaId/cancelar" element={<CancelarPolizaPage />} />
        <Route path="/polizas" element={<h1>Mis pólizas</h1>} />
        <Route path="/login" element={<h1>Inicia sesión</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

it("muestra la liquidación y las consecuencias antes de cancelar", async () => {
  montar();

  expect(await screen.findByText("$ 42.000")).toBeInTheDocument();
  expect(screen.getByText("La cobertura termina de inmediato.")).toBeInTheDocument();
  expect(consultarCancelacion).toHaveBeenCalledWith("POL-1");
});

it("exige motivo y confirmación antes de enviar la cancelación", async () => {
  vi.mocked(confirmarCancelacion).mockResolvedValue({
    cancelacion_id: "CAN-POL-1",
    poliza_id: "POL-1",
    motivo: "YA_NO_LA_NECESITO",
    detalle: null,
    fecha_efecto: "2026-11-15",
    dias_totales: 30,
    dias_no_transcurridos: 15,
    prima_total: "84000.00",
    saldo_estimado: "42000.00",
    moneda: "COP",
    estado_devolucion: "PENDIENTE",
    creado_en: "2026-11-15T12:00:00Z",
  });
  montar();

  const boton = await screen.findByRole("button", { name: "Confirmar cancelación" });
  expect(boton).toBeDisabled();
  await userEvent.selectOptions(screen.getByLabelText("Selecciona un motivo"), "YA_NO_LA_NECESITO");
  await userEvent.click(screen.getByRole("checkbox"));
  expect(boton).toBeEnabled();
  await userEvent.click(boton);

  expect(confirmarCancelacion).toHaveBeenCalledWith(
    "POL-1",
    { motivo: "YA_NO_LA_NECESITO" },
    expect.any(String),
  );
  expect(await screen.findByRole("heading", { name: "Póliza cancelada" })).toBeInTheDocument();
});

it("explica por qué una póliza no se puede cancelar", async () => {
  vi.mocked(consultarCancelacion).mockResolvedValue({
    ...CONDICIONES,
    cancelable: false,
    bloqueos: [{
      codigo: "SINIESTRO_EN_TRAMITE",
      mensaje: "La póliza tiene un siniestro en trámite.",
      siniestros: ["SIN-1"],
    }],
  });
  montar();

  expect(await screen.findByText("Esta póliza no se puede cancelar")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Confirmar cancelación" })).not.toBeInTheDocument();
});

it("identifica cuando el asesor actúa en nombre de un cliente", async () => {
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "ASE-1", rol: "ASESOR_VENTAS" });
  render(
    <MemoryRouter
      initialEntries={[{
        pathname: "/polizas/POL-1/cancelar",
        state: { clienteNombre: "Ana Solano" },
      }]}
    >
      <Routes>
        <Route path="/polizas/:polizaId/cancelar" element={<CancelarPolizaPage />} />
      </Routes>
    </MemoryRouter>,
  );

  expect(await screen.findByText(/como asesor para Ana Solano/)).toBeInTheDocument();
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import { obtenerBilletera, obtenerCertificado } from "../services/billetera.service";
import type { Certificado, PolizaResumen } from "../services/billetera.service";
import PolizasPage from "./PolizasPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/billetera.service", () => ({
  obtenerBilletera: vi.fn(),
  obtenerCertificado: vi.fn(),
}));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));

const POLIZA: PolizaResumen = {
  poliza_id: "POL-1",
  numero_poliza: "SOL-VJ-0001",
  ramo: "VIAJE",
  nombre_ramo: "Seguro de viaje",
  estado: "VIGENTE",
  activa: true,
  fecha_inicio: "2026-10-01",
  fecha_fin: "2026-11-01",
  cobertura_principal: "Asistencia en viaje",
};

const CERTIFICADO: Certificado = {
  poliza_id: "POL-1",
  numero_poliza: "SOL-VJ-0001",
  nombre_ramo: "Seguro de viaje",
  estado: "VIGENTE",
  activa: true,
  titular: "Ana Solano",
  documento_titular: "CC ****5678",
  fecha_inicio: "2026-10-01",
  fecha_fin: "2026-11-01",
  cobertura_principal: "Asistencia en viaje",
  suma_asegurada: "40000000.00",
  prima_total: "85000.00",
  moneda: "COP",
  emitida_en: "2026-10-01T12:00:00Z",
  contenido_qr: "SOLVENTA|SOL-VJ-0001|abc",
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "CLI-1", rol: "CLIENTE" });
});

function montar() {
  render(
    <MemoryRouter initialEntries={["/polizas"]}>
      <Routes>
        <Route path="/polizas" element={<PolizasPage />} />
        <Route path="/login" element={<h1>Inicia sesión</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

it("lista las pólizas del cliente", async () => {
  vi.mocked(obtenerBilletera).mockResolvedValue({
    polizas: [POLIZA], total_vigentes: 1, total_inactivas: 0,
  });
  montar();
  expect(await screen.findByText("Seguro de viaje")).toBeInTheDocument();
  expect(screen.getByText("Vigente")).toBeInTheDocument();
});

it("despliega el detalle y carga el certificado al hacer clic", async () => {
  vi.mocked(obtenerBilletera).mockResolvedValue({
    polizas: [POLIZA], total_vigentes: 1, total_inactivas: 0,
  });
  vi.mocked(obtenerCertificado).mockResolvedValue(CERTIFICADO);
  montar();
  await userEvent.click(await screen.findByRole("button", { name: /Seguro de viaje/ }));

  expect(await screen.findByText("Ana Solano")).toBeInTheDocument();
  expect(screen.getByText("CC ****5678")).toBeInTheDocument();
  expect(obtenerCertificado).toHaveBeenCalledWith("POL-1");
});

it("indica cuando no hay pólizas", async () => {
  vi.mocked(obtenerBilletera).mockResolvedValue({
    polizas: [], total_vigentes: 0, total_inactivas: 0,
  });
  montar();
  expect(await screen.findByText("Aún no tienes pólizas.")).toBeInTheDocument();
});

it("informa el error si no puede consultar", async () => {
  vi.mocked(obtenerBilletera).mockRejectedValue(
    new Error("No fue posible consultar tus pólizas."),
  );
  montar();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "No fue posible consultar tus pólizas.",
  );
});

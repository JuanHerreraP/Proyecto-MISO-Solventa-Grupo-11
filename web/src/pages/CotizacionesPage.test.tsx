import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import { listarCotizaciones, obtenerRamos } from "../services/cotizaciones.service";
import type { Cotizacion, DefinicionRamo } from "../types/cotizaciones";
import CotizacionesPage from "./CotizacionesPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/cotizaciones.service", () => ({
  listarCotizaciones: vi.fn(),
  obtenerRamos: vi.fn(),
}));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));

const RAMO_VIAJE: DefinicionRamo = {
  ramo: "VIAJE",
  nombre: "Seguro de viaje",
  descripcion: "Protección durante un viaje.",
  campos: [
    { codigo: "destino", etiqueta: "Destino", tipo: "TEXTO", requerido: true, descripcion: "", unidad: null, opciones: [] },
    { codigo: "numero_viajeros", etiqueta: "Número de viajeros", tipo: "ENTERO", requerido: true, descripcion: "", unidad: null, opciones: [] },
  ],
};

const COTIZACION: Cotizacion = {
  cotizacion_id: "COT-001",
  cliente_id: "CLI-1",
  ramo: "VIAJE",
  datos_riesgo: { destino: "Lima", numero_viajeros: 2 },
  estado: "VIGENTE",
  prima_total: "45000.00",
  moneda: "COP",
  cobertura_principal: {
    codigo: "ASIST", nombre: "Asistencia en viaje", suma_asegurada: "1000000.00", descripcion: null,
  },
  creada_en: "2026-10-24T12:00:00Z",
  vigente_hasta: "2026-11-24T12:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "CLI-1", rol: "CLIENTE" });
  vi.mocked(obtenerRamos).mockResolvedValue([RAMO_VIAJE]);
});

function montar() {
  render(
    <MemoryRouter initialEntries={["/cotizaciones"]}>
      <Routes>
        <Route path="/cotizaciones" element={<CotizacionesPage />} />
        <Route path="/login" element={<h1>Inicia sesión</h1>} />
        <Route path="/cotizar" element={<h1>Cotizar</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

it("lista las cotizaciones del cliente", async () => {
  vi.mocked(listarCotizaciones).mockResolvedValue([COTIZACION]);
  montar();
  expect(await screen.findByText("Seguro de viaje")).toBeInTheDocument();
  expect(screen.getByText("Vigente")).toBeInTheDocument();
});

it("despliega el detalle con los datos del formulario al hacer clic", async () => {
  vi.mocked(listarCotizaciones).mockResolvedValue([COTIZACION]);
  montar();
  await userEvent.click(await screen.findByRole("button", { name: /Seguro de viaje/ }));

  // Etiquetas legibles tomadas del catálogo de ramos y sus valores.
  expect(await screen.findByText("Destino")).toBeInTheDocument();
  expect(screen.getByText("Lima")).toBeInTheDocument();
  expect(screen.getByText("Número de viajeros")).toBeInTheDocument();
  expect(screen.getByText("Asistencia en viaje")).toBeInTheDocument();
});

it("indica cuando no hay cotizaciones", async () => {
  vi.mocked(listarCotizaciones).mockResolvedValue([]);
  montar();
  expect(await screen.findByText("Aún no tienes cotizaciones.")).toBeInTheDocument();
});

it("informa el error si no puede consultar", async () => {
  vi.mocked(listarCotizaciones).mockRejectedValue(
    new Error("No fue posible consultar tus cotizaciones."),
  );
  montar();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "No fue posible consultar tus cotizaciones.",
  );
});

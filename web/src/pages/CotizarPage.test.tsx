import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import {
  crearCotizacion,
  obtenerCotizacion,
  obtenerRamos,
} from "../services/cotizaciones.service";
import { crearPago, obtenerPago } from "../services/pagos.service";
import type { Cotizacion, DefinicionRamo } from "../types/cotizaciones";
import CotizarPage from "./CotizarPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/cotizaciones.service", () => ({
  obtenerRamos: vi.fn(),
  crearCotizacion: vi.fn(),
  obtenerCotizacion: vi.fn(),
}));
vi.mock("../services/pagos.service", () => ({
  crearPago: vi.fn(),
  obtenerPago: vi.fn(),
}));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));

const RAMO_VIAJE: DefinicionRamo = {
  ramo: "VIAJE",
  nombre: "Seguro de viaje",
  descripcion: "Protección durante un viaje.",
  campos: [
    {
      codigo: "destino",
      etiqueta: "Destino",
      tipo: "TEXTO",
      requerido: true,
      descripcion: "País del viaje.",
      unidad: null,
      opciones: [],
    },
  ],
};

const RAMO_VIDA: DefinicionRamo = {
  ramo: "VIDA",
  nombre: "Microseguro de vida",
  descripcion: "Protección de vida.",
  campos: [
    {
      codigo: "fecha_nacimiento",
      etiqueta: "Fecha de nacimiento",
      tipo: "FECHA",
      requerido: true,
      descripcion: "Fecha de nacimiento.",
      unidad: null,
      opciones: [],
    },
    {
      codigo: "fumador",
      etiqueta: "¿Es fumador?",
      tipo: "BOOLEANO",
      requerido: false,
      descripcion: "Indica si fuma.",
      unidad: null,
      opciones: [],
    },
    {
      codigo: "plan",
      etiqueta: "Plan",
      tipo: "OPCION",
      requerido: true,
      descripcion: "Plan elegido.",
      unidad: null,
      opciones: ["BASICO", "PREMIUM"],
    },
  ],
};

const COTIZACION: Cotizacion = {
  cotizacion_id: "COT-001",
  cliente_id: "CLI-1",
  ramo: "VIAJE",
  datos_riesgo: { destino: "Lima" },
  estado: "VIGENTE",
  prima_total: "45000.00",
  moneda: "COP",
  cobertura_principal: {
    codigo: "ASIST",
    nombre: "Asistencia en viaje",
    suma_asegurada: "1000000.00",
    descripcion: "Cobertura médica.",
  },
  creada_en: "2026-10-24T12:00:00Z",
  vigente_hasta: "2026-11-24T12:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "CLI-1", rol: "CLIENTE" });
  vi.mocked(obtenerRamos).mockResolvedValue([RAMO_VIAJE]);
  vi.mocked(crearCotizacion).mockResolvedValue(COTIZACION);
});

function montar(ruta = "/cotizar") {
  render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route path="/cotizar" element={<CotizarPage />} />
        <Route path="/home" element={<h1>Inicio</h1>} />
        <Route path="/login" element={<h1>Inicia sesión</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

async function avanzarHastaPago() {
  montar();
  await userEvent.click(await screen.findByRole("button", { name: /Seguro de viaje/ }));
  await userEvent.type(await screen.findByLabelText("Destino"), "Lima");
  await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
  await userEvent.click(await screen.findByRole("button", { name: "Aceptar y continuar" }));
}

it("lista los ramos disponibles con sus nombres", async () => {
  montar();
  expect(await screen.findByText("Seguro de viaje")).toBeInTheDocument();
});

it("crea la cotización y muestra el resumen con la prima", async () => {
  montar();
  await userEvent.click(await screen.findByRole("button", { name: /Seguro de viaje/ }));
  await userEvent.type(await screen.findByLabelText("Destino"), "Lima");
  await userEvent.click(screen.getByRole("button", { name: "Continuar" }));

  expect(await screen.findByText("Asistencia en viaje")).toBeInTheDocument();
  expect(screen.getByText("$ 45.000")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Aceptar y continuar" })).toBeInTheDocument();
});

it("paga con tarjeta aprobada y muestra la confirmación", async () => {
  vi.mocked(crearPago).mockResolvedValue({
    pago_id: "PAG-1", cotizacion_id: "COT-001", metodo: "TARJETA", monto: "45000.00",
    moneda: "COP", estado: "APROBADO", motivo_rechazo: null, creado_en: "2026-10-24T12:00:00Z",
    referencia_pasarela: "PSP-1", url_redireccion: null, actualizado_en: "2026-10-24T12:00:00Z",
  });
  await avanzarHastaPago();

  await userEvent.type(await screen.findByLabelText("Número de tarjeta"), "4111111111111111");
  await userEvent.type(screen.getByLabelText("Vencimiento (MM/AA)"), "0829");
  await userEvent.type(screen.getByLabelText("CVV"), "123");
  await userEvent.click(screen.getByRole("button", { name: "Pagar prima" }));

  expect(await screen.findByText("Pago aprobado")).toBeInTheDocument();
});

it("muestra el rechazo y permite reintentar volviendo a pagar la prima", async () => {
  vi.mocked(crearPago).mockResolvedValue({
    pago_id: "PAG-2", cotizacion_id: "COT-001", metodo: "TARJETA", monto: "45000.00",
    moneda: "COP", estado: "RECHAZADO", motivo_rechazo: "FONDOS_INSUFICIENTES",
    creado_en: "2026-10-24T12:00:00Z", referencia_pasarela: "PSP-2", url_redireccion: null,
    actualizado_en: "2026-10-24T12:00:00Z",
  });
  await avanzarHastaPago();

  await userEvent.type(await screen.findByLabelText("Número de tarjeta"), "4111111111111110");
  await userEvent.type(screen.getByLabelText("Vencimiento (MM/AA)"), "0829");
  await userEvent.type(screen.getByLabelText("CVV"), "123");
  await userEvent.click(screen.getByRole("button", { name: "Pagar prima" }));

  expect(await screen.findByText("Pago rechazado")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Reintentar pago" }));
  expect(await screen.findByRole("button", { name: "Pagar prima" })).toBeInTheDocument();
});

it("al volver del portal PSE consulta el pago y muestra el resultado", async () => {
  vi.mocked(obtenerPago).mockResolvedValue({
    pago_id: "PAG-3", cotizacion_id: "COT-001", metodo: "PSE", monto: "45000.00",
    moneda: "COP", estado: "APROBADO", motivo_rechazo: null, creado_en: "2026-10-24T12:00:00Z",
    referencia_pasarela: "PSP-3", url_redireccion: null, actualizado_en: "2026-10-24T12:00:00Z",
  });
  vi.mocked(obtenerCotizacion).mockResolvedValue(COTIZACION);
  montar("/cotizar?pago=PAG-3&estado=APROBADO");

  expect(await screen.findByText("Pago aprobado")).toBeInTheDocument();
  await waitFor(() => expect(obtenerPago).toHaveBeenCalledWith("PAG-3"));
});

it("informa el error cuando falla la creación de la cotización", async () => {
  vi.mocked(crearCotizacion).mockRejectedValue(new Error("El perfil no permite la cobertura."));
  montar();
  await userEvent.click(await screen.findByRole("button", { name: /Seguro de viaje/ }));
  await userEvent.type(await screen.findByLabelText("Destino"), "Lima");
  await userEvent.click(screen.getByRole("button", { name: "Continuar" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("El perfil no permite la cobertura.");
});

it("informa el error cuando falla el pago", async () => {
  vi.mocked(crearPago).mockRejectedValue(new Error("La cotización no está vigente."));
  await avanzarHastaPago();
  await userEvent.type(await screen.findByLabelText("Número de tarjeta"), "4111111111111111");
  await userEvent.type(screen.getByLabelText("Vencimiento (MM/AA)"), "0829");
  await userEvent.type(screen.getByLabelText("CVV"), "123");
  await userEvent.click(screen.getByRole("button", { name: "Pagar prima" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("La cotización no está vigente.");
});

it("cancela desde el resumen y vuelve a la selección de ramos", async () => {
  montar();
  await userEvent.click(await screen.findByRole("button", { name: /Seguro de viaje/ }));
  await userEvent.type(await screen.findByLabelText("Destino"), "Lima");
  await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
  await userEvent.click(await screen.findByRole("button", { name: "Cancelar" }));

  expect(await screen.findByText("Elige el tipo de seguro que quieres cotizar.")).toBeInTheDocument();
});

it("redirige al portal PSE cuando el pago devuelve una URL de redirección", async () => {
  vi.mocked(crearPago).mockResolvedValue({
    pago_id: "PAG-4", cotizacion_id: "COT-001", metodo: "PSE", monto: "45000.00",
    moneda: "COP", estado: "PENDIENTE", motivo_rechazo: null, creado_en: "2026-10-24T12:00:00Z",
    referencia_pasarela: "PSP-4",
    url_redireccion: "http://localhost:8000/api/v1/pagos/pse-simulado/PSP-4",
    actualizado_en: "2026-10-24T12:00:00Z",
  });
  const asignarHref = vi.fn();
  Object.defineProperty(window, "location", {
    value: { origin: "http://localhost:5173", set href(v: string) { asignarHref(v); } },
    writable: true,
  });

  await avanzarHastaPago();
  await userEvent.click(await screen.findByLabelText(/PSE/));
  await userEvent.selectOptions(await screen.findByLabelText("Banco"), "1007");
  await userEvent.click(screen.getByRole("button", { name: "Pagar prima" }));

  await waitFor(() =>
    expect(asignarHref).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/pagos/pse-simulado/PSP-4",
    ),
  );
});

it("renderiza los campos de un ramo con fecha, opción y booleano", async () => {
  vi.mocked(obtenerRamos).mockResolvedValue([RAMO_VIDA]);
  montar();
  await userEvent.click(await screen.findByRole("button", { name: /Microseguro de vida/ }));

  expect(await screen.findByLabelText("Fecha de nacimiento")).toBeInTheDocument();
  expect(screen.getByLabelText("Plan")).toBeInTheDocument();
  expect(screen.getByLabelText(/¿Es fumador\?/)).toBeInTheDocument();
});

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import {
  confirmarEndoso,
  descargarEndoso,
  ErrorEndoso,
  listarEndosos,
  obtenerOpciones,
  simularEndoso,
  type Endoso,
  type OpcionesModificacion,
  type PropuestaEndoso,
} from "../services/endosos.service";
import ModificarPolizaPage from "./ModificarPolizaPage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));
vi.mock("../services/endosos.service", async (original) => ({
  ...(await original<typeof import("../services/endosos.service")>()),
  obtenerOpciones: vi.fn(),
  listarEndosos: vi.fn(),
  simularEndoso: vi.fn(),
  confirmarEndoso: vi.fn(),
  descargarEndoso: vi.fn(),
}));

const OPCIONES: OpcionesModificacion = {
  poliza_id: "POL-1",
  numero_poliza: "SOL-2026-VIDA0001",
  nombre_ramo: "Seguro de vida",
  estado: "VIGENTE",
  modificable: true,
  fecha_inicio: "2026-01-01",
  fecha_fin: "2026-12-31",
  prima_total: "150000.00",
  moneda: "COP",
  cobertura_principal: {
    codigo: "FALLECIMIENTO", nombre: "Cobertura por fallecimiento",
    suma_asegurada: "100000000.00", descripcion: null,
  },
  coberturas_opcionales: [],
  coberturas_disponibles: [
    {
      codigo: "INCAPACIDAD_TOTAL_PERMANENTE", nombre: "Incapacidad total y permanente",
      descripcion: "Anticipa la suma asegurada.", suma_minima: "1000000.00", suma_maxima: "100000000.00",
    },
    {
      codigo: "AUXILIO_FUNERARIO", nombre: "Auxilio funerario",
      descripcion: "Reembolso de gastos funerarios.", suma_minima: "1000000.00", suma_maxima: "10000000.00",
    },
  ],
  admite_beneficiarios: true,
  max_beneficiarios: 10,
  beneficiarios: [],
};

const PROPUESTA: PropuestaEndoso = {
  poliza_id: "POL-1",
  tipo: "COBERTURAS",
  cambios: [{ tipo: "COBERTURA_INCLUIDA", descripcion: "Se incluye Auxilio funerario.", antes: null, despues: {} }],
  beneficiarios: [],
  coberturas_opcionales: [],
  fecha_efecto: "2026-07-02",
  dias_vigencia: 365,
  dias_restantes: 183,
  prima_anterior: "150000.00",
  ajuste_prima: "9150.00",
  concepto_ajuste: "COBRO",
  prima_nueva: "159150.00",
  moneda: "COP",
};

const ENDOSO: Endoso = {
  ...PROPUESTA,
  endoso_id: "END-1-001",
  numero_endoso: 1,
  rol_solicitante: "CLIENTE",
  creado_en: "2026-07-02T15:00:00Z",
  huella_documento: "a".repeat(64),
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "CLI-1", rol: "CLIENTE" });
  vi.mocked(obtenerOpciones).mockResolvedValue(OPCIONES);
  vi.mocked(listarEndosos).mockResolvedValue([]);
});

function montar() {
  render(
    <MemoryRouter initialEntries={["/polizas/POL-1/modificar"]}>
      <Routes>
        <Route path="/polizas/:polizaId/modificar" element={<ModificarPolizaPage />} />
        <Route path="/polizas" element={<h1>Mis pólizas</h1>} />
        <Route path="/login" element={<h1>Inicia sesión</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

it("muestra las coberturas opcionales y la cobertura principal de la póliza", async () => {
  montar();

  expect(await screen.findByText("Seguro de vida · SOL-2026-VIDA0001")).toBeInTheDocument();
  expect(screen.getByText("Incapacidad total y permanente")).toBeInTheDocument();
  expect(screen.getByText("Cobertura por fallecimiento")).toBeInTheDocument();
  expect(obtenerOpciones).toHaveBeenCalledWith("POL-1");
  // La suma solo se edita al incluir la cobertura.
  expect(screen.getByLabelText("Suma asegurada de Auxilio funerario")).toBeDisabled();
});

it("calcula el ajuste, pide aceptación y emite el endoso", async () => {
  vi.mocked(simularEndoso).mockResolvedValue(PROPUESTA);
  vi.mocked(confirmarEndoso).mockResolvedValue(ENDOSO);
  const usuario = userEvent.setup();
  montar();

  await usuario.click(await screen.findByRole("checkbox", { name: /Auxilio funerario/ }));
  const suma = screen.getByLabelText("Suma asegurada de Auxilio funerario");
  await usuario.clear(suma);
  await usuario.type(suma, "5000000");
  await usuario.click(screen.getByRole("button", { name: "Calcular ajuste de prima" }));

  expect(simularEndoso).toHaveBeenCalledWith("POL-1", {
    coberturas_opcionales: [{ codigo: "AUXILIO_FUNERARIO", suma_asegurada: "5000000" }],
    beneficiarios: [],
  });
  expect(await screen.findByText("Se incluye Auxilio funerario.")).toBeInTheDocument();
  expect(screen.getByText("Cobro adicional")).toBeInTheDocument();
  expect(screen.getByText(/183 de 365 días/)).toBeInTheDocument();

  const emitir = screen.getByRole("button", { name: "Confirmar y emitir endoso" });
  expect(emitir).toBeDisabled();
  await usuario.click(screen.getByRole("checkbox", { name: /Acepto estos cambios/ }));
  vi.mocked(listarEndosos).mockResolvedValue([ENDOSO]);
  await usuario.click(emitir);

  const [, , clave] = vi.mocked(confirmarEndoso).mock.calls[0];
  expect(clave).toBeTruthy();
  expect(await screen.findByText(/Emitimos el endoso No. 1/)).toBeInTheDocument();
  await usuario.click(screen.getByRole("button", { name: /Descargar endoso \(PDF\)/ }));
  expect(descargarEndoso).toHaveBeenCalledWith("POL-1", "END-1-001");
  expect(screen.getByText("Endoso No. 1 · Coberturas")).toBeInTheDocument();
});

it("editar después de calcular obliga a recalcular", async () => {
  vi.mocked(simularEndoso).mockResolvedValue(PROPUESTA);
  const usuario = userEvent.setup();
  montar();

  await usuario.click(await screen.findByRole("checkbox", { name: /Auxilio funerario/ }));
  await usuario.click(screen.getByRole("button", { name: "Calcular ajuste de prima" }));
  expect(await screen.findByText("Revisa los cambios")).toBeInTheDocument();

  await usuario.click(screen.getByRole("checkbox", { name: /Incapacidad total/ }));

  expect(screen.queryByText("Revisa los cambios")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Calcular ajuste de prima" })).toBeEnabled();
});

it("controla que los porcentajes de los beneficiarios sumen 100", async () => {
  const usuario = userEvent.setup();
  montar();

  await usuario.click(await screen.findByRole("button", { name: "Agregar beneficiario" }));
  const primero = screen.getByRole("group", { name: "Beneficiario 1" });
  await usuario.type(within(primero).getByLabelText("Nombre completo"), "Mateo Gómez");
  await usuario.type(within(primero).getByLabelText("Documento"), "1098765432");
  await usuario.type(within(primero).getByLabelText("Parentesco"), "Hijo");
  await usuario.type(within(primero).getByLabelText("Porcentaje"), "60");

  expect(screen.getByText("Suman 60 %")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Calcular ajuste de prima" })).toBeDisabled();

  await usuario.click(screen.getByRole("button", { name: "Agregar beneficiario" }));
  const segundo = screen.getByRole("group", { name: "Beneficiario 2" });
  await usuario.type(within(segundo).getByLabelText("Porcentaje"), "40");

  expect(screen.getByText("Suman 100 %")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Calcular ajuste de prima" })).toBeEnabled();

  await usuario.click(screen.getByRole("button", { name: "Quitar beneficiario 2" }));
  expect(screen.queryByRole("group", { name: "Beneficiario 2" })).not.toBeInTheDocument();
});

it("muestra el mensaje del servidor cuando rechaza la solicitud", async () => {
  vi.mocked(simularEndoso).mockRejectedValue(
    new ErrorEndoso("La solicitud no cambia nada de la póliza.", "SIN_CAMBIOS", 422),
  );
  const usuario = userEvent.setup();
  montar();

  await usuario.click(await screen.findByRole("button", { name: "Calcular ajuste de prima" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("La solicitud no cambia nada de la póliza.");
});

it("no ofrece beneficiarios en seguros que no los admiten", async () => {
  vi.mocked(obtenerOpciones).mockResolvedValue({ ...OPCIONES, admite_beneficiarios: false });
  montar();

  expect(await screen.findByText("Coberturas opcionales")).toBeInTheDocument();
  expect(screen.queryByText("Beneficiarios")).not.toBeInTheDocument();
});

it("una póliza no vigente se muestra sin permitir cambios", async () => {
  vi.mocked(obtenerOpciones).mockResolvedValue({ ...OPCIONES, estado: "VENCIDA", modificable: false });
  montar();

  expect(await screen.findByText(/ya no está vigente/)).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: /Auxilio funerario/ })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Calcular ajuste de prima" })).toBeDisabled();
});

it("lista el historial de endosos con su descarga", async () => {
  vi.mocked(listarEndosos).mockResolvedValue([{ ...ENDOSO, concepto_ajuste: "DEVOLUCION", ajuste_prima: "-9150.00" }]);
  const usuario = userEvent.setup();
  montar();

  expect(await screen.findByText("Endoso No. 1 · Coberturas")).toBeInTheDocument();
  expect(screen.getByText(/Devolución a tu favor/)).toBeInTheDocument();
  await usuario.click(screen.getByRole("button", { name: "Descargar endoso No. 1" }));
  expect(descargarEndoso).toHaveBeenCalledWith("POL-1", "END-1-001");
});

it("informa si no puede cargar la póliza", async () => {
  vi.mocked(obtenerOpciones).mockRejectedValue(new Error("La póliza no existe."));
  montar();

  expect(await screen.findByRole("alert")).toHaveTextContent("La póliza no existe.");
});

import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { cerrarSesion } from "../services/session";
import { obtenerPerfil } from "../services/auth.service";
import { obtenerBilletera } from "../services/billetera.service";
import { obtenerHistorialPoliza } from "../services/historial-poliza.service";
import HomePage from "./HomePage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));
vi.mock("../services/asesor.service", () => ({
  listarClientesDeAsesor: vi.fn().mockResolvedValue([]),
  asociarCliente: vi.fn(),
}));
vi.mock("../services/billetera.service", () => ({
  obtenerBilletera: vi.fn(),
}));
vi.mock("../services/historial-poliza.service", () => ({
  obtenerHistorialPoliza: vi.fn(),
}));
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerBilletera).mockResolvedValue({
    polizas: [], total_vigentes: 0, total_inactivas: 0,
  });
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue({
    poliza_id: "p1", numero_poliza: "SOL-0001", movimientos: [],
  });
});

function inicio() {
  render(<MemoryRouter initialEntries={["/home"]}><Routes>
    <Route path="/home" element={<HomePage />} />
    <Route path="/login" element={<h1>Inicia sesión</h1>} />
    <Route path="/admin/socios/nuevo" element={<h1>Registro de socio</h1>} />
<<<<<<< Updated upstream
    <Route path="/admin/asesores/nuevo" element={<h1>Crear asesor</h1>} />
=======
    <Route path="/polizas/:polizaId/historial" element={<h1>Historial de la póliza</h1>} />
>>>>>>> Stashed changes
  </Routes></MemoryRouter>);
}

it("el manager puede abrir el formulario de creación de asesor", async () => {
  vi.mocked(obtenerPerfil).mockResolvedValue({ rol: "SERVICIO_INTERNO" });
  inicio();
  await userEvent.click(await screen.findByRole("button", { name: "Crear un asesor de ventas" }));
  expect(await screen.findByRole("heading", { name: "Crear asesor" })).toBeInTheDocument();
});

it.each(["CLIENTE", "ASESOR_VENTAS", "INGENIERO_INTEGRACIONES", "ANALISTA_RIESGOS"])(
  "%s no ve el botón de crear asesor", async (rol) => {
    vi.mocked(obtenerPerfil).mockResolvedValue({ rol });
    inicio();
    await screen.findByRole("heading", { name: "Hola" });
    expect(
      screen.queryByRole("button", { name: "Crear un asesor de ventas" }),
    ).not.toBeInTheDocument();
  },
);

it.each(["INGENIERO_INTEGRACIONES", "SERVICIO_INTERNO"])(
  "%s puede abrir el formulario de socios", async (rol) => {
    vi.mocked(obtenerPerfil).mockResolvedValue({ rol });
    inicio();
    await userEvent.click(await screen.findByRole("button", { name: "Crear un nuevo socio" }));
    expect(await screen.findByRole("heading", { name: "Registro de socio" })).toBeInTheDocument();
  },
);

it.each(["CLIENTE", "ASESOR_VENTAS", "ANALISTA_RIESGOS", "SOCIO_DISTRIBUCION"])(
  "%s conserva Home sin el botón de socios", async (rol) => {
    let resolver!: (perfil: { rol: string }) => void;
    vi.mocked(obtenerPerfil).mockReturnValue(new Promise((resolve) => { resolver = resolve; }));
    inicio();
    await act(async () => { resolver({ rol }); });
    expect(screen.getByRole("heading", { name: "Hola" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Crear un nuevo socio" })).not.toBeInTheDocument();
  },
);

it("requiere iniciar sesión si no puede validar el perfil", async () => {
  vi.mocked(obtenerPerfil).mockRejectedValue(new Error("Sesión expirada"));
  inicio();
  expect(await screen.findByRole("heading", { name: "Inicia sesión" })).toBeInTheDocument();
});


it("cierra sesión y vuelve al login", async () => {
  vi.mocked(obtenerPerfil).mockResolvedValue({ rol: "CLIENTE" });
  vi.mocked(cerrarSesion).mockResolvedValue();
  inicio();
  await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));
  expect(await screen.findByRole("heading", { name: "Inicia sesión" })).toBeInTheDocument();
  expect(cerrarSesion).toHaveBeenCalledOnce();
});

it("permite reintentar logout si el servidor no confirma el cierre", async () => {
  vi.mocked(obtenerPerfil).mockResolvedValue({ rol: "CLIENTE" });
  vi.mocked(cerrarSesion).mockRejectedValueOnce(new Error("Sin conexión")).mockResolvedValue();
  inicio();
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("No fue posible cerrar la sesión");
  expect(screen.getByRole("heading", { name: "Hola" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));
  expect(await screen.findByRole("heading", { name: "Inicia sesión" })).toBeInTheDocument();
});

it("informa un acceso denegado desde una ruta restringida", async () => {
  vi.mocked(obtenerPerfil).mockResolvedValue({ rol: "CLIENTE" });
  await act(async () => {
    render(<MemoryRouter initialEntries={[{ pathname: "/home", state: { accesoDenegado: true } }]}>
      <HomePage />
    </MemoryRouter>);
  });
  expect(screen.getByRole("alert")).toHaveTextContent("No tienes permiso");
});

it("saluda al cliente por su nombre y muestra su póliza activa", async () => {
  vi.mocked(obtenerPerfil).mockResolvedValue({ rol: "CLIENTE", nombre: "María", apellido: "Torres" });
  vi.mocked(obtenerBilletera).mockResolvedValue({
    total_vigentes: 1,
    total_inactivas: 0,
    polizas: [{
      poliza_id: "p1", numero_poliza: "SOLV-VH-2026-004821", ramo: "VIDA",
      nombre_ramo: "Vida hipotecario", estado: "VIGENTE", activa: true,
      fecha_inicio: "2026-09-17", fecha_fin: "2027-09-17", cobertura_principal: "Vida",
      emitida_en: "2026-09-17T12:00:00Z",
    }],
  });
  inicio();
  expect(await screen.findByRole("heading", { name: "Hola, María" })).toBeInTheDocument();
  expect(await screen.findByText("Vida hipotecario")).toBeInTheDocument();
  expect(screen.getByText("SOLV-VH-2026-004821")).toBeInTheDocument();
});

const POLIZA_CLIENTE = {
  poliza_id: "p1", numero_poliza: "SOLV-VH-2026-004821", ramo: "VIDA",
  nombre_ramo: "Vida hipotecario", estado: "VIGENTE", activa: true,
  fecha_inicio: "2026-09-17", fecha_fin: "2027-09-17", cobertura_principal: "Vida",
  emitida_en: "2026-09-17T12:00:00Z",
};

it("muestra los movimientos recientes del historial en la página de inicio", async () => {
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "CLI-1", rol: "CLIENTE" });
  vi.mocked(obtenerBilletera).mockResolvedValue({
    total_vigentes: 1, total_inactivas: 0, polizas: [POLIZA_CLIENTE],
  });
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue({
    poliza_id: "p1",
    numero_poliza: "SOLV-VH-2026-004821",
    movimientos: [
      {
        movimiento_id: "PAY-001", poliza_id: "p1", categoria: "FINANCIERO",
        tipo: "PAGO_PRIMA_INICIAL", fecha: "2026-10-20T13:45:00Z",
        descripcion: "Pago de prima inicial", referencia: "PAY-001",
        referencia_externa: "PSP-88910", estado: "APROBADO", monto: "125000.00",
        moneda: "COP", naturaleza_monto: "COBRO", cambios: [], consentimiento: null,
      },
    ],
  });
  inicio();

  expect(await screen.findByText("Pago de prima inicial")).toBeInTheDocument();
  expect(screen.getByText("APROBADO")).toBeInTheDocument();
  // El cobro se muestra en negativo (ignora separadores y símbolos).
  const fila = screen.getByText("Pago de prima inicial").closest("tr") as HTMLElement;
  expect(fila.textContent?.replace(/[\s$.]/g, "")).toContain("-125000");
});

it("abre el historial completo de la póliza al hacer clic en un movimiento", async () => {
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "CLI-1", rol: "CLIENTE" });
  vi.mocked(obtenerBilletera).mockResolvedValue({
    total_vigentes: 1, total_inactivas: 0, polizas: [POLIZA_CLIENTE],
  });
  vi.mocked(obtenerHistorialPoliza).mockResolvedValue({
    poliza_id: "p1",
    numero_poliza: "SOLV-VH-2026-004821",
    movimientos: [
      {
        movimiento_id: "p1-EMISION", poliza_id: "p1", categoria: "POLIZA",
        tipo: "EMISION", fecha: "2026-09-17T12:00:00Z", descripcion: "Póliza emitida",
        referencia: "SOLV-VH-2026-004821", referencia_externa: null, estado: "COMPLETADO",
        monto: null, moneda: null, naturaleza_monto: null, cambios: [], consentimiento: null,
      },
    ],
  });
  inicio();

  await userEvent.click(await screen.findByRole("button", { name: /Ver historial de Vida hipotecario/ }));
  expect(await screen.findByRole("heading", { name: "Historial de la póliza" })).toBeInTheDocument();
});

it("indica cuando no hay movimientos recientes", async () => {
  vi.mocked(obtenerPerfil).mockResolvedValue({ id: "CLI-1", rol: "CLIENTE" });
  vi.mocked(obtenerBilletera).mockResolvedValue({
    total_vigentes: 0, total_inactivas: 0, polizas: [],
  });
  inicio();
  expect(await screen.findByText("Todavía no hay movimientos.")).toBeInTheDocument();
});

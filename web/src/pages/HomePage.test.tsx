import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { cerrarSesion } from "../services/session";
import { obtenerPerfil } from "../services/auth.service";
import { obtenerBilletera } from "../services/billetera.service";
import HomePage from "./HomePage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));
vi.mock("../services/billetera.service", () => ({
  obtenerBilletera: vi.fn().mockResolvedValue({ polizas: [], total_vigentes: 0, total_inactivas: 0 }),
}));
beforeEach(() => vi.clearAllMocks());

function inicio() {
  render(<MemoryRouter initialEntries={["/home"]}><Routes>
    <Route path="/home" element={<HomePage />} />
    <Route path="/login" element={<h1>Inicia sesión</h1>} />
    <Route path="/admin/socios/nuevo" element={<h1>Registro de socio</h1>} />
  </Routes></MemoryRouter>);
}

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
    }],
  });
  inicio();
  expect(await screen.findByRole("heading", { name: "Hola, María" })).toBeInTheDocument();
  expect(await screen.findByText("Vida hipotecario")).toBeInTheDocument();
  expect(screen.getByText("SOLV-VH-2026-004821")).toBeInTheDocument();
});

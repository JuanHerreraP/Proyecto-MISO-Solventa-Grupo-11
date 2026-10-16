import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import App from "./App";
import { obtenerPerfil } from "./services/auth.service";
import { restaurarSesion } from "./services/session";

vi.mock("./services/session", async (original) => ({
  ...await original<typeof import("./services/session")>(),
  restaurarSesion: vi.fn(), iniciarControlSesion: vi.fn(() => vi.fn()),
}));
vi.mock("./pages/HomePage", () => ({ default: () => <h1>Inicio restaurado</h1> }));
vi.mock("./services/auth.service", async (original) => ({
  ...await original<typeof import("./services/auth.service")>(), obtenerPerfil: vi.fn(),
}));
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(obtenerPerfil).mockResolvedValue({ rol: "CLIENTE" });
});

it("espera la restauración antes de montar la página de inicio", async () => {
  let terminar!: (valor: boolean) => void;
  vi.mocked(restaurarSesion).mockReturnValue(new Promise((resolve) => { terminar = resolve; }));
  render(<MemoryRouter initialEntries={["/home"]}><App /></MemoryRouter>);
  expect(screen.getByRole("status")).toHaveTextContent("Cargando sesión");
  expect(screen.queryByRole("heading", { name: "Inicio restaurado" })).not.toBeInTheDocument();
  await act(async () => terminar(true));
  expect(await screen.findByRole("heading", { name: "Inicio restaurado" })).toBeInTheDocument();
});

it("permite acceder al login cuando no hay cookie de sesión", async () => {
  vi.mocked(restaurarSesion).mockResolvedValue(false);
  render(<MemoryRouter initialEntries={["/login"]}><App /></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Inicia sesión" })).toBeInTheDocument();
});

it("no intenta restaurar otra vez después de cerrar o expirar la sesión", async () => {
  vi.mocked(restaurarSesion).mockResolvedValue(true);
  render(<MemoryRouter initialEntries={["/home"]}><App /></MemoryRouter>);
  await screen.findByRole("heading", { name: "Inicio restaurado" });
  await act(async () => window.dispatchEvent(new Event("sesion-expirada")));
  expect(await screen.findByRole("heading", { name: "Inicia sesión" })).toBeInTheDocument();
  expect(restaurarSesion).toHaveBeenCalledOnce();
});

vi.mock("./pages/SocioRegistrationPage", () => ({
  default: vi.fn(() => <h1>Crear socio protegido</h1>),
}));

it.each(["INGENIERO_INTEGRACIONES", "SERVICIO_INTERNO"])(
  "%s puede entrar directamente a la ruta de socios", async (rol) => {
    vi.mocked(restaurarSesion).mockResolvedValue(true);
    vi.mocked(obtenerPerfil).mockResolvedValue({ rol });
    render(<MemoryRouter initialEntries={["/admin/socios/nuevo"]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Crear socio protegido" })).toBeInTheDocument();
  },
);

it.each(["CLIENTE", "ASESOR_VENTAS", "ANALISTA_RIESGOS", "OPERACIONES_SINIESTROS", "SOCIO_DISTRIBUCION"])(
  "%s no monta el formulario escribiendo la URL", async (rol) => {
    const { default: formulario } = await import("./pages/SocioRegistrationPage");
    vi.mocked(restaurarSesion).mockResolvedValue(true);
    vi.mocked(obtenerPerfil).mockResolvedValue({ rol });
    render(<MemoryRouter initialEntries={["/admin/socios/nuevo"]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Inicio restaurado" })).toBeInTheDocument();
    expect(formulario).not.toHaveBeenCalled();
  },
);

it.each(["/home", "/admin/socios/nuevo"])(
  "sin sesión redirige %s al login", async (ruta) => {
    vi.mocked(restaurarSesion).mockResolvedValue(false);
    vi.mocked(obtenerPerfil).mockRejectedValue(new Error("Inicia sesión"));
    render(<MemoryRouter initialEntries={[ruta]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Inicia sesión" })).toBeInTheDocument();
  },
);

it("no monta la pantalla de socios mientras verifica los permisos", async () => {
  const { default: formulario } = await import("./pages/SocioRegistrationPage");
  vi.mocked(restaurarSesion).mockResolvedValue(true);
  let terminar!: (perfil: { rol: string }) => void;
  vi.mocked(obtenerPerfil).mockReturnValue(new Promise((resolve) => { terminar = resolve; }));
  render(<MemoryRouter initialEntries={["/admin/socios/nuevo"]}><App /></MemoryRouter>);
  expect(await screen.findByText("Verificando acceso…")).toBeInTheDocument();
  expect(formulario).not.toHaveBeenCalled();
  await act(async () => terminar({ rol: "SERVICIO_INTERNO" }));
  expect(await screen.findByRole("heading", { name: "Crear socio protegido" })).toBeInTheDocument();
});


it("vuelve a validar el rol cuando cambia de una ruta protegida a otra", async () => {
  const { default: formulario } = await import("./pages/SocioRegistrationPage");
  vi.mocked(restaurarSesion).mockResolvedValue(true);
  vi.mocked(obtenerPerfil).mockResolvedValue({ rol: "SERVICIO_INTERNO" });
  render(<MemoryRouter initialEntries={["/home"]}>
    <Link to="/admin/socios/nuevo">Abrir socios</Link><App />
  </MemoryRouter>);
  await screen.findByRole("heading", { name: "Inicio restaurado" });
  vi.mocked(obtenerPerfil).mockResolvedValue({ rol: "CLIENTE" });
  await userEvent.click(screen.getByRole("link", { name: "Abrir socios" }));
  expect(await screen.findByRole("heading", { name: "Inicio restaurado" })).toBeInTheDocument();
  expect(formulario).not.toHaveBeenCalled();
  expect(obtenerPerfil).toHaveBeenCalledTimes(3);
});

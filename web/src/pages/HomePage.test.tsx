import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import HomePage from "./HomePage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
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
    expect(screen.getByRole("heading", { name: "Home" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Crear un nuevo socio" })).not.toBeInTheDocument();
  },
);

it("requiere iniciar sesión si no puede validar el perfil", async () => {
  vi.mocked(obtenerPerfil).mockRejectedValue(new Error("Sesión expirada"));
  inicio();
  expect(await screen.findByRole("heading", { name: "Inicia sesión" })).toBeInTheDocument();
});

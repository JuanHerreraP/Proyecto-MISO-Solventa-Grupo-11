import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerPerfil } from "../services/auth.service";
import ProfilePage from "./ProfilePage";

vi.mock("../services/auth.service", () => ({ obtenerPerfil: vi.fn() }));
vi.mock("../services/session", () => ({ cerrarSesion: vi.fn() }));

beforeEach(() => {
  vi.mocked(obtenerPerfil).mockResolvedValue({
    id: "CLI-1",
    nombre: "María",
    apellido: "Solano",
    email: "maria@correo.com",
    rol: "CLIENTE",
    tipo_documento: "CC",
    numero_documento: "1020456789",
    celular: "3001234567",
  });
});

it("muestra los datos y preferencias disponibles", async () => {
  render(<MemoryRouter><ProfilePage /></MemoryRouter>);

  expect((await screen.findAllByText("María Solano")).length).toBeGreaterThan(0);
  expect(screen.getByText("Cliente")).toBeInTheDocument();
  expect(screen.getByText("CC 1020456789")).toBeInTheDocument();
  expect(screen.getByText("3001234567")).toBeInTheDocument();
  expect(screen.getByText("Peso colombiano (COP)")).toBeInTheDocument();
  expect(screen.getByText("Disponible próximamente")).toBeInTheDocument();
});

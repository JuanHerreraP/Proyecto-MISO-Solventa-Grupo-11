import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { crearAnalistaCumplimiento } from "../services/auditor.service";
import AuditorRegistrationPage from "./AuditorRegistrationPage";

vi.mock("../services/auditor.service", () => ({ crearAnalistaCumplimiento: vi.fn() }));

function montar() {
  return render(
    <MemoryRouter>
      <AuditorRegistrationPage />
    </MemoryRouter>,
  );
}

async function llenarFormulario(password: string, confirmar: string) {
  await userEvent.type(screen.getByLabelText("Nombre"), "María");
  await userEvent.type(screen.getByLabelText("Apellido"), "Torres");
  await userEvent.type(screen.getByLabelText("Número de documento"), "1012345678");
  await userEvent.type(screen.getByLabelText("Fecha de nacimiento"), "1990-01-01");
  await userEvent.type(screen.getByLabelText("Correo corporativo"), "maria@solventa.com");
  await userEvent.type(screen.getByLabelText("Contraseña"), password);
  await userEvent.type(screen.getByLabelText("Confirmar contraseña"), confirmar);
}

beforeEach(() => {
  vi.clearAllMocks();
});

it("crea el analista y muestra la confirmación con el rol", async () => {
  vi.mocked(crearAnalistaCumplimiento).mockResolvedValue({
    id: "u1",
    nombre: "María",
    apellido: "Torres",
    email: "maria@solventa.com",
    rol: "ANALISTA_CUMPLIMIENTO",
    kyc_validado: true,
    fecha_creacion: "2026-11-08T00:00:00Z",
  });

  montar();
  await llenarFormulario("Password123!", "Password123!");
  await userEvent.click(screen.getByRole("button", { name: /Crear analista/ }));

  expect(await screen.findByText("Analista creado correctamente")).toBeInTheDocument();
  expect(screen.getByText("ANALISTA_CUMPLIMIENTO")).toBeInTheDocument();
  expect(crearAnalistaCumplimiento).toHaveBeenCalledWith(
    expect.objectContaining({ email: "maria@solventa.com" }),
  );
});

it("valida que las contraseñas coincidan sin llamar al servicio", async () => {
  montar();
  await llenarFormulario("Password123!", "Otra123456");
  await userEvent.click(screen.getByRole("button", { name: /Crear analista/ }));

  expect(await screen.findByText("Las contraseñas no coinciden.")).toBeInTheDocument();
  expect(crearAnalistaCumplimiento).not.toHaveBeenCalled();
});

it("muestra el error devuelto por el servicio", async () => {
  vi.mocked(crearAnalistaCumplimiento).mockRejectedValue(
    new Error("Ya existe un usuario con ese correo."),
  );
  montar();
  await llenarFormulario("Password123!", "Password123!");
  await userEvent.click(screen.getByRole("button", { name: /Crear analista/ }));

  expect(await screen.findByText("Ya existe un usuario con ese correo.")).toBeInTheDocument();
});

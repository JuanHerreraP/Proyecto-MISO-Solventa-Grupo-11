import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { obtenerCuenta, registrarCuenta } from "../../services/desembolsos.service";
import CuentaIndemnizaciones from "./CuentaIndemnizaciones";

vi.mock("../../services/desembolsos.service", async (original) => ({
  ...(await original<typeof import("../../services/desembolsos.service")>()),
  obtenerCuenta: vi.fn(),
  registrarCuenta: vi.fn(),
}));

const CUENTA = {
  codigo_banco: "1007", nombre_banco: "Bancolombia", tipo_cuenta: "AHORROS" as const,
  ultimos_digitos: "1234", actualizada_en: "2026-11-07T15:00:00Z",
};

beforeEach(() => vi.clearAllMocks());

it("sin cuenta pide registrarla y valida el número", async () => {
  vi.mocked(obtenerCuenta).mockResolvedValue(null);
  vi.mocked(registrarCuenta).mockResolvedValue(CUENTA);
  const usuario = userEvent.setup();
  render(<CuentaIndemnizaciones />);

  const numero = await screen.findByLabelText("Número de cuenta");
  const guardar = screen.getByRole("button", { name: "Guardar cuenta" });
  await usuario.type(numero, "12");
  expect(guardar).toBeDisabled();
  await usuario.type(numero, "34-56789 1234");
  await usuario.click(guardar);

  expect(registrarCuenta).toHaveBeenCalledWith({
    codigo_banco: "1007", tipo_cuenta: "AHORROS", numero_cuenta: "1234567891234",
  });
  expect(await screen.findByText(/Bancolombia · Ahorros · \*\*\*\*1234/)).toBeInTheDocument();
});

it("con cuenta muestra solo los últimos dígitos y permite cambiarla", async () => {
  vi.mocked(obtenerCuenta).mockResolvedValue(CUENTA);
  const usuario = userEvent.setup();
  render(<CuentaIndemnizaciones />);

  expect(await screen.findByText(/\*\*\*\*1234/)).toBeInTheDocument();
  await usuario.click(screen.getByRole("button", { name: "Cambiar cuenta" }));
  expect(screen.getByLabelText("Número de cuenta")).toHaveValue("");
  await usuario.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(screen.getByText(/\*\*\*\*1234/)).toBeInTheDocument();
});

it("muestra el error del servidor", async () => {
  vi.mocked(obtenerCuenta).mockResolvedValue(null);
  vi.mocked(registrarCuenta).mockRejectedValue(new Error("El banco no está habilitado."));
  const usuario = userEvent.setup();
  render(<CuentaIndemnizaciones />);

  await usuario.type(await screen.findByLabelText("Número de cuenta"), "12345678");
  await usuario.click(screen.getByRole("button", { name: "Guardar cuenta" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("El banco no está habilitado.");
});

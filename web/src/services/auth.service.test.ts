import { afterEach, describe, expect, it, vi } from "vitest";
import { login, register } from "./auth.service";

const credenciales = { email: "maria@solventa.com", password: "Password123!" };
const solicitud = { ...credenciales, nombre: "Maria", apellido: "Torres", tipo_documento: "CC",
  numero_documento: "123456789", fecha_nacimiento: "1995-06-15", acepta_validacion_identidad: true };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
function simular(respuesta: Response) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    String(url).endsWith("/csrf") ? json({ csrf_token: "reto-csrf" }) : respuesta.clone());
}
afterEach(() => vi.restoreAllMocks());

describe("auth.service", () => {
  it("login usa cookie de sesión y cabecera CSRF", async () => {
    const fetch = simular(json({ access_token: "access-token", csrf_token: "csrf", token_type: "bearer", expires_in: 1800 }));
    await login(credenciales);
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/v1/auth/web/login"),
      expect.objectContaining({ method: "POST", credentials: "include", headers: {
        "Content-Type": "application/json", "X-CSRF-Token": "reto-csrf",
      }, body: JSON.stringify(credenciales) }));
  });

  it.each([
    [{ detail: { mensaje: "Credenciales incorrectas." } }, "Credenciales incorrectas."],
    [{ detail: "Credenciales inválidas." }, "Credenciales inválidas."],
    [{}, "Ocurrió un error al procesar la solicitud."],
  ])("muestra el error de login del backend", async (body, mensaje) => {
    simular(json(body, 401));
    await expect(login(credenciales)).rejects.toThrow(mensaje as string);
  });

  it("registro conserva su contrato público", async () => {
    const fetch = simular(json({ id: "usuario-123" }, 201));
    await register(solicitud);
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/v1/auth/register"),
      expect.objectContaining({ method: "POST", body: JSON.stringify(solicitud) }));
  });

  it.each([
    [{ detail: "Ya existe un usuario registrado con este correo." }, "Ya existe un usuario registrado con este correo."],
    [{ error: "Internal server error" }, "Ocurrió un error al procesar la solicitud."],
  ])("muestra errores de registro", async (body, mensaje) => {
    simular(json(body, 409));
    await expect(register(solicitud)).rejects.toThrow(mensaje as string);
  });

  it("maneja respuestas inválidas", async () => {
    simular(new Response("respuesta-no-json", { status: 500 }));
    await expect(register(solicitud)).rejects.toThrow("No fue posible comunicarse correctamente con el servidor.");
  });
});

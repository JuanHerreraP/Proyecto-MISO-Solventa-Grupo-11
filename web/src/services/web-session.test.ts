import { afterEach, expect, it, vi } from "vitest";
import { conBloqueoSesion, postSesionWeb } from "./web-session";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("no envía credenciales si falla la obtención del reto CSRF", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 403 }));
  await expect(postSesionWeb("login", { password: "secreto" })).rejects.toThrow("validar la sesión");
  expect(fetch).toHaveBeenCalledOnce();
});

it.each([undefined, "", 42])("rechaza un reto CSRF inválido (%s)", async (csrf_token) => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ csrf_token })));
  await expect(postSesionWeb("refresh")).rejects.toThrow("Reto CSRF inválido");
  expect(fetch).toHaveBeenCalledOnce();
});

it("no continúa si el servidor devuelve un reto que no es JSON", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("no-json"));
  await expect(postSesionWeb("logout")).rejects.toThrow();
  expect(fetch).toHaveBeenCalledOnce();
});

it("utiliza Web Locks cuando el navegador los ofrece", async () => {
  const accion = vi.fn(async () => "resultado");
  const request = vi.fn(async (_nombre: string, callback: () => Promise<string>) => callback());
  vi.stubGlobal("navigator", { locks: { request } });
  expect(await conBloqueoSesion(accion)).toBe("resultado");
  expect(request).toHaveBeenCalledWith("solventa-sesion-web", accion);
  expect(accion).toHaveBeenCalledOnce();
});

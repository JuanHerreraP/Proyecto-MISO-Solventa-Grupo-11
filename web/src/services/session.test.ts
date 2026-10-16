import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cerrarSesion, fetchAutenticado, guardarAccessToken, guardarSesion, iniciarControlSesion, obtenerAccessToken, restaurarSesion } from "./session";

const sesion = { access_token: "access-1", csrf_token: "csrf-1", expires_in: 1800, token_type: "bearer" };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
function simular(responder: (url: string) => Response | Promise<Response>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    if (String(url).endsWith("/csrf")) return json({ csrf_token: "reto-csrf" });
    if (String(url).endsWith("/logout")) return new Response(null, { status: 204 });
    return responder(String(url));
  });
}
let detener: (() => void) | undefined;
beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-16T12:00:00Z"));
  guardarSesion(sesion);
});
afterEach(async () => {
  detener?.();
  detener = undefined;
  guardarAccessToken(null);
  await vi.advanceTimersByTimeAsync(0);
  vi.restoreAllMocks();
  vi.useRealTimers();
});

it("renueva con cookies y CSRF sin enviar un refresh en el cuerpo", async () => {
  vi.setSystemTime(Date.now() + 29 * 60_000);
  const fetch = simular((url) => url.endsWith("/refresh")
    ? json({ ...sesion, access_token: "access-2" }) : json({ ok: true }));
  await fetchAutenticado("/protegido");
  const refresh = fetch.mock.calls.find(([url]) => String(url).endsWith("/refresh"))!;
  expect(refresh[1]).toMatchObject({ credentials: "include", headers: { "X-CSRF-Token": "reto-csrf" } });
  expect(refresh[1]?.body).toBeUndefined();
  expect(fetch.mock.calls.at(-1)?.[1]).toMatchObject({
    credentials: "omit", headers: { authorization: "Bearer access-2" },
  });
});

it("comparte la renovación entre peticiones concurrentes", async () => {
  vi.setSystemTime(Date.now() + 29 * 60_000);
  const fetch = simular((url) => url.endsWith("/refresh")
    ? json({ ...sesion, access_token: "access-2" }) : json({ ok: true }));
  await Promise.all([fetchAutenticado("/uno"), fetchAutenticado("/dos")]);
  expect(fetch.mock.calls.filter(([url]) => String(url).endsWith("/refresh"))).toHaveLength(1);
});

it("reintenta una sola vez tras TOKEN_EXPIRED", async () => {
  let intento = 0;
  const fetch = simular((url) => {
    if (url.endsWith("/refresh")) return json({ ...sesion, access_token: "access-2" });
    return ++intento === 1 ? json({ detail: { codigo: "TOKEN_EXPIRED" } }, 401) : json({ ok: true });
  });
  expect((await fetchAutenticado("/protegido")).status).toBe(200);
  expect(fetch.mock.calls.filter(([url]) => url === "/protegido")).toHaveLength(2);
});

it("30 minutos sin interacción cierran sesión sin renovar", async () => {
  const expirada = vi.fn();
  window.addEventListener("sesion-expirada", expirada, { once: true });
  const fetch = simular(() => json({}));
  detener = iniciarControlSesion();
  await vi.advanceTimersByTimeAsync(30 * 60_000);
  expect(obtenerAccessToken()).toBeNull();
  expect(expirada).toHaveBeenCalledOnce();
  expect(fetch.mock.calls.some(([url]) => String(url).endsWith("/refresh"))).toBe(false);
  expect(fetch.mock.calls.some(([url]) => String(url).endsWith("/logout"))).toBe(true);
});

it("la interacción mantiene la sesión y permite renovar", async () => {
  const fetch = simular((url) => url.endsWith("/refresh") ? json({ ...sesion, access_token: "access-2" }) : json({}));
  detener = iniciarControlSesion();
  for (let minuto = 0; minuto < 31; minuto++) {
    window.dispatchEvent(new Event("keydown"));
    await vi.advanceTimersByTimeAsync(60_000);
  }
  expect(obtenerAccessToken()).toBe("access-2");
  expect(fetch.mock.calls.some(([url]) => String(url).endsWith("/refresh"))).toBe(true);
});

it("una renovación rechazada limpia la sesión", async () => {
  vi.setSystemTime(Date.now() + 29 * 60_000);
  simular(() => json({}, 401));
  await expect(fetchAutenticado("/protegido")).rejects.toThrow("renovar");
  expect(obtenerAccessToken()).toBeNull();
});

it("un 403 de negocio conserva la sesión y no renueva", async () => {
  const fetch = simular(() => json({}, 403));
  expect((await fetchAutenticado("/protegido")).status).toBe(403);
  expect(fetch).toHaveBeenCalledOnce();
  expect(obtenerAccessToken()).toBe("access-1");
});

it("restaura la sesión al recargar sin almacenamiento de tokens en JavaScript", async () => {
  guardarAccessToken(null);
  simular(() => json(sesion));
  expect(await restaurarSesion()).toBe(true);
  expect(obtenerAccessToken()).toBe("access-1");
});

it("una recarga sin cookie no interrumpe las páginas públicas", async () => {
  guardarAccessToken(null);
  const evento = vi.fn();
  window.addEventListener("sesion-expirada", evento);
  simular(() => json({}, 401));
  expect(await restaurarSesion()).toBe(false);
  expect(evento).not.toHaveBeenCalled();
  window.removeEventListener("sesion-expirada", evento);
});

it("logout usa CSRF y limpia el token en memoria", async () => {
  const fetch = simular(() => json({}));
  await cerrarSesion();
  expect(obtenerAccessToken()).toBeNull();
  expect(fetch.mock.calls.at(-1)?.[1]).toMatchObject({ credentials: "include", headers: { "X-CSRF-Token": "reto-csrf" } });
});

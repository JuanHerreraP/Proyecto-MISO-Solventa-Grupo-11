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
  vi.unstubAllGlobals();
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

it("no restaura una sesión que ya tiene access token", async () => {
  const fetch = simular(() => json({}));
  expect(await restaurarSesion()).toBe(true);
  expect(fetch).not.toHaveBeenCalled();
});

it("logout fallido conserva la sesión para permitir reintentar", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    String(url).endsWith("/csrf") ? json({ csrf_token: "csrf" }) : json({}, 503));
  await expect(cerrarSesion()).rejects.toThrow("cerrar la sesión");
  expect(obtenerAccessToken()).toBe("access-1");
});

it("una petición sin sesión no llega a la red", async () => {
  guardarAccessToken(null);
  const fetch = simular(() => json({}));
  await expect(fetchAutenticado("/protegido")).rejects.toThrow("Inicia sesión");
  expect(fetch).not.toHaveBeenCalled();
});

it("no reactiva la sesión después de una suspensión superior a 30 minutos", async () => {
  const fetch = simular(() => json({}));
  detener = iniciarControlSesion();
  vi.setSystemTime(Date.now() + 31 * 60_000);
  window.dispatchEvent(new Event("pointerdown"));
  expect(obtenerAccessToken()).toBeNull();
  await expect(fetchAutenticado("/protegido")).rejects.toThrow("Inicia sesión");
  expect(fetch.mock.calls.some(([url]) => url === "/protegido")).toBe(false);
});

it("un 401 que no contiene JSON limpia la sesión sin renovar", async () => {
  const fetch = simular(() => new Response("no-json", { status: 401 }));
  expect((await fetchAutenticado("/protegido")).status).toBe(401);
  expect(obtenerAccessToken()).toBeNull();
  expect(fetch.mock.calls.some(([url]) => String(url).endsWith("/refresh"))).toBe(false);
});

it("un segundo 401 finaliza la sesión sin reintentos infinitos", async () => {
  const fetch = simular((url) => url.endsWith("/refresh")
    ? json(sesion) : json({ detail: { codigo: "TOKEN_EXPIRED" } }, 401));
  expect((await fetchAutenticado("/protegido")).status).toBe(401);
  expect(obtenerAccessToken()).toBeNull();
  expect(fetch.mock.calls.filter(([url]) => url === "/protegido")).toHaveLength(2);
});

it("una respuesta de refresh antigua no reemplaza una sesión nueva", async () => {
  let terminar!: (respuesta: Response) => void;
  const pendiente = new Promise<Response>((resolve) => { terminar = resolve; });
  const fetch = simular((url) => url.endsWith("/refresh") ? pendiente : json({}));
  vi.setSystemTime(Date.now() + 29 * 60_000);
  const peticion = fetchAutenticado("/protegido");
  await vi.waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).endsWith("/refresh"))).toBe(true));
  guardarSesion({ ...sesion, access_token: "nuevo-login" });
  const rechazada = expect(peticion).rejects.toThrow("La sesión cambió");
  terminar(json({ ...sesion, access_token: "respuesta-antigua" }));
  await rechazada;
  expect(obtenerAccessToken()).toBe("nuevo-login");
});

it("coordina un 401 recibido mientras otra petición está renovando", async () => {
  let devolverLenta!: (respuesta: Response) => void;
  let devolverRefresh!: (respuesta: Response) => void;
  const lenta = new Promise<Response>((resolve) => { devolverLenta = resolve; });
  const refresh = new Promise<Response>((resolve) => { devolverRefresh = resolve; });
  let intentosLenta = 0;
  const fetch = simular((url) => {
    if (url.endsWith("/refresh")) return refresh;
    if (url === "/lenta" && ++intentosLenta === 1) return lenta;
    return json({ ok: true });
  });
  const primera = fetchAutenticado("/lenta");
  vi.setSystemTime(Date.now() + 29 * 60_000);
  const segunda = fetchAutenticado("/rapida");
  await vi.waitFor(() => expect(fetch.mock.calls.some(([url]) => String(url).endsWith("/refresh"))).toBe(true));
  devolverLenta(json({ detail: { codigo: "SESSION_EXPIRED" } }, 401));
  await Promise.resolve();
  devolverRefresh(json({ ...sesion, access_token: "renovado" }));
  const respuestas = await Promise.all([primera, segunda]);
  expect(respuestas.every((respuesta) => respuesta.status === 200)).toBe(true);
  expect(fetch.mock.calls.filter(([url]) => String(url).endsWith("/refresh"))).toHaveLength(1);
});

class CanalSimulado {
  static ultimo: CanalSimulado;
  onmessage: ((event: MessageEvent) => void) | null = null;
  postMessage = vi.fn();
  close = vi.fn();
  constructor() { CanalSimulado.ultimo = this; }
  recibir(data: unknown) { this.onmessage?.({ data } as MessageEvent); }
}

it("comparte actividad entre pestañas y libera el canal al desmontar", async () => {
  vi.stubGlobal("BroadcastChannel", CanalSimulado);
  const fetch = simular((url) => url.endsWith("/refresh") ? json(sesion) : json({}));
  detener = iniciarControlSesion();
  const canal = CanalSimulado.ultimo;
  window.dispatchEvent(new Event("keydown"));
  expect(canal.postMessage).toHaveBeenCalledWith({ tipo: "actividad", cuando: Date.now() });
  vi.setSystemTime(Date.now() + 29 * 60_000);
  canal.recibir({ tipo: "actividad", cuando: Date.now() });
  canal.recibir({ tipo: "actividad", cuando: "inválido" });
  canal.recibir({ tipo: "desconocido" });
  await vi.advanceTimersByTimeAsync(2 * 60_000);
  expect(obtenerAccessToken()).toBe("access-1");
  detener();
  detener = undefined;
  expect(canal.close).toHaveBeenCalledOnce();
  const cantidad = fetch.mock.calls.length;
  window.dispatchEvent(new Event("scroll"));
  await vi.advanceTimersByTimeAsync(60_000);
  expect(fetch).toHaveBeenCalledTimes(cantidad);
});

it("el cierre en otra pestaña limpia la sesión sin enviar otro logout", async () => {
  vi.stubGlobal("BroadcastChannel", CanalSimulado);
  const fetch = simular(() => json({}));
  detener = iniciarControlSesion();
  CanalSimulado.ultimo.recibir({ tipo: "cerrada" });
  window.dispatchEvent(new Event("keydown"));
  await vi.advanceTimersByTimeAsync(15_000);
  expect(obtenerAccessToken()).toBeNull();
  expect(fetch).not.toHaveBeenCalled();
});

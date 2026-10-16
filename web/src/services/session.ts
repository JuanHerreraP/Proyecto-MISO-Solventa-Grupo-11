import { conBloqueoSesion, postSesionWeb } from "./web-session";
import type { LoginResponse } from "../types/auth";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const INACTIVIDAD_MS = 30 * 60 * 1000;
let accessToken: string | null = null;
let expiraEn = Infinity;
let ultimaActividad = Date.now();
let renovacion: Promise<void> | null = null;
let version = 0;
let canalSesion: BroadcastChannel | null = null;

export function guardarAccessToken(token: string | null): void {
  version++;
  accessToken = token;
  expiraEn = Infinity;
  ultimaActividad = Date.now();
}

export function guardarSesion(sesion: LoginResponse): void {
  guardarAccessToken(sesion.access_token);
  expiraEn = Date.now() + sesion.expires_in * 1000;
}

export function obtenerAccessToken(): string | null {
  return accessToken;
}

function expirarSesion(revocar = true): void {
  guardarAccessToken(null);
  canalSesion?.postMessage({ tipo: "cerrada" });
  window.dispatchEvent(new Event("sesion-expirada"));
  if (revocar) {
    void conBloqueoSesion(() => postSesionWeb("logout")).catch(() => undefined);
  }
}

export async function cerrarSesion(): Promise<void> {
  const respuesta = await conBloqueoSesion(() => postSesionWeb("logout"));
  if (!respuesta.ok) throw new Error("No fue posible cerrar la sesión en el servidor.");
  expirarSesion(false);
}

export async function restaurarSesion(): Promise<boolean> {
  if (accessToken) return true;
  try {
    await renovarSesion(true);
    return true;
  } catch {
    return false;
  }
}

function comprobarInactividad(): void {
  if (Date.now() - ultimaActividad >= INACTIVIDAD_MS) {
    expirarSesion();
    throw new Error("La sesión expiró por inactividad. Inicia sesión nuevamente.");
  }
}

async function renovarSesion(restaurando = false): Promise<void> {
  if (renovacion) return renovacion;
  comprobarInactividad();
  const actual = version;
  renovacion = (async () => {
    try {
      const respuesta = await conBloqueoSesion(() => postSesionWeb("refresh"));
      if (!respuesta.ok) throw new Error("No fue posible renovar la sesión.");
      const sesion: LoginResponse = await respuesta.json();
      if (actual !== version) throw new Error("La sesión cambió.");
      comprobarInactividad();
      accessToken = sesion.access_token;
      expiraEn = Date.now() + sesion.expires_in * 1000;
    } catch (error) {
      if (actual === version) {
        if (restaurando) guardarAccessToken(null);
        else expirarSesion();
      }
      throw error;
    } finally {
      renovacion = null;
    }
  })();
  return renovacion;
}

export async function fetchAutenticado(url: string, opciones: RequestInit = {}): Promise<Response> {
  comprobarInactividad();
  if (!accessToken) throw new Error("Inicia sesión para continuar.");
  if (Date.now() >= expiraEn - 60_000) await renovarSesion();
  const enviar = () => {
    const headers = new Headers(opciones.headers);
    headers.set("Authorization", `Bearer ${accessToken}`);
    return fetch(url, { ...opciones, credentials: "omit", headers: Object.fromEntries(headers.entries()) });
  };
  const tokenEnviado = accessToken;
  const respuesta = await enviar();
  if (respuesta.status !== 401) return respuesta;
  if (renovacion) await renovacion;
  const reintentar = async () => {
    const segundoIntento = await enviar();
    if (segundoIntento.status === 401) expirarSesion();
    return segundoIntento;
  };
  if (accessToken && accessToken !== tokenEnviado) return reintentar();
  const body = await respuesta.clone().json().catch(() => null);
  if (["TOKEN_EXPIRED", "SESSION_EXPIRED"].includes(body?.detail?.codigo)) {
    if (accessToken === tokenEnviado) await renovarSesion();
    return reintentar();
  }
  expirarSesion();
  return respuesta;
}

export function iniciarControlSesion(): () => void {
  let ultimaSincronizacion = Date.now();
  const canal = typeof window.BroadcastChannel === "function"
    ? new BroadcastChannel("solventa-actividad") : null;
  canalSesion = canal;
  if (canal) canal.onmessage = ({ data }) => {
    if (data?.tipo === "cerrada") {
      guardarAccessToken(null);
      window.dispatchEvent(new Event("sesion-expirada"));
    } else if (data?.tipo === "actividad" && accessToken && Number.isFinite(data.cuando)) {
      ultimaActividad = Math.max(ultimaActividad, Math.min(data.cuando, Date.now()));
    }
  };
  const actividad = () => {
    if (!accessToken) return;
    try { comprobarInactividad(); } catch { return; }
    ultimaActividad = Date.now();
    canal?.postMessage({ tipo: "actividad", cuando: ultimaActividad });
  };
  const eventos = ["pointerdown", "keydown", "scroll", "touchstart"];
  eventos.forEach((evento) => window.addEventListener(evento, actividad, { passive: true }));
  const timer = window.setInterval(() => {
    if (!accessToken) return;
    try { comprobarInactividad(); } catch { return; }
    // Solo sincroniza si hubo interacción: el temporizador no mantiene viva la sesión.
    if (ultimaActividad > ultimaSincronizacion) {
      ultimaSincronizacion = Date.now();
      void fetchAutenticado(`${API_URL}/api/v1/auth/me`).catch(() => undefined);
    }
  }, 15_000);
  return () => {
    clearInterval(timer);
    canal?.close();
    if (canalSesion === canal) canalSesion = null;
    eventos.forEach((evento) => window.removeEventListener(evento, actividad));
  };
}

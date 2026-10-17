const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// El navegador administra las cookies HttpOnly. JavaScript solo recibe el reto CSRF.
export async function postSesionWeb(operacion: "login" | "refresh" | "logout", datos?: unknown): Promise<Response> {
  const reto = await fetch(`${API_URL}/api/v1/auth/web/csrf`, {
    credentials: "include", cache: "no-store",
  });
  if (!reto.ok) throw new Error("No fue posible validar la sesión web.");
  const { csrf_token: csrf } = await reto.json();
  if (typeof csrf !== "string" || !csrf) throw new Error("Reto CSRF inválido.");
  return fetch(`${API_URL}/api/v1/auth/web/${operacion}`, {
    method: "POST", credentials: "include", cache: "no-store",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    ...(datos === undefined ? {} : { body: JSON.stringify(datos) }),
  });
}

export async function conBloqueoSesion<T>(accion: () => Promise<T>): Promise<T> {
  // Serializa la rotación entre pestañas cuando el navegador admite Web Locks.
  if (navigator.locks) return navigator.locks.request("solventa-sesion-web", accion);
  return accion();
}

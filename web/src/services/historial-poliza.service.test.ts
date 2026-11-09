import { afterEach, describe, expect, it, vi } from "vitest";
import { guardarAccessToken } from "./session";
import { obtenerHistorialPoliza } from "./historial-poliza.service";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

function simular(respuesta: Response) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async () => respuesta.clone());
}

function simularSinJson(status: number) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => new Response("no-es-json", { status }));
}

const HISTORIAL = {
  poliza_id: "POL-1",
  numero_poliza: "SOLV-VIA-2026-00152",
  movimientos: [
    {
      movimiento_id: "POL-1-EMISION",
      poliza_id: "POL-1",
      categoria: "POLIZA",
      tipo: "EMISION",
      fecha: "2026-10-20T14:05:00Z",
      descripcion: "Póliza emitida",
      referencia: "SOLV-VIA-2026-00152",
      referencia_externa: null,
      estado: "COMPLETADO",
      monto: null,
      moneda: null,
      naturaleza_monto: null,
      cambios: [],
      consentimiento: null,
    },
  ],
};

afterEach(() => {
  vi.restoreAllMocks();
  guardarAccessToken(null);
});

describe("historial-poliza.service", () => {
  it("consulta el historial con token Bearer y la ruta de la póliza", async () => {
    guardarAccessToken("tok");
    const fetch = simular(json(HISTORIAL));

    const historial = await obtenerHistorialPoliza("POL-1");

    expect(historial.poliza_id).toBe("POL-1");
    expect(historial.movimientos).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/polizas/POL-1/historial"),
      expect.objectContaining({ headers: { authorization: "Bearer tok" } }),
    );
  });

  it("codifica el identificador de la póliza en la URL", async () => {
    guardarAccessToken("tok");
    const fetch = simular(json(HISTORIAL));
    await obtenerHistorialPoliza("a/b");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/polizas/a%2Fb/historial"),
      expect.anything(),
    );
  });

  it.each([
    ["POLIZA_NO_ENCONTRADA", 404, "No encontramos la póliza."],
    ["ACCESS_DENIED", 403, "No tienes acceso al historial de esta póliza."],
  ])("traduce el código %s", async (codigo, status, mensaje) => {
    guardarAccessToken("tok");
    simular(json({ detail: { codigo } }, status));
    await expect(obtenerHistorialPoliza("POL-1")).rejects.toThrow(mensaje as string);
  });

  it("avisa que la sesión expiró ante un 401 sin código", async () => {
    guardarAccessToken("tok");
    simular(json({ detail: {} }, 401));
    await expect(obtenerHistorialPoliza("POL-1")).rejects.toThrow(
      "Tu sesión expiró. Vuelve a iniciar sesión.",
    );
  });

  it("cae al mensaje genérico ante un 500 sin cuerpo JSON", async () => {
    guardarAccessToken("tok");
    simularSinJson(500);
    await expect(obtenerHistorialPoliza("POL-1")).rejects.toThrow(
      "No fue posible consultar el historial de la póliza.",
    );
  });
});

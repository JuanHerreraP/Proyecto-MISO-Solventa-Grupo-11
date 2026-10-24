import { afterEach, describe, expect, it, vi } from "vitest";
import { guardarAccessToken } from "./session";
import {
  crearCotizacion,
  obtenerCotizacion,
  obtenerRamos,
} from "./cotizaciones.service";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status });

function simular(respuesta: Response) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => respuesta.clone());
}

afterEach(() => {
  vi.restoreAllMocks();
  guardarAccessToken(null);
});

describe("cotizaciones.service", () => {
  it("obtiene los ramos con el token Bearer", async () => {
    guardarAccessToken("token-ramos");
    const fetch = simular(json([{ ramo: "VIAJE", nombre: "Seguro de viaje" }]));
    const ramos = await obtenerRamos();
    expect(ramos).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/cotizaciones/ramos"),
      expect.objectContaining({ headers: { authorization: "Bearer token-ramos" } }),
    );
  });

  it("lanza un error cuando no puede consultar los ramos", async () => {
    guardarAccessToken("token-ramos");
    simular(json({}, 500));
    await expect(obtenerRamos()).rejects.toThrow(
      "No fue posible consultar los ramos disponibles.",
    );
  });

  it("crea una cotización enviando el cuerpo esperado", async () => {
    guardarAccessToken("token-crear");
    const solicitud = {
      cliente_id: "CLI-1",
      ramo: "VIAJE" as const,
      datos_riesgo: { destino: "Lima" },
    };
    const fetch = simular(json({ cotizacion_id: "COT-1" }, 201));
    const cotizacion = await crearCotizacion(solicitud);
    expect(cotizacion.cotizacion_id).toBe("COT-1");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/cotizaciones"),
      expect.objectContaining({ method: "POST", body: JSON.stringify(solicitud) }),
    );
  });

  it.each([
    [{ detail: { mensaje: "El perfil no permite la cobertura." } }, "El perfil no permite la cobertura."],
    [{ detail: "Datos inválidos." }, "Datos inválidos."],
    [{}, "No fue posible crear la cotización."],
  ])("propaga el error del backend al crear", async (body, mensaje) => {
    guardarAccessToken("token-crear");
    simular(json(body, 422));
    await expect(
      crearCotizacion({ cliente_id: "CLI-1", ramo: "VIAJE", datos_riesgo: {} }),
    ).rejects.toThrow(mensaje as string);
  });

  it("consulta una cotización por id", async () => {
    guardarAccessToken("token-consultar");
    const fetch = simular(json({ cotizacion_id: "COT-9" }));
    const cotizacion = await obtenerCotizacion("COT-9");
    expect(cotizacion.cotizacion_id).toBe("COT-9");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/cotizaciones/COT-9"),
      expect.anything(),
    );
  });

  it("lanza un error si la cotización no se puede consultar", async () => {
    guardarAccessToken("token-consultar");
    simular(json({}, 404));
    await expect(obtenerCotizacion("COT-9")).rejects.toThrow(
      "No fue posible consultar la cotización.",
    );
  });
});

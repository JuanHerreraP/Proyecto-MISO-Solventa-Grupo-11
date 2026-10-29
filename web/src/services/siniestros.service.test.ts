import { afterEach, describe, expect, it, vi } from "vitest";
import { guardarAccessToken } from "./session";
import { crearSiniestro, listarSiniestros } from "./siniestros.service";
import type { SolicitudSiniestro } from "../types/siniestros";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status });

function simular(respuesta: Response) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => respuesta.clone());
}

/** Respuesta cuyo cuerpo no es JSON, para ejercitar el catch del mensaje de error. */
function simularSinJson(status: number) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => new Response("no-es-json", { status }));
}

const SOLICITUD: SolicitudSiniestro = {
  poliza_id: "POL-1",
  fecha_evento: "2026-10-20",
  hora_evento: "18:30:00",
  lugar: "Aeropuerto El Dorado",
  descripcion: "El vuelo fue cancelado y hubo gastos adicionales.",
  estimacion_danos: 850000,
};

const SINIESTRO = {
  siniestro_id: "SIN-1",
  cliente_id: "CLI-1",
  poliza_id: "POL-1",
  origen: "MANUAL",
  estado: "REGISTRADO",
  fecha_evento: "2026-10-20",
  hora_evento: "18:30:00",
  lugar: "Aeropuerto El Dorado",
  descripcion: "El vuelo fue cancelado y hubo gastos adicionales.",
  estimacion_danos: "850000.00",
  moneda: "COP",
  registrado_por: "CLI-1",
  registrado_en: "2026-10-21T15:00:00Z",
};

afterEach(() => {
  vi.restoreAllMocks();
  guardarAccessToken(null);
});

describe("siniestros.service", () => {
  describe("crearSiniestro", () => {
    it("registra el siniestro con POST, token Bearer y el cuerpo en JSON", async () => {
      guardarAccessToken("token-siniestro");
      const fetch = simular(json(SINIESTRO, 201));

      const creado = await crearSiniestro(SOLICITUD);

      expect(creado.siniestro_id).toBe("SIN-1");
      expect(creado.origen).toBe("MANUAL");
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/siniestros"),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            authorization: "Bearer token-siniestro",
            "content-type": "application/json",
          }),
          body: JSON.stringify(SOLICITUD),
        }),
      );
    });

    it.each([
      ["POLIZA_NO_ENCONTRADA", 404, "No encontramos la póliza seleccionada."],
      ["POLIZA_AJENA", 403, "La póliza seleccionada no está asociada a tu cuenta."],
      [
        "POLIZA_NO_VIGENTE",
        409,
        "La póliza no está vigente; no es posible registrar el siniestro.",
      ],
      ["FECHA_FUTURA", 422, "La fecha del evento no puede estar en el futuro."],
      [
        "FECHA_FUERA_DE_VIGENCIA",
        422,
        "La fecha del evento está fuera del periodo cubierto por la póliza.",
      ],
    ])("traduce el código de dominio %s a un mensaje claro", async (codigo, status, mensaje) => {
      guardarAccessToken("token-siniestro");
      simular(json({ detail: { codigo } }, status));

      await expect(crearSiniestro(SOLICITUD)).rejects.toThrow(mensaje as string);
    });

    it("usa el mensaje genérico de 422 cuando no hay un código conocido", async () => {
      guardarAccessToken("token-siniestro");
      simular(json({ detail: { codigo: "OTRO_CODIGO" } }, 422));

      await expect(crearSiniestro(SOLICITUD)).rejects.toThrow(
        "Revisa los datos del evento e inténtalo de nuevo.",
      );
    });

    it("avisa que la sesión expiró ante un 401 sin código", async () => {
      guardarAccessToken("token-siniestro");
      simular(json({ detail: {} }, 401));

      await expect(crearSiniestro(SOLICITUD)).rejects.toThrow(
        "Tu sesión expiró. Vuelve a iniciar sesión.",
      );
    });

    it("cae al mensaje genérico cuando el error no trae cuerpo JSON", async () => {
      guardarAccessToken("token-siniestro");
      simularSinJson(500);

      await expect(crearSiniestro(SOLICITUD)).rejects.toThrow(
        "No fue posible registrar el siniestro. Inténtalo de nuevo.",
      );
    });

    it("cae al mensaje genérico ante un 500 con cuerpo sin código ni estado mapeado", async () => {
      guardarAccessToken("token-siniestro");
      simular(json({ detail: { codigo: "DESCONOCIDO" } }, 500));

      await expect(crearSiniestro(SOLICITUD)).rejects.toThrow(
        "No fue posible registrar el siniestro. Inténtalo de nuevo.",
      );
    });
  });

  describe("listarSiniestros", () => {
    it("devuelve la lista de siniestros del cliente", async () => {
      guardarAccessToken("token-listar");
      const fetch = simular(json([SINIESTRO]));

      const siniestros = await listarSiniestros();

      expect(siniestros).toHaveLength(1);
      expect(siniestros[0].siniestro_id).toBe("SIN-1");
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/siniestros"),
        expect.objectContaining({ headers: { authorization: "Bearer token-listar" } }),
      );
    });

    it("lanza un error cuando no puede consultar los siniestros", async () => {
      guardarAccessToken("token-listar");
      simular(json({}, 500));

      await expect(listarSiniestros()).rejects.toThrow(
        "No fue posible consultar tus siniestros.",
      );
    });
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { guardarAccessToken } from "./session";
import {
  confirmarEndoso,
  descargarEndoso,
  ErrorEndoso,
  listarEndosos,
  obtenerOpciones,
  simularEndoso,
} from "./endosos.service";

const json = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } });

beforeEach(() => {
  guardarAccessToken("token-endosos");
  URL.createObjectURL = vi.fn(() => "blob:endoso");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
  guardarAccessToken(null);
});

describe("endosos.service", () => {
  it("consulta las opciones de la póliza con la sesión", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ poliza_id: "POL-1" }));

    await obtenerOpciones("POL-1");

    const [url, opciones] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/polizas\/POL-1\/endosos\/opciones$/);
    expect(new Headers(opciones?.headers).get("Authorization")).toBe("Bearer token-endosos");
  });

  it("simula enviando solo el estado deseado", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ ajuste_prima: "1.00" }));

    await simularEndoso("POL-1", { coberturas_opcionales: [] });

    const [url, opciones] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/endosos\/simulacion$/);
    expect(opciones?.method).toBe("POST");
    expect(JSON.parse(String(opciones?.body))).toEqual({ coberturas_opcionales: [] });
  });

  it("confirma con la aceptación y la clave de idempotencia", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ endoso_id: "E-1" }, 201));

    const endoso = await confirmarEndoso("POL-1", { beneficiarios: [] }, "clave-1");

    const [, opciones] = fetchMock.mock.calls[0];
    expect(new Headers(opciones?.headers).get("Idempotency-Key")).toBe("clave-1");
    expect(JSON.parse(String(opciones?.body))).toEqual({ beneficiarios: [], acepta_condiciones: true });
    expect(endoso.endoso_id).toBe("E-1");
  });

  it("convierte el error de negocio en ErrorEndoso con su código y campo", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json(
        { detail: { codigo: "PORCENTAJES_NO_SUMAN_100", mensaje: "Deben sumar 100%.", campo: "beneficiarios" } },
        422,
      ),
    );

    const error = await simularEndoso("POL-1", { beneficiarios: [] }).catch((e) => e);

    expect(error).toBeInstanceOf(ErrorEndoso);
    expect(error.codigo).toBe("PORCENTAJES_NO_SUMAN_100");
    expect(error.campo).toBe("beneficiarios");
    expect(error.message).toBe("Deben sumar 100%.");
  });

  it("usa un mensaje legible para la validación de FastAPI", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ detail: [{ loc: ["body"] }] }, 422));

    await expect(simularEndoso("POL-1", {})).rejects.toThrow("Revisa los datos ingresados.");
  });

  it("lista el historial", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ endosos: [{ endoso_id: "E-1" }] }));

    expect(await listarEndosos("POL-1")).toEqual([{ endoso_id: "E-1" }]);
  });

  it("descarga el PDF del endoso con el nombre del servidor", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("%PDF-1.4", {
        status: 200,
        headers: { "Content-Disposition": 'attachment; filename="endoso-SOL-1-001.pdf"' },
      }),
    );
    let nombre = "";
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      nombre = this.download;
    });

    await descargarEndoso("POL-1", "END-1-001");

    expect(nombre).toBe("endoso-SOL-1-001.pdf");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:endoso");
  });

  it("no descarga nada si el servidor rechaza", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ detail: { codigo: "ENDOSO_NO_ENCONTRADO", mensaje: "El endoso no existe." } }, 404),
    );

    await expect(descargarEndoso("POL-1", "X")).rejects.toThrow("El endoso no existe.");
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });
});

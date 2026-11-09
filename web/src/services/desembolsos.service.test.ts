import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { guardarAccessToken } from "./session";
import {
  aprobarSiniestro,
  ErrorDesembolso,
  listarDesembolsos,
  obtenerBandeja,
  obtenerCuenta,
  rechazarSiniestro,
  registrarCuenta,
  reintentarDesembolso,
} from "./desembolsos.service";

const json = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } });

beforeEach(() => guardarAccessToken("token-desembolsos"));
afterEach(() => {
  vi.restoreAllMocks();
  guardarAccessToken(null);
});

describe("desembolsos.service", () => {
  it("consulta la cuenta con la sesión y acepta que no haya", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(null));

    expect(await obtenerCuenta()).toBeNull();

    const [url, opciones] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/desembolsos\/cuenta$/);
    expect(new Headers(opciones?.headers).get("Authorization")).toBe("Bearer token-desembolsos");
  });

  it("registra la cuenta con PUT", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ ultimos_digitos: "1234" }));

    await registrarCuenta({ codigo_banco: "1007", tipo_cuenta: "AHORROS", numero_cuenta: "4567891234" });

    const [, opciones] = fetchMock.mock.calls[0];
    expect(opciones?.method).toBe("PUT");
    expect(JSON.parse(String(opciones?.body))).toEqual({
      codigo_banco: "1007", tipo_cuenta: "AHORROS", numero_cuenta: "4567891234",
    });
  });

  it("lista los desembolsos del cliente", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json([{ desembolso_id: "DES-1" }]));

    expect(await listarDesembolsos()).toEqual([{ desembolso_id: "DES-1" }]);
  });

  it("filtra la bandeja por estado", async () => {
    // Una respuesta nueva por llamada: el cuerpo de una Response solo se lee una vez.
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => json([]));

    await obtenerBandeja("REGISTRADO");
    await obtenerBandeja();

    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/operaciones\/siniestros\?estado=REGISTRADO$/);
    expect(String(fetchMock.mock.calls[1][0])).toMatch(/\/operaciones\/siniestros$/);
  });

  it("aprueba con o sin monto, rechaza con motivo y reintenta", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => json({}));

    await aprobarSiniestro("SIN-1", "600000");
    await aprobarSiniestro("SIN-1");
    await rechazarSiniestro("SIN-2", "No cubierto");
    await reintentarDesembolso("SIN-3");

    const cuerpos = fetchMock.mock.calls.map(([, o]) => (o?.body ? JSON.parse(String(o.body)) : undefined));
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/SIN-1\/aprobacion$/);
    expect(cuerpos[0]).toEqual({ monto_aprobado: "600000" });
    expect(cuerpos[1]).toEqual({});
    expect(cuerpos[2]).toEqual({ motivo: "No cubierto" });
    expect(String(fetchMock.mock.calls[3][0])).toMatch(/\/SIN-3\/desembolso\/reintento$/);
  });

  it("convierte el error de negocio en ErrorDesembolso", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ detail: { codigo: "MONTO_INVALIDO", mensaje: "Supera la suma asegurada." } }, 422),
    );

    const error = await aprobarSiniestro("SIN-1", "1").catch((e) => e);

    expect(error).toBeInstanceOf(ErrorDesembolso);
    expect(error.codigo).toBe("MONTO_INVALIDO");
    expect(error.message).toBe("Supera la suma asegurada.");
  });

  it("usa un mensaje legible para la validación de FastAPI", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ detail: [{ loc: ["body"] }] }, 422));

    await expect(registrarCuenta({ codigo_banco: "x", tipo_cuenta: "AHORROS", numero_cuenta: "1" }))
      .rejects.toThrow("Revisa los datos ingresados.");
  });
});

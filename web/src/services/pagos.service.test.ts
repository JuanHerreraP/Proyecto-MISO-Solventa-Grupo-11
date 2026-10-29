import { afterEach, describe, expect, it, vi } from "vitest";
import { guardarAccessToken } from "./session";
import { crearPago, listarPagos, obtenerPago } from "./pagos.service";

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

describe("pagos.service", () => {
  it("lista los pagos del cliente", async () => {
    guardarAccessToken("token-listar");
    simular(json([{ pago_id: "p1" }]));
    const pagos = await listarPagos();
    expect(pagos).toHaveLength(1);
  });

  it("falla al listar si la respuesta no es correcta", async () => {
    guardarAccessToken("token-listar");
    simular(json({}, 500));
    await expect(listarPagos()).rejects.toThrow("No fue posible consultar tus pagos.");
  });

  it("crea un pago enviando la Idempotency-Key y el cuerpo", async () => {
    guardarAccessToken("token-pago");
    const solicitud = {
      cotizacion_id: "COT-1",
      metodo: "TARJETA" as const,
      token_tarjeta: "tok_visa_123456",
    };
    const fetch = simular(json({ pago_id: "PAG-1", estado: "APROBADO" }, 201));
    const pago = await crearPago(solicitud, "llave-unica-0001");
    expect(pago.estado).toBe("APROBADO");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/pagos"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "idempotency-key": "llave-unica-0001" }),
        body: JSON.stringify(solicitud),
      }),
    );
  });

  it.each([
    [{ detail: { mensaje: "La cotización no está vigente." } }, "La cotización no está vigente."],
    [{ detail: "Error" }, "Error"],
    [{}, "No fue posible procesar el pago."],
  ])("propaga el error del backend al pagar", async (body, mensaje) => {
    guardarAccessToken("token-pago");
    simular(json(body, 409));
    await expect(
      crearPago({ cotizacion_id: "COT-1", metodo: "PSE", codigo_banco: "1007" }, "llave-0002"),
    ).rejects.toThrow(mensaje as string);
  });

  it("consulta un pago por id", async () => {
    guardarAccessToken("token-pago");
    const fetch = simular(json({ pago_id: "PAG-9", estado: "APROBADO" }));
    const pago = await obtenerPago("PAG-9");
    expect(pago.pago_id).toBe("PAG-9");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/pagos/PAG-9"),
      expect.anything(),
    );
  });

  it("falla al consultar un pago inexistente", async () => {
    guardarAccessToken("token-pago");
    simular(json({}, 404));
    await expect(obtenerPago("PAG-9")).rejects.toThrow("No fue posible consultar tu pago.");
  });
});

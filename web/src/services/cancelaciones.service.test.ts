import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  confirmarCancelacion,
  consultarCancelacion,
  ErrorCancelacion,
} from "./cancelaciones.service";
import { guardarAccessToken } from "./session";

const json = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });

beforeEach(() => guardarAccessToken("token-cancelacion"));

afterEach(() => {
  vi.restoreAllMocks();
  guardarAccessToken(null);
});

describe("cancelaciones.service", () => {
  it("consulta las condiciones de la póliza con la sesión autenticada", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ poliza_id: "POL-1", cancelable: true, saldo_estimado: "74794.52" }),
    );

    const condiciones = await consultarCancelacion("POL/1");

    const [url, opciones] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/polizas\/POL%2F1\/cancelacion$/);
    expect(new Headers(opciones?.headers).get("Authorization")).toBe(
      "Bearer token-cancelacion",
    );
    expect(condiciones.saldo_estimado).toBe("74794.52");
  });

  it("confirma explícitamente con una clave de idempotencia", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ cancelacion_id: "CAN-POL-1", estado_devolucion: "PENDIENTE" }, 201),
    );

    const cancelacion = await confirmarCancelacion(
      "POL-1",
      { motivo: "OTRO", detalle: "Ya no necesito la cobertura" },
      "cancelacion-1",
    );

    const [, opciones] = fetchMock.mock.calls[0];
    expect(opciones?.method).toBe("POST");
    expect(new Headers(opciones?.headers).get("Idempotency-Key")).toBe("cancelacion-1");
    expect(JSON.parse(String(opciones?.body))).toEqual({
      motivo: "OTRO",
      detalle: "Ya no necesito la cobertura",
      confirmo: true,
    });
    expect(cancelacion.cancelacion_id).toBe("CAN-POL-1");
  });

  it("preserva el código y los bloqueos de un error de negocio", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json(
        {
          detail: {
            codigo: "SINIESTRO_EN_TRAMITE",
            mensaje: "La póliza tiene un siniestro en trámite.",
            bloqueos: [
              {
                codigo: "SINIESTRO_EN_TRAMITE",
                mensaje: "Espera a que finalice el siniestro.",
                siniestros: ["SIN-1"],
              },
            ],
          },
        },
        409,
      ),
    );

    const error = await consultarCancelacion("POL-1").catch((fallo) => fallo);

    expect(error).toBeInstanceOf(ErrorCancelacion);
    expect(error.codigo).toBe("SINIESTRO_EN_TRAMITE");
    expect(error.status).toBe(409);
    expect(error.bloqueos[0].siniestros).toEqual(["SIN-1"]);
  });

  it("traduce los errores de validación de FastAPI", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ detail: [{ loc: ["body", "motivo"] }] }, 422),
    );

    await expect(
      confirmarCancelacion("POL-1", { motivo: "OTRO" }, "cancelacion-1"),
    ).rejects.toMatchObject({
      codigo: "DATOS_INVALIDOS",
      message: "Revisa los datos ingresados.",
    });
  });
});

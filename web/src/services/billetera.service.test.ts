import { afterEach, describe, expect, it, vi } from "vitest";
import { guardarAccessToken } from "./session";
import { obtenerBilletera } from "./billetera.service";

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

describe("billetera.service", () => {
  it("obtiene la billetera del cliente con el token Bearer", async () => {
    guardarAccessToken("token-billetera");
    const fetch = simular(
      json({
        polizas: [
          {
            poliza_id: "POL-1",
            numero_poliza: "SOL-0001",
            nombre_ramo: "Seguro de viaje",
            estado: "VIGENTE",
            activa: true,
            fecha_fin: "2027-01-01",
            cobertura_principal: "Asistencia en viaje",
          },
        ],
        total_vigentes: 1,
        total_inactivas: 0,
      }),
    );

    const billetera = await obtenerBilletera();

    expect(billetera.total_vigentes).toBe(1);
    expect(billetera.polizas[0].numero_poliza).toBe("SOL-0001");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/billetera/polizas"),
      expect.objectContaining({ headers: { authorization: "Bearer token-billetera" } }),
    );
  });

  it("lanza un error cuando no puede consultar las pólizas", async () => {
    guardarAccessToken("token-billetera");
    simular(json({}, 500));
    await expect(obtenerBilletera()).rejects.toThrow("No fue posible consultar tus pólizas.");
  });
});

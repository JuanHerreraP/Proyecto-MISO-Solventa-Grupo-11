import { afterEach, describe, expect, it, vi } from "vitest";
import { guardarAccessToken } from "./session";
import { crearAnalistaCumplimiento } from "./auditor.service";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

function simular(respuesta: Response) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async () => respuesta.clone());
}

const DATOS = {
  nombre: "María",
  apellido: "Torres",
  email: "maria@solventa.com",
  password: "Password123!",
  tipo_documento: "CC",
  numero_documento: "1012345678",
  fecha_nacimiento: "1990-01-01",
};

afterEach(() => {
  vi.restoreAllMocks();
  guardarAccessToken(null);
});

describe("crearAnalistaCumplimiento", () => {
  it("crea el analista con POST, rol fijo y consentimiento KYC", async () => {
    guardarAccessToken("tok");
    const fetch = simular(json({ id: "u1", rol: "ANALISTA_CUMPLIMIENTO", ...DATOS }, 201));

    const creado = await crearAnalistaCumplimiento(DATOS);

    expect(creado.rol).toBe("ANALISTA_CUMPLIMIENTO");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/users"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          ...DATOS,
          acepta_validacion_identidad: true,
          rol: "ANALISTA_CUMPLIMIENTO",
        }),
      }),
    );
  });

  it.each([
    ["EMAIL_ALREADY_EXISTS", 409, "Ya existe un usuario con ese correo."],
    ["DOCUMENT_ALREADY_EXISTS", 409, "Ya existe una cuenta con ese tipo y número de documento."],
  ])("traduce %s al crear analista", async (codigo, status, mensaje) => {
    guardarAccessToken("tok");
    simular(json({ detail: { codigo } }, status));
    await expect(crearAnalistaCumplimiento(DATOS)).rejects.toThrow(mensaje as string);
  });

  it("avisa cuando el usuario no tiene permisos", async () => {
    guardarAccessToken("tok");
    simular(json({ detail: {} }, 403));
    await expect(crearAnalistaCumplimiento(DATOS)).rejects.toThrow(
      "No tienes permisos para crear analistas de cumplimiento.",
    );
  });

  it("cae al mensaje genérico ante un 500 sin cuerpo útil", async () => {
    guardarAccessToken("tok");
    simular(json({}, 500));
    await expect(crearAnalistaCumplimiento(DATOS)).rejects.toThrow(
      "No fue posible crear el analista de cumplimiento. Inténtalo de nuevo.",
    );
  });
});

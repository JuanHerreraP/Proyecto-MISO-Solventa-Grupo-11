import { beforeEach, expect, it, vi } from "vitest";
import { ErrorFirma, firmarContrato, obtenerContrato, solicitarCodigo } from "./firma.service";
import { fetchAutenticado } from "./session";

vi.mock("./session", () => ({ fetchAutenticado: vi.fn() }));

function respuesta(status: number, cuerpo: unknown): Response {
  return new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } });
}

beforeEach(() => vi.clearAllMocks());

it("consulta el contrato de la cotización", async () => {
  vi.mocked(fetchAutenticado).mockResolvedValue(respuesta(200, { estado: "PENDIENTE" }));

  await expect(obtenerContrato("COT 1")).resolves.toEqual({ estado: "PENDIENTE" });
  expect(vi.mocked(fetchAutenticado).mock.calls[0][0]).toMatch(/\/api\/v1\/firmas\/COT%201$/);
});

it("pide el código por el canal elegido", async () => {
  vi.mocked(fetchAutenticado).mockResolvedValue(respuesta(200, {}));

  await solicitarCodigo("COT-1", "SMS");

  const [url, opciones] = vi.mocked(fetchAutenticado).mock.calls[0];
  expect(url).toMatch(/\/firmas\/COT-1\/otp$/);
  expect(opciones?.method).toBe("POST");
  expect(opciones?.body).toBe(JSON.stringify({ canal: "SMS" }));
});

it("envía el código con la huella aceptada", async () => {
  vi.mocked(fetchAutenticado).mockResolvedValue(respuesta(200, {}));

  await firmarContrato("COT-1", "123456", "ab".repeat(32));

  expect(vi.mocked(fetchAutenticado).mock.calls[0][1]?.body).toBe(
    JSON.stringify({ codigo: "123456", huella_documento: "ab".repeat(32) }),
  );
});

it("convierte el error del backend en ErrorFirma con sus datos", async () => {
  vi.mocked(fetchAutenticado).mockResolvedValue(respuesta(422, {
    detail: { codigo: "OTP_INCORRECTO", mensaje: "El código no es correcto.", intentos_restantes: 1 },
  }));

  const error = await firmarContrato("COT-1", "000000", "a".repeat(64)).catch((e) => e);

  expect(error).toBeInstanceOf(ErrorFirma);
  expect(error).toMatchObject({
    message: "El código no es correcto.", codigo: "OTP_INCORRECTO", status: 422, intentosRestantes: 1,
  });
});

it("usa un mensaje genérico si el backend no explica el error", async () => {
  vi.mocked(fetchAutenticado).mockResolvedValue(new Response("caído", { status: 502 }));

  await expect(obtenerContrato("COT-1")).rejects.toThrow("No fue posible cargar el contrato.");
});

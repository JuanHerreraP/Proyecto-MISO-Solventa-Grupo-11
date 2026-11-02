import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { guardarAccessToken } from "./session";
import { descargarDocumentoPoliza } from "./poliza-documento.service";

const pdf = (cabeceras: Record<string, string> = {}) =>
  new Response("%PDF-1.4", { status: 200, headers: { "Content-Type": "application/pdf", ...cabeceras } });

beforeEach(() => {
  guardarAccessToken("token-poliza");
  URL.createObjectURL = vi.fn(() => "blob:poliza");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
  guardarAccessToken(null);
});

describe("descargarDocumentoPoliza", () => {
  it("pide el PDF con la sesión y lo descarga con el nombre indicado por el servidor", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      pdf({ "Content-Disposition": 'attachment; filename="poliza-SOL-2027-ABC.pdf"' }),
    );
    let descargado: { download: string; href: string } | undefined;
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      descargado = { download: this.download, href: this.href };
    });

    await descargarDocumentoPoliza("POL-001");

    const [url, opciones] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/polizas\/POL-001\/documento$/);
    expect(new Headers(opciones?.headers).get("Authorization")).toBe("Bearer token-poliza");
    expect(descargado?.download).toBe("poliza-SOL-2027-ABC.pdf");
    expect(descargado?.href).toBe("blob:poliza");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:poliza");
  });

  it("usa un nombre por defecto si el servidor no lo informa", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(pdf());
    let nombre = "";
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      nombre = this.download;
    });

    await descargarDocumentoPoliza("POL-001");

    expect(nombre).toBe("poliza-POL-001.pdf");
  });

  it("muestra el mensaje del servidor cuando la descarga falla", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: { codigo: "X", mensaje: "La póliza no existe." } }), { status: 404 }),
    );

    await expect(descargarDocumentoPoliza("POL-9")).rejects.toThrow("La póliza no existe.");
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it("usa un mensaje genérico si la respuesta de error no es legible", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("boom", { status: 500 }));

    await expect(descargarDocumentoPoliza("POL-9")).rejects.toThrow(
      "No fue posible descargar la póliza.",
    );
  });
});

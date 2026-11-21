import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { guardarAccessToken } from "./session";
import {
  configurarRenovacionAutomatica,
  consultarRenovacionAutomatica,
  descargarDocumentoRenovacion,
  ErrorRenovacionAutomatica,
  type RenovacionAutomatica,
} from "./renovacion-automatica.service";

const ESTADO: RenovacionAutomatica = {
  poliza_id: "POL-1",
  disponible: true,
  activa: true,
  tarjeta: null,
  vence_el: "2026-12-31",
  preaviso_desde: "2026-12-01",
  cobro_programado_para: "2026-12-31",
  actualizado_en: null,
  ultimo_ciclo: null,
};

const json = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } });

beforeEach(() => {
  guardarAccessToken("token-renovacion");
  URL.createObjectURL = vi.fn(() => "blob:renovacion");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
  guardarAccessToken(null);
});

describe("renovación automática", () => {
  it("consulta el estado con la sesión del cliente", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(json(ESTADO));

    const estado = await consultarRenovacionAutomatica("POL 1");

    const [url, opciones] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/polizas\/POL%201\/renovacion-automatica$/);
    expect(new Headers(opciones?.headers).get("Authorization")).toBe("Bearer token-renovacion");
    expect(estado.activa).toBe(true);
  });

  it("guarda la preferencia con PUT y solo envía el token de la tarjeta", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ ...ESTADO, tarjeta: { ultimos_digitos: "4242" } }),
    );

    const estado = await configurarRenovacionAutomatica("POL-1", {
      activa: true,
      tarjeta: { token_tarjeta: "tok_visa_abc", ultimos_digitos: "4242" },
    });

    const [, opciones] = fetchMock.mock.calls[0];
    expect(opciones?.method).toBe("PUT");
    expect(JSON.parse(String(opciones?.body))).toEqual({
      activa: true,
      tarjeta: { token_tarjeta: "tok_visa_abc", ultimos_digitos: "4242" },
    });
    expect(estado.tarjeta?.ultimos_digitos).toBe("4242");
  });

  it("traduce los errores del servidor con su código", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ detail: { codigo: "ACCESO_DENEGADO", mensaje: "Solo el titular." } }, 403),
    );

    const fallo = await configurarRenovacionAutomatica("POL-1", { activa: true }).catch((e) => e);

    expect(fallo).toBeInstanceOf(ErrorRenovacionAutomatica);
    expect(fallo.codigo).toBe("ACCESO_DENEGADO");
    expect(fallo.status).toBe(403);
    expect(fallo.message).toBe("Solo el titular.");
  });

  it("los errores de validación no repiten lo enviado", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ detail: [{ msg: "x" }] }, 422));

    await expect(
      configurarRenovacionAutomatica("POL-1", { activa: true }),
    ).rejects.toThrow("Revisa los datos de la tarjeta.");
  });

  it("descarga el documento de la renovación con el nombre del servidor", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("%PDF-1.4", {
        status: 200,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": 'attachment; filename="renovacion-SOL-1-20261231.pdf"',
        },
      }),
    );
    let nombre = "";
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      nombre = this.download;
    });

    await descargarDocumentoRenovacion("POL-1", "REN-POL-1-20270101");

    expect(String(fetchMock.mock.calls[0][0])).toMatch(
      /\/renovacion-automatica\/REN-POL-1-20270101\/documento$/,
    );
    expect(nombre).toBe("renovacion-SOL-1-20261231.pdf");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:renovacion");
  });
});

import { guardarAccessToken } from "./session";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import type { SolicitudRegistroSocio } from "../types/socios";
import {
  generarCredencialesSocio,
  registrarSocio,
} from "./socios.service";

const SOLICITUD: SolicitudRegistroSocio = {
  nit: "900123456-7",
  razon_social: "Banco Andes S.A.",
  contactos_tecnicos: [
    {
      nombre: "María Torres",
      correo: "maria.torres@bancoandes.com",
    },
  ],
  pais_operacion: "CO",
  tipos_seguros_autorizados: ["VIAJE"],
  endpoints_autorizados: ["cotizaciones:crear"],
};

describe("socios.service", () => {
  it("identifica los campos rechazados por la validación del backend", async () => {
    guardarAccessToken("token-prueba");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      detail: [{ loc: ["body", "contactos_tecnicos", 0, "telefono"],
        msg: "String should have at least 7 characters" }],
    }), { status: 422, headers: { "Content-Type": "application/json" } }));
    await expect(registrarSocio(SOLICITUD)).rejects.toThrow(
      "Contacto técnico / 1 / Teléfono: String should have at least 7 characters",
    );
  });

  beforeEach(() => {
    guardarAccessToken(null);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("exige una sesión autorizada antes de registrar un socio", async () => {
    await expect(registrarSocio(SOLICITUD)).rejects.toThrow(
      "Debes iniciar sesión con un usuario autorizado para registrar socios.",
    );
  });

  it("envía el registro al endpoint de socios con el token de acceso", async () => {
    guardarAccessToken("token-prueba");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          ...SOLICITUD,
          socio_id: "socio-001",
          tenant_id: "tenant-001",
          estado: "ACTIVO",
          creado_en: "2026-10-13T00:00:00Z",
          actualizado_en: "2026-10-13T00:00:00Z",
        }),
        {
          status: 201,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const respuesta = await registrarSocio(SOLICITUD);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/socios"),
      {
        method: "POST",
        credentials: "omit",
        headers: {
          authorization: "Bearer token-prueba",
          "content-type": "application/json",
        },
        body: JSON.stringify(SOLICITUD),
      },
    );
    expect(respuesta.socio_id).toBe("socio-001");
    expect(respuesta.tenant_id).toBe("tenant-001");
  });

  it("muestra el mensaje estructurado entregado por el backend", async () => {
    guardarAccessToken("token-prueba");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            codigo: "SOCIO_DUPLICADO",
            mensaje: "Ya existe un socio registrado con este NIT.",
          },
        }),
        {
          status: 409,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await expect(registrarSocio(SOLICITUD)).rejects.toThrow(
      "Ya existe un socio registrado con este NIT.",
    );
  });

  it("muestra el mensaje textual entregado por el backend", async () => {
    guardarAccessToken("token-prueba");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "El usuario no tiene permisos para registrar socios.",
        }),
        {
          status: 403,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await expect(registrarSocio(SOLICITUD)).rejects.toThrow(
      "El usuario no tiene permisos para registrar socios.",
    );
  });

  it("genera las credenciales del socio con la sesión administrativa", async () => {
    guardarAccessToken("token-prueba");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          socio_id: "socio-001",
          tenant_id: "tenant-001",
          client_id: "solv_cliente_001",
          client_secret: "solv_secret_unico",
          scopes: ["cotizaciones:crear"],
          creado_en: "2026-10-13T00:00:00Z",
        }),
        {
          status: 201,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const respuesta = await generarCredencialesSocio("socio-001");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/socios/socio-001/credenciales"),
      {
        method: "POST",
        credentials: "omit",
        headers: {
          authorization: "Bearer token-prueba",
        },
      },
    );
    expect(respuesta.client_id).toBe("solv_cliente_001");
    expect(respuesta.client_secret).toBe("solv_secret_unico");
  });
});

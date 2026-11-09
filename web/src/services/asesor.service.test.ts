import { afterEach, describe, expect, it, vi } from "vitest";
import { guardarAccessToken } from "./session";
import {
  asociarCliente,
  crearAsesorVentas,
  crearSiniestroAsistido,
  listarClientesDeAsesor,
  obtenerPolizasDeCliente,
  type SolicitudSiniestroAsesor,
} from "./asesor.service";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

function simular(respuesta: Response) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async () => respuesta.clone());
}

const CLIENTE = {
  cliente_id: "CLI-1",
  nombre: "Ana",
  apellido: "Pérez",
  email: "ana@correo.com",
};

const SOLICITUD: SolicitudSiniestroAsesor = {
  cliente_id: "CLI-1",
  poliza_id: "POL-1",
  fecha_evento: "2026-10-20",
  hora_evento: "18:30:00",
  lugar: "El Dorado",
  descripcion: "El vuelo fue cancelado y hubo gastos adicionales.",
  estimacion_danos: 850000,
};

afterEach(() => {
  vi.restoreAllMocks();
  guardarAccessToken(null);
});

describe("asesor.service", () => {
  it("lista los clientes del asesor con token Bearer", async () => {
    guardarAccessToken("tok");
    const fetch = simular(json([CLIENTE]));

    const clientes = await listarClientesDeAsesor();

    expect(clientes).toHaveLength(1);
    expect(clientes[0].email).toBe("ana@correo.com");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/asesor/clientes"),
      expect.objectContaining({ headers: { authorization: "Bearer tok" } }),
    );
  });

  it("lanza error si no puede listar clientes", async () => {
    guardarAccessToken("tok");
    simular(json({}, 500));
    await expect(listarClientesDeAsesor()).rejects.toThrow("No fue posible consultar tus clientes.");
  });

  it("asocia un cliente por correo con POST", async () => {
    guardarAccessToken("tok");
    const fetch = simular(json(CLIENTE, 201));

    const cliente = await asociarCliente("ana@correo.com");

    expect(cliente.cliente_id).toBe("CLI-1");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/asesor/clientes"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ email: "ana@correo.com" }),
      }),
    );
  });

  it.each([
    ["CLIENTE_NO_ENCONTRADO", 404, "No existe un cliente con ese correo."],
    ["CLIENTE_YA_ASOCIADO", 409, "Ese cliente ya está asociado a tu cuenta."],
  ])("traduce %s al asociar", async (codigo, status, mensaje) => {
    guardarAccessToken("tok");
    simular(json({ detail: { codigo } }, status));
    await expect(asociarCliente("ana@correo.com")).rejects.toThrow(mensaje as string);
  });

  it("obtiene las pólizas del cliente asociado", async () => {
    guardarAccessToken("tok");
    const billetera = { polizas: [], total_vigentes: 0, total_inactivas: 0 };
    const fetch = simular(json(billetera));

    const resultado = await obtenerPolizasDeCliente("CLI-1");

    expect(resultado.total_vigentes).toBe(0);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/asesor/clientes/CLI-1/polizas"),
      expect.anything(),
    );
  });

  it("registra un siniestro asistido con el cliente en el cuerpo", async () => {
    guardarAccessToken("tok");
    const fetch = simular(json({ siniestro_id: "SIN-1", cliente_id: "CLI-1" }, 201));

    const creado = await crearSiniestroAsistido(SOLICITUD);

    expect(creado.siniestro_id).toBe("SIN-1");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/siniestros/asistido"),
      expect.objectContaining({ method: "POST", body: JSON.stringify(SOLICITUD) }),
    );
  });

  it("traduce CLIENTE_NO_ASOCIADO al registrar", async () => {
    guardarAccessToken("tok");
    simular(json({ detail: { codigo: "CLIENTE_NO_ASOCIADO" } }, 403));
    await expect(crearSiniestroAsistido(SOLICITUD)).rejects.toThrow(
      "El cliente no está asociado a tu cuenta.",
    );
  });

  describe("crearAsesorVentas", () => {
    const DATOS = {
      nombre: "María",
      apellido: "Torres",
      email: "maria@solventa.com",
      password: "Password123!",
      tipo_documento: "CC",
      numero_documento: "1012345678",
      fecha_nacimiento: "1990-01-01",
    };

    it("crea el asesor con POST, rol fijo y consentimiento KYC", async () => {
      guardarAccessToken("tok");
      const fetch = simular(json({ id: "u1", rol: "ASESOR_VENTAS", ...DATOS }, 201));

      const creado = await crearAsesorVentas(DATOS);

      expect(creado.rol).toBe("ASESOR_VENTAS");
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/auth/users"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            ...DATOS,
            acepta_validacion_identidad: true,
            rol: "ASESOR_VENTAS",
          }),
        }),
      );
    });

    it.each([
      ["EMAIL_ALREADY_EXISTS", 409, "Ya existe un usuario con ese correo."],
      [
        "DOCUMENT_ALREADY_EXISTS",
        409,
        "Ya existe una cuenta con ese tipo y número de documento.",
      ],
    ])("traduce %s al crear asesor", async (codigo, status, mensaje) => {
      guardarAccessToken("tok");
      simular(json({ detail: { codigo } }, status));
      await expect(crearAsesorVentas(DATOS)).rejects.toThrow(mensaje as string);
    });

    it("avisa cuando el usuario no tiene permisos", async () => {
      guardarAccessToken("tok");
      simular(json({ detail: {} }, 403));
      await expect(crearAsesorVentas(DATOS)).rejects.toThrow(
        "No tienes permisos para crear asesores.",
      );
    });
  });
});

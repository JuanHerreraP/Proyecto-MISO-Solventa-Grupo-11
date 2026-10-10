import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  login,
  register,
} from "./auth.service";


describe(
  "auth.service",
  () => {
    afterEach(() => {
      vi.restoreAllMocks();
    });


    it(
      "realiza el login contra el endpoint correcto",
      async () => {
        const fetchMock =
          vi.spyOn(
            globalThis,
            "fetch",
          );

        fetchMock.mockResolvedValue(
          new Response(
            JSON.stringify({
              access_token:
                "access-token",
              refresh_token:
                "refresh-token",
              token_type:
                "bearer",
              expires_in:
                1800,
              refresh_expires_in:
                604800,
            }),
            {
              status: 200,

              headers: {
                "Content-Type":
                  "application/json",
              },
            },
          ),
        );

        await login({
          email:
            "maria@solventa.com",
          password:
            "Password123!",
        });

        expect(
          fetchMock,
        ).toHaveBeenCalledWith(
          expect.stringContaining(
            "/api/v1/auth/login",
          ),
          expect.objectContaining({
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },
          }),
        );
      },
    );


    it(
      "lanza el mensaje del backend cuando falla el login",
      async () => {
        vi.spyOn(
          globalThis,
          "fetch",
        ).mockResolvedValue(
          new Response(
            JSON.stringify({
              detail: {
                codigo:
                  "INVALID_CREDENTIALS",

                mensaje:
                  "El correo electrónico o la contraseña son incorrectos.",
              },
            }),
            {
              status: 401,

              headers: {
                "Content-Type":
                  "application/json",
              },
            },
          ),
        );

        await expect(
          login({
            email:
              "maria@solventa.com",
            password:
              "incorrecta",
          }),
        ).rejects.toThrow(
          "El correo electrónico o la contraseña son incorrectos.",
        );
      },
    );


    it(
      "realiza el registro contra el endpoint correcto",
      async () => {
        const fetchMock =
          vi.spyOn(
            globalThis,
            "fetch",
          );

        fetchMock.mockResolvedValue(
          new Response(
            JSON.stringify({
              id: "usuario-123",
              nombre: "Maria",
              apellido: "Torres",
              email:
                "maria@solventa.com",
              rol: "CLIENTE",
              kyc_validado: true,
              fecha_creacion:
                "2026-10-10T00:00:00Z",
            }),
            {
              status: 201,

              headers: {
                "Content-Type":
                  "application/json",
              },
            },
          ),
        );

        const solicitud = {
          nombre: "Maria",
          apellido: "Torres",
          email:
            "maria@solventa.com",
          password:
            "Password123!",
          tipo_documento: "CC",
          numero_documento:
            "123456789",
          fecha_nacimiento:
            "1995-06-15",
          acepta_validacion_identidad:
            true,
        };

        await register(
          solicitud,
        );

        expect(
          fetchMock,
        ).toHaveBeenCalledWith(
          expect.stringContaining(
            "/api/v1/auth/register",
          ),
          expect.objectContaining({
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(
                solicitud,
              ),
          }),
        );
      },
    );
    it(
        "maneja un error de registro cuando detail es texto",
        async () => {
            vi.spyOn(
            globalThis,
            "fetch",
            ).mockResolvedValue(
            new Response(
                JSON.stringify({
                detail:
                    "Ya existe un usuario registrado con este correo.",
                }),
                {
                status: 409,

                headers: {
                    "Content-Type":
                    "application/json",
                },
                },
            ),
            );

            await expect(
            register({
                nombre: "Maria",
                apellido: "Torres",
                email:
                "maria@solventa.com",
                password:
                "Password123!",
                tipo_documento: "CC",
                numero_documento:
                "123456789",
                fecha_nacimiento:
                "1995-06-15",
                acepta_validacion_identidad:
                true,
            }),
            ).rejects.toThrow(
            "Ya existe un usuario registrado con este correo.",
            );
        },
    );

    it(
        "usa un mensaje genérico cuando el backend no entrega detail",
        async () => {
            vi.spyOn(
            globalThis,
            "fetch",
            ).mockResolvedValue(
            new Response(
                JSON.stringify({
                error:
                    "Internal server error",
                }),
                {
                status: 500,

                headers: {
                    "Content-Type":
                    "application/json",
                },
                },
            ),
            );

            await expect(
            register({
                nombre: "Maria",
                apellido: "Torres",
                email:
                "maria@solventa.com",
                password:
                "Password123!",
                tipo_documento: "CC",
                numero_documento:
                "123456789",
                fecha_nacimiento:
                "1995-06-15",
                acepta_validacion_identidad:
                true,
            }),
            ).rejects.toThrow(
            "Ocurrió un error al procesar la solicitud.",
            );
        },
    );

    it(
        "maneja una respuesta inválida del servidor",
        async () => {
            vi.spyOn(
            globalThis,
            "fetch",
            ).mockResolvedValue(
            new Response(
                "respuesta-no-json",
                {
                status: 500,

                headers: {
                    "Content-Type":
                    "text/plain",
                },
                },
            ),
            );

            await expect(
            register({
                nombre: "Maria",
                apellido: "Torres",
                email:
                "maria@solventa.com",
                password:
                "Password123!",
                tipo_documento: "CC",
                numero_documento:
                "123456789",
                fecha_nacimiento:
                "1995-06-15",
                acepta_validacion_identidad:
                true,
            }),
            ).rejects.toThrow(
            "No fue posible comunicarse correctamente con el servidor.",
            );
        },
    );
    it(
    "maneja detail como texto en un error de login",
    async () => {
        vi.spyOn(
        globalThis,
        "fetch",
        ).mockResolvedValue(
        new Response(
            JSON.stringify({
            detail:
                "Credenciales inválidas.",
            }),
            {
            status: 401,

            headers: {
                "Content-Type":
                "application/json",
            },
            },
        ),
        );

        await expect(
        login({
            email:
            "maria@solventa.com",
            password:
            "incorrecta",
        }),
        ).rejects.toThrow(
        "Credenciales inválidas.",
        );
    },
    );


    it(
      "usa mensaje genérico cuando el login falla sin detail",
      async () => {
        vi.spyOn(
          globalThis,
          "fetch",
        ).mockResolvedValue(
          new Response(
            JSON.stringify({}),
            {
              status: 401,

              headers: {
                "Content-Type":
                  "application/json",
              },
            },
          ),
        );

        await expect(
          login({
            email:
              "maria@solventa.com",
            password:
              "incorrecta",
          }),
        ).rejects.toThrow(
          "Ocurrió un error al procesar la solicitud.",
        );
      },
    );
  },
);
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import {
  MemoryRouter,
  Route,
  Routes,
} from "react-router-dom";

import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import RegisterPage from "./RegisterPage";

import {
  register,
} from "../services/auth.service";


vi.mock(
  "../services/auth.service",
  () => ({
    login: vi.fn(),
    register: vi.fn(),
  }),
);


function renderRegister() {
  return render(
    <MemoryRouter
      initialEntries={["/registro"]}
    >
      <Routes>
        <Route
          path="/registro"
          element={
            <RegisterPage />
          }
        />

        <Route
          path="/login"
          element={
            <h1>
              Inicia sesión
            </h1>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}


describe(
  "RegisterPage",
  () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });


    it(
      "muestra el formulario de registro",
      () => {
        renderRegister();

        expect(
          screen.getByRole(
            "heading",
            {
              name: /crear cuenta/i,
            },
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByLabelText(
            /^nombre$/i,
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByLabelText(
            /^apellido$/i,
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByLabelText(
            /correo electrónico/i,
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByLabelText(
            /tipo documento/i,
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByLabelText(
            /número de documento/i,
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByLabelText(
            /fecha de nacimiento/i,
          ),
        ).toBeInTheDocument();
      },
    );


    it(
      "no permite registrar cuando las contraseñas no coinciden",
      async () => {
        const user =
          userEvent.setup();

        renderRegister();

        await llenarFormularioBase(
          user,
        );

        await user.type(
          screen.getByLabelText(
            /^contraseña$/i,
          ),
          "Password123!",
        );

        await user.type(
          screen.getByLabelText(
            /confirmar contraseña/i,
          ),
          "OtraPassword123!",
        );

        await user.click(
          screen.getByRole(
            "checkbox",
          ),
        );

        await user.click(
          screen.getByRole(
            "button",
            {
              name:
                /crear cuenta y continuar/i,
            },
          ),
        );

        expect(
          await screen.findByRole(
            "alert",
          ),
        ).toHaveTextContent(
          "Las contraseñas no coinciden.",
        );

        expect(
          register,
        ).not.toHaveBeenCalled();
      },
    );


    it(
      "exige autorización para validar la identidad",
      async () => {
        const user =
          userEvent.setup();

        renderRegister();

        await llenarFormularioBase(
          user,
        );

        await user.type(
          screen.getByLabelText(
            /^contraseña$/i,
          ),
          "Password123!",
        );

        await user.type(
          screen.getByLabelText(
            /confirmar contraseña/i,
          ),
          "Password123!",
        );

        await user.click(
          screen.getByRole(
            "button",
            {
              name:
                /crear cuenta y continuar/i,
            },
          ),
        );

        expect(
          await screen.findByRole(
            "alert",
          ),
        ).toHaveTextContent(
          /autorizar la validación de identidad/i,
        );

        expect(
          register,
        ).not.toHaveBeenCalled();
      },
    );


    it(
      "envía correctamente el registro cuando los datos son válidos",
      async () => {
        const user =
          userEvent.setup();

        vi.mocked(register)
          .mockResolvedValue({
            id: "usuario-123",
            nombre: "Maria",
            apellido: "Torres",
            email:
              "maria@solventa.com",
            rol: "CLIENTE",
            kyc_validado: true,
            fecha_creacion:
              "2026-10-10T00:00:00Z",
          });

        renderRegister();

        await llenarFormularioBase(
          user,
        );

        await user.type(
          screen.getByLabelText(
            /^contraseña$/i,
          ),
          "Password123!",
        );

        await user.type(
          screen.getByLabelText(
            /confirmar contraseña/i,
          ),
          "Password123!",
        );

        await user.click(
          screen.getByRole(
            "checkbox",
          ),
        );

        await user.click(
          screen.getByRole(
            "button",
            {
              name:
                /crear cuenta y continuar/i,
            },
          ),
        );

        await waitFor(() => {
          expect(
            register,
          ).toHaveBeenCalledWith({
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
          });
        });

        expect(
          await screen.findByRole(
            "status",
          ),
        ).toHaveTextContent(
          /cuenta creada correctamente/i,
        );
      },
    );


    it(
      "muestra el error entregado por el backend",
      async () => {
        const user =
          userEvent.setup();

        vi.mocked(register)
          .mockRejectedValue(
            new Error(
              "Ya existe un usuario registrado con este correo.",
            ),
          );

        renderRegister();

        await llenarFormularioBase(
          user,
        );

        await user.type(
          screen.getByLabelText(
            /^contraseña$/i,
          ),
          "Password123!",
        );

        await user.type(
          screen.getByLabelText(
            /confirmar contraseña/i,
          ),
          "Password123!",
        );

        await user.click(
          screen.getByRole(
            "checkbox",
          ),
        );

        await user.click(
          screen.getByRole(
            "button",
            {
              name:
                /crear cuenta y continuar/i,
            },
          ),
        );

        expect(
          await screen.findByRole(
            "alert",
          ),
        ).toHaveTextContent(
          /ya existe un usuario/i,
        );
      },
    );

    it(
        "rechaza una contraseña con menos de 8 caracteres",
        async () => {
            const user =
            userEvent.setup();

            renderRegister();

            await llenarFormularioBase(
            user,
            );

            await user.type(
            screen.getByLabelText(
                /^contraseña$/i,
            ),
            "1234567",
            );

            await user.type(
            screen.getByLabelText(
                /confirmar contraseña/i,
            ),
            "1234567",
            );

            const boton =
            screen.getByRole(
                "button",
                {
                name:
                    /crear cuenta y continuar/i,
                },
            );

            const formulario =
            boton.closest("form");

            expect(
            formulario,
            ).not.toBeNull();

            fireEvent.submit(
            formulario!,
            );

            expect(
            await screen.findByRole(
                "alert",
            ),
            ).toHaveTextContent(
            /mínimo 8 caracteres/i,
            );

            expect(
            register,
            ).not.toHaveBeenCalled();
        },
    );
    
    it(
        "permite seleccionar otro tipo de documento",
        async () => {
            const user =
            userEvent.setup();

            renderRegister();

            const tipoDocumento =
            screen.getByLabelText(
                /tipo documento/i,
            );

            await user.selectOptions(
            tipoDocumento,
            "CE",
            );

            expect(
            tipoDocumento,
            ).toHaveValue("CE");
        },
    );

    it(
        "muestra un error genérico cuando ocurre un error desconocido en el registro",
        async () => {
            const user =
            userEvent.setup();

            vi.mocked(register)
            .mockRejectedValue(
                "error-desconocido",
            );

            renderRegister();

            await llenarFormularioBase(
            user,
            );

            await user.type(
            screen.getByLabelText(
                /^contraseña$/i,
            ),
            "Password123!",
            );

            await user.type(
            screen.getByLabelText(
                /confirmar contraseña/i,
            ),
            "Password123!",
            );

            await user.click(
            screen.getByRole(
                "checkbox",
            ),
            );

            await user.click(
            screen.getByRole(
                "button",
                {
                name:
                    /crear cuenta y continuar/i,
                },
            ),
            );

            expect(
            await screen.findByRole(
                "alert",
            ),
            ).toHaveTextContent(
            "No fue posible crear la cuenta.",
            );
        },
    );

    it(
        "redirige al login después de crear correctamente la cuenta",
        async () => {
            const user =
            userEvent.setup();

            vi.mocked(register)
            .mockResolvedValue({
                id: "usuario-123",
                nombre: "Maria",
                apellido: "Torres",
                email:
                "maria@solventa.com",
                rol: "CLIENTE",
                kyc_validado: true,
                fecha_creacion:
                "2026-10-10T00:00:00Z",
            });

            renderRegister();

            await llenarFormularioBase(
            user,
            );

            await user.type(
            screen.getByLabelText(
                /^contraseña$/i,
            ),
            "Password123!",
            );

            await user.type(
            screen.getByLabelText(
                /confirmar contraseña/i,
            ),
            "Password123!",
            );

            await user.click(
            screen.getByRole(
                "checkbox",
            ),
            );

            await user.click(
            screen.getByRole(
                "button",
                {
                name:
                    /crear cuenta y continuar/i,
                },
            ),
            );

            expect(
            await screen.findByRole(
                "status",
            ),
            ).toHaveTextContent(
            /cuenta creada correctamente/i,
            );

            expect(
            await screen.findByRole(
                "heading",
                {
                name:
                    /inicia sesión/i,
                },
                {
                timeout: 2000,
                },
            ),
            ).toBeInTheDocument();
        },
        );
  },
);


async function llenarFormularioBase(
  user: ReturnType<
    typeof userEvent.setup
  >,
) {
  await user.type(
    screen.getByLabelText(
      /^nombre$/i,
    ),
    "Maria",
  );

  await user.type(
    screen.getByLabelText(
      /^apellido$/i,
    ),
    "Torres",
  );

  await user.type(
    screen.getByLabelText(
      /correo electrónico/i,
    ),
    "maria@solventa.com",
  );

  await user.type(
    screen.getByLabelText(
      /número de documento/i,
    ),
    "123456789",
  );

  await user.type(
    screen.getByLabelText(
      /fecha de nacimiento/i,
    ),
    "1995-06-15",
  );
}
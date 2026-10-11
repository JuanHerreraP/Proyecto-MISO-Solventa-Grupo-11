import {
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

import LoginPage from "./LoginPage";

import {
  login,
} from "../services/auth.service";


vi.mock(
  "../services/auth.service",
  () => ({
    login: vi.fn(),
    register: vi.fn(),
  }),
);


function renderLogin() {
  return render(
    <MemoryRouter
      initialEntries={["/login"]}
    >
      <Routes>
        <Route
          path="/login"
          element={<LoginPage />}
        />

        <Route
          path="/home"
          element={
            <h1>
              Inicio Solventa
            </h1>
          }
        />

        <Route
          path="/registro"
          element={
            <h1>
              Crear cuenta
            </h1>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}


describe(
  "LoginPage",
  () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });


    it(
      "muestra el formulario de inicio de sesión",
      () => {
        renderLogin();

        expect(
          screen.getByRole(
            "heading",
            {
              name: /inicia sesión/i,
            },
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByLabelText(
            /correo electrónico/i,
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByLabelText(
            /contraseña/i,
          ),
        ).toBeInTheDocument();

        expect(
          screen.getByRole(
            "button",
            {
              name: /iniciar sesión/i,
            },
          ),
        ).toBeInTheDocument();
      },
    );


    it(
      "envía las credenciales y redirige al home cuando el login es correcto",
      async () => {
        const user =
          userEvent.setup();

        vi.mocked(login)
          .mockResolvedValue({
            access_token:
              "access-token-prueba",

            refresh_token:
              "refresh-token-prueba",

            token_type:
              "bearer",

            expires_in:
              1800,

            refresh_expires_in:
              604800,
          });

        renderLogin();

        await user.type(
          screen.getByLabelText(
            /correo electrónico/i,
          ),
          "maria@solventa.com",
        );

        await user.type(
          screen.getByLabelText(
            /contraseña/i,
          ),
          "Password123!",
        );

        await user.click(
          screen.getByRole(
            "button",
            {
              name: /iniciar sesión/i,
            },
          ),
        );

        await waitFor(() => {
          expect(
            login,
          ).toHaveBeenCalledWith({
            email:
              "maria@solventa.com",

            password:
              "Password123!",
          });
        });

        expect(
          await screen.findByRole(
            "heading",
            {
              name:
                /inicio solventa/i,
            },
          ),
        ).toBeInTheDocument();
      },
    );


    it(
      "muestra error cuando las credenciales son incorrectas",
      async () => {
        const user =
          userEvent.setup();

        vi.mocked(login)
          .mockRejectedValue(
            new Error(
              "El correo electrónico o la contraseña son incorrectos.",
            ),
          );

        renderLogin();

        await user.type(
          screen.getByLabelText(
            /correo electrónico/i,
          ),
          "maria@solventa.com",
        );

        await user.type(
          screen.getByLabelText(
            /contraseña/i,
          ),
          "PasswordIncorrecta",
        );

        await user.click(
          screen.getByRole(
            "button",
            {
              name: /iniciar sesión/i,
            },
          ),
        );

        expect(
          await screen.findByRole(
            "alert",
          ),
        ).toHaveTextContent(
          "El correo electrónico o la contraseña son incorrectos.",
        );
      },
    );


    it(
      "permite navegar hacia la página de registro",
      async () => {
        const user =
          userEvent.setup();

        renderLogin();

        await user.click(
          screen.getByRole(
            "link",
            {
              name:
                /crea tu cuenta/i,
            },
          ),
        );

        expect(
          await screen.findByRole(
            "heading",
            {
              name:
                /crear cuenta/i,
            },
          ),
        ).toBeInTheDocument();
      },
    );

    it(
        "muestra un error genérico cuando ocurre un error desconocido",
        async () => {
            const user =
            userEvent.setup();

            vi.mocked(login)
            .mockRejectedValue(
                "error-desconocido",
            );

            renderLogin();

            await user.type(
            screen.getByLabelText(
                /correo electrónico/i,
            ),
            "maria@solventa.com",
            );

            await user.type(
            screen.getByLabelText(
                /contraseña/i,
            ),
            "Password123!",
            );

            await user.click(
            screen.getByRole(
                "button",
                {
                name: /iniciar sesión/i,
                },
            ),
            );

            expect(
            await screen.findByRole(
                "alert",
            ),
            ).toHaveTextContent(
            "No fue posible iniciar sesión.",
            );
        },
    );
  },
);
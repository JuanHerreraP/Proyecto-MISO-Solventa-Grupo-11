import {
  render,
  screen,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  generarCredencialesSocio,
  registrarSocio,
} from "../services/socios.service";
import SocioRegistrationPage from "./SocioRegistrationPage";

vi.mock("../services/socios.service", () => ({
  generarCredencialesSocio: vi.fn(),
  registrarSocio: vi.fn(),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <SocioRegistrationPage />
    </MemoryRouter>,
  );
}

async function completarDatosBasicos() {
  const user = userEvent.setup();

  await user.type(screen.getByLabelText(/^NIT/i), "900123456-7");
  await user.type(
    screen.getByLabelText(/razón social/i),
    "Banco Andes S.A.",
  );
  await user.type(
    screen.getByLabelText(/nombre completo/i),
    "María Torres",
  );
  await user.type(
    screen.getByLabelText(/correo corporativo/i),
    "maria.torres@bancoandes.com",
  );

  return user;
}

describe("SocioRegistrationPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("muestra los campos necesarios para registrar un socio", () => {
    renderPage();

    expect(
      screen.getByRole("heading", { name: /registrar nuevo socio/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/^NIT/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/razón social/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/país de operación/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/nombre completo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/correo corporativo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/teléfono.*opcional/i)).toBeInTheDocument();
  });

  it("exige seleccionar al menos un tipo de seguro", async () => {
    renderPage();
    const user = await completarDatosBasicos();

    await user.click(
      screen.getByRole("button", { name: /registrar socio/i }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Selecciona al menos un tipo de seguro autorizado.",
    );
    expect(registrarSocio).not.toHaveBeenCalled();
  });

  it("exige seleccionar al menos un permiso de API", async () => {
    renderPage();
    const user = await completarDatosBasicos();

    await user.click(screen.getByLabelText(/seguro de viaje/i));
    await user.click(
      screen.getByRole("button", { name: /registrar socio/i }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Selecciona al menos un permiso de API.",
    );
    expect(registrarSocio).not.toHaveBeenCalled();
  });

  it("envía los datos y muestra la confirmación del registro", async () => {
    vi.mocked(registrarSocio).mockResolvedValue({
      socio_id: "socio-001",
      tenant_id: "tenant-001",
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
      estado: "ACTIVO",
      creado_en: "2026-10-13T00:00:00Z",
      actualizado_en: "2026-10-13T00:00:00Z",
    });
    vi.mocked(generarCredencialesSocio).mockResolvedValue({
      socio_id: "socio-001",
      tenant_id: "tenant-001",
      client_id: "solv_cliente_001",
      client_secret: "solv_secret_unico",
      scopes: ["cotizaciones:crear"],
      creado_en: "2026-10-13T00:00:00Z",
    });

    renderPage();
    const user = await completarDatosBasicos();
    await user.click(screen.getByLabelText(/seguro de viaje/i));
    await user.click(screen.getByLabelText(/cotizar póliza/i));
    await user.click(
      screen.getByRole("button", { name: /registrar socio/i }),
    );

    expect(registrarSocio).toHaveBeenCalledWith({
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
    });
    expect(
      await screen.findByRole("heading", {
        name: /socio registrado correctamente/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("socio-001")).toBeInTheDocument();
    expect(screen.getByText("tenant-001")).toBeInTheDocument();
    expect(generarCredencialesSocio).toHaveBeenCalledWith("socio-001");
    expect(screen.getByText("solv_cliente_001")).toBeInTheDocument();
    expect(screen.getByText("solv_secret_unico")).toBeInTheDocument();
    expect(
      screen.getByText(/client secret no volverá a mostrarse/i),
    ).toBeInTheDocument();
  });

  it("muestra el error entregado por el servicio", async () => {
    vi.mocked(registrarSocio).mockRejectedValue(
      new Error("Ya existe un socio registrado con este NIT."),
    );

    renderPage();
    const user = await completarDatosBasicos();
    await user.click(screen.getByLabelText(/seguro de viaje/i));
    await user.click(screen.getByLabelText(/cotizar póliza/i));
    await user.click(
      screen.getByRole("button", { name: /registrar socio/i }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Ya existe un socio registrado con este NIT.",
    );
  });
});

const SOCIO_PRUEBA: import("../types/socios").RespuestaRegistroSocio = {
  socio_id: "socio-prueba", tenant_id: "tenant-prueba", nit: "900123456-7",
  razon_social: "Banco Andes S.A.", contactos_tecnicos: [{ nombre: "María Torres", correo: "maria.torres@bancoandes.com" }],
  pais_operacion: "CO", tipos_seguros_autorizados: ["VIAJE"], endpoints_autorizados: ["cotizaciones:crear"],
  estado: "ACTIVO", creado_en: "2026-10-13T00:00:00Z", actualizado_en: "2026-10-13T00:00:00Z",
};
const CREDENCIALES_PRUEBA = {
  socio_id: "socio-prueba", tenant_id: "tenant-prueba", client_id: "client-prueba",
  client_secret: "secret-prueba", scopes: SOCIO_PRUEBA.endpoints_autorizados,
  creado_en: "2026-10-13T00:00:00Z",
};

async function enviarFormulario() {
  const user = await completarDatosBasicos();
  await user.click(screen.getByLabelText(/seguro de viaje/i));
  await user.click(screen.getByLabelText(/cotizar póliza/i));
  await user.click(screen.getByRole("button", { name: /registrar socio/i }));
  return user;
}

describe("edición y recuperación del alta de socios", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(registrarSocio).mockResolvedValue(SOCIO_PRUEBA);
    vi.mocked(generarCredencialesSocio).mockResolvedValue(CREDENCIALES_PRUEBA);
  });

  it("edita contactos, país, teléfono y permisos antes de enviar", async () => {
    renderPage();
    const user = await completarDatosBasicos();
    await user.selectOptions(screen.getByLabelText(/país de operación/i), "MX");
    await user.type(screen.getByLabelText(/teléfono.*opcional/i), "+57 300 123 4567");
    await user.click(screen.getByRole("button", { name: /agregar otro contacto/i }));
    await user.type(screen.getAllByLabelText(/nombre completo/i)[1], "Contacto extra");
    expect(screen.getAllByLabelText(/nombre completo/i)).toHaveLength(2);
    await user.click(screen.getAllByRole("button", { name: /eliminar contacto/i })[1]);
    expect(screen.getAllByLabelText(/nombre completo/i)).toHaveLength(1);
    await user.click(screen.getByLabelText(/seguro de viaje/i));
    await user.click(screen.getByLabelText(/protección de dispositivos/i));
    await user.click(screen.getByLabelText(/protección de dispositivos/i));
    await user.click(screen.getByLabelText(/cotizar póliza/i));
    await user.click(screen.getByLabelText(/emitir póliza/i));
    await user.click(screen.getByLabelText(/emitir póliza/i));
    await user.click(screen.getByRole("button", { name: /registrar socio/i }));
    expect(registrarSocio).toHaveBeenCalledWith(expect.objectContaining({
      pais_operacion: "MX", tipos_seguros_autorizados: ["VIAJE"], endpoints_autorizados: ["cotizaciones:crear"],
      contactos_tecnicos: [{ nombre: "María Torres", correo: "maria.torres@bancoandes.com", telefono: "+57 300 123 4567" }],
    }));
  });

  it("presenta un error genérico si el registro falla sin un Error", async () => {
    vi.mocked(registrarSocio).mockRejectedValue("fallo desconocido");
    renderPage();
    await enviarFormulario();
    expect(await screen.findByRole("alert")).toHaveTextContent("No fue posible registrar el socio.");
    expect(generarCredencialesSocio).not.toHaveBeenCalled();
  });

  it.each([new Error("Proveedor no disponible"), "fallo desconocido"])(
    "reintenta las credenciales sin volver a crear al socio (%s)", async (error) => {
      vi.mocked(generarCredencialesSocio).mockRejectedValueOnce(error).mockResolvedValue(CREDENCIALES_PRUEBA);
      renderPage();
      const user = await enviarFormulario();
      expect(await screen.findByRole("alert")).toHaveTextContent(
        error instanceof Error ? error.message : "No fue posible generar las credenciales del socio.",
      );
      await user.click(screen.getByRole("button", { name: /reintentar generación/i }));
      expect(await screen.findByText("secret-prueba")).toBeInTheDocument();
      expect(registrarSocio).toHaveBeenCalledOnce();
      expect(generarCredencialesSocio).toHaveBeenCalledTimes(2);
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    },
  );

  it("copia las credenciales y limpia el secreto al registrar otro socio", async () => {
    renderPage();
    const user = await enviarFormulario();
    const escribir = vi.spyOn(navigator.clipboard, "writeText");
    await user.click(screen.getByRole("button", { name: "Copiar Client ID" }));
    expect(escribir).toHaveBeenLastCalledWith("client-prueba");
    expect(await screen.findByRole("status")).toHaveTextContent("Client ID copiado.");
    await user.click(screen.getByRole("button", { name: "Copiar Client secret" }));
    expect(escribir).toHaveBeenLastCalledWith("secret-prueba");
    expect(await screen.findByRole("status")).toHaveTextContent("Client secret copiado.");
    await user.click(screen.getByRole("button", { name: /registrar otro socio/i }));
    expect(screen.queryByText("secret-prueba")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/^NIT/i)).toHaveValue("");
    expect(screen.getByLabelText(/seguro de viaje/i)).not.toBeChecked();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("impide iniciar otra alta mientras se generan las credenciales", async () => {
    let terminar!: (valor: typeof CREDENCIALES_PRUEBA) => void;
    vi.mocked(generarCredencialesSocio).mockReturnValue(new Promise((resolve) => { terminar = resolve; }));
    renderPage();
    await enviarFormulario();
    expect(await screen.findByRole("status")).toHaveTextContent("Generando credenciales");
    expect(screen.getByRole("button", { name: /registrar otro socio/i })).toBeDisabled();
    const { act } = await import("@testing-library/react");
    await act(async () => terminar(CREDENCIALES_PRUEBA));
    expect(screen.getByRole("button", { name: /registrar otro socio/i })).toBeEnabled();
  });
});

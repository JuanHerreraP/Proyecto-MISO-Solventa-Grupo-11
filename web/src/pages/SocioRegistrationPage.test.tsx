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

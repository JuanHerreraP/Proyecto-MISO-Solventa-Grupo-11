import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import {
  ErrorFirma,
  firmarContrato,
  obtenerContrato,
  solicitarCodigo,
  type ProcesoFirma,
} from "../services/firma.service";
import FirmaPage from "./FirmaPage";

vi.mock("../services/firma.service", async (original) => ({
  ...(await original<typeof import("../services/firma.service")>()),
  obtenerContrato: vi.fn(),
  solicitarCodigo: vi.fn(),
  firmarContrato: vi.fn(),
}));

const HUELLA = "a".repeat(64);

function proceso(cambios: Partial<ProcesoFirma> = {}): ProcesoFirma {
  return {
    firma_id: "FIR-1",
    cotizacion_id: "COT-001",
    estado: "PENDIENTE",
    contrato: {
      version_plantilla: "2026.10",
      cotizacion_id: "COT-001",
      ramo: "VIDA",
      nombre_ramo: "Seguro de vida hipotecario",
      titular: {
        nombre_completo: "Laura Gómez", tipo_documento: "CC", numero_documento: "1020304050",
        email: "laura@example.com", celular: "+57 300 123 4567",
      },
      cobertura_principal: {
        codigo: "VIDA_DEUDORES", nombre: "Vida deudores hipotecario",
        suma_asegurada: "250000000.00", descripcion: null,
      },
      datos_riesgo: { valor_credito: 250000000, plazo_meses: 240 },
      prima_total: "94500.00",
      moneda: "COP",
      pago_id: "PAG-1",
      referencia_pago: "PSP-123",
      fecha_pago: "2027-01-01T14:56:00Z",
      clausulas: ["El beneficiario a título oneroso es la entidad financiera."],
    },
    huella_documento: HUELLA,
    documento_integro: true,
    otp_canal: null,
    otp_destino: null,
    otp_expira_en: null,
    reenvio_disponible_en: null,
    intentos_restantes: 0,
    envios_restantes: 3,
    firmado_en: null,
    ip_firmante: null,
    referencia_proveedor: null,
    ...cambios,
  };
}

const conCodigo = () => proceso({
  otp_canal: "SMS", otp_destino: "*** *** 4567", otp_expira_en: "2099-01-01T15:05:00Z",
  reenvio_disponible_en: "2000-01-01T00:00:00Z", intentos_restantes: 3, envios_restantes: 2,
});

beforeEach(() => vi.clearAllMocks());

function pantalla() {
  render(<MemoryRouter initialEntries={["/firma/COT-001"]}><Routes>
    <Route path="/firma/:cotizacionId" element={<FirmaPage />} />
    <Route path="/pagos" element={<h1>Pagos</h1>} />
  </Routes></MemoryRouter>);
}

it("presenta el contrato prellenado con su huella", async () => {
  vi.mocked(obtenerContrato).mockResolvedValue(proceso());
  pantalla();

  expect(await screen.findByRole("heading", { name: "Firma tu contrato" })).toBeInTheDocument();
  expect(obtenerContrato).toHaveBeenCalledWith("COT-001");
  expect(screen.getByText("Laura Gómez")).toBeInTheDocument();
  expect(screen.getByText("CC 1020304050")).toBeInTheDocument();
  expect(screen.getByText("Valor credito")).toBeInTheDocument();
  expect(screen.getByText(/entidad financiera/)).toBeInTheDocument();
  expect(screen.getByText(HUELLA)).toBeInTheDocument();
});

it("exige autorizar antes de enviar el código", async () => {
  vi.mocked(obtenerContrato).mockResolvedValue(proceso());
  vi.mocked(solicitarCodigo).mockResolvedValue(conCodigo());
  pantalla();

  const enviar = await screen.findByRole("button", { name: "Enviar código" });
  expect(enviar).toBeDisabled();
  await userEvent.click(screen.getByRole("checkbox"));
  await userEvent.click(screen.getByLabelText("Correo electrónico"));
  await userEvent.click(enviar);

  expect(solicitarCodigo).toHaveBeenCalledWith("COT-001", "EMAIL");
  expect(await screen.findByText(/Enviamos un código a \*\*\* \*\*\* 4567/)).toBeInTheDocument();
});

it("firma con el código y la huella del contrato revisado", async () => {
  vi.mocked(obtenerContrato).mockResolvedValue(conCodigo());
  vi.mocked(firmarContrato).mockResolvedValue(proceso({
    estado: "FIRMADA", firmado_en: "2027-01-01T15:02:00Z", referencia_proveedor: "SIM-abc",
  }));
  pantalla();

  const firmar = await screen.findByRole("button", { name: /Firmar contrato/ });
  expect(firmar).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Código de verificación"), "12a3456");
  await userEvent.click(firmar);

  expect(firmarContrato).toHaveBeenCalledWith("COT-001", "123456", HUELLA);
  expect(await screen.findByRole("heading", { name: "Contrato firmado" })).toBeInTheDocument();
  expect(screen.getByText("Referencia de la firma: SIM-abc")).toBeInTheDocument();
});

it("informa los intentos restantes si el código es incorrecto", async () => {
  vi.mocked(obtenerContrato).mockResolvedValue(conCodigo());
  vi.mocked(firmarContrato).mockRejectedValue(
    new ErrorFirma("El código no es correcto.", "OTP_INCORRECTO", 422, 2),
  );
  pantalla();

  await userEvent.type(await screen.findByLabelText("Código de verificación"), "000000");
  await userEvent.click(screen.getByRole("button", { name: /Firmar contrato/ }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "El código no es correcto. Te quedan 2 intentos.",
  );
  expect(screen.getByLabelText("Código de verificación")).toHaveValue("");
});

it("muestra el bloqueo y oculta la firma", async () => {
  vi.mocked(obtenerContrato).mockResolvedValue(conCodigo());
  vi.mocked(firmarContrato).mockRejectedValue(
    new ErrorFirma("El proceso de firma se bloqueó.", "FIRMA_BLOQUEADA", 423),
  );
  pantalla();

  await userEvent.type(await screen.findByLabelText("Código de verificación"), "000000");
  await userEvent.click(screen.getByRole("button", { name: /Firmar contrato/ }));

  expect(await screen.findByText(/se bloqueó por intentos fallidos/)).toBeInTheDocument();
  expect(screen.queryByLabelText("Código de verificación")).not.toBeInTheDocument();
});

it("muestra la firma registrada de un contrato ya firmado", async () => {
  vi.mocked(obtenerContrato).mockResolvedValue(proceso({
    estado: "FIRMADA", firmado_en: "2027-01-01T15:02:00Z", referencia_proveedor: "SIM-abc",
  }));
  pantalla();

  expect(await screen.findByRole("heading", { name: "Contrato firmado" })).toBeInTheDocument();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
});

it("impide firmar un contrato que no coincide con su huella", async () => {
  vi.mocked(obtenerContrato).mockResolvedValue({ ...conCodigo(), documento_integro: false });
  pantalla();

  expect(await screen.findByText(/no coincide con su huella/)).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText("Código de verificación"), "123456");
  expect(screen.getByRole("button", { name: /Firmar contrato/ })).toBeDisabled();
});

it("explica por qué no hay contrato si el pago no está aprobado", async () => {
  vi.mocked(obtenerContrato).mockRejectedValue(
    new ErrorFirma("El contrato se firma después de que el pago de la prima quede aprobado.",
      "PAGO_NO_APROBADO", 409),
  );
  pantalla();

  expect(await screen.findByRole("alert")).toHaveTextContent("pago de la prima quede aprobado");
  await userEvent.click(screen.getByRole("button", { name: "Volver a pagos" }));
  expect(await screen.findByRole("heading", { name: "Pagos" })).toBeInTheDocument();
});

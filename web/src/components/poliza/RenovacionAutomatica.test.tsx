import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  configurarRenovacionAutomatica,
  consultarRenovacionAutomatica,
  descargarDocumentoRenovacion,
  type RenovacionAutomatica as Estado,
} from "../../services/renovacion-automatica.service";
import RenovacionAutomatica from "./RenovacionAutomatica";

vi.mock("../../services/renovacion-automatica.service", () => ({
  consultarRenovacionAutomatica: vi.fn(),
  configurarRenovacionAutomatica: vi.fn(),
  descargarDocumentoRenovacion: vi.fn(),
}));

const ESTADO: Estado = {
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

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(consultarRenovacionAutomatica).mockResolvedValue(ESTADO);
});

describe("RenovacionAutomatica", () => {
  it("muestra que está activa, cuándo se cobra y que falta la tarjeta", async () => {
    render(<RenovacionAutomatica polizaId="POL-1" puedeRegistrarTarjeta />);

    expect(await screen.findByRole("switch", { name: "Renovar automáticamente" })).toBeChecked();
    expect(screen.getByText(/se renovará el 31 de diciembre de 2026/)).toBeInTheDocument();
    expect(screen.getByText("Sin tarjeta registrada")).toBeInTheDocument();
    expect(screen.getByText(/Registra una tarjeta para que podamos renovar/)).toBeInTheDocument();
  });

  it("desactiva la renovación automática", async () => {
    vi.mocked(configurarRenovacionAutomatica).mockResolvedValue({ ...ESTADO, activa: false });
    render(<RenovacionAutomatica polizaId="POL-1" puedeRegistrarTarjeta />);

    await userEvent.click(await screen.findByRole("switch", { name: "Renovar automáticamente" }));

    expect(configurarRenovacionAutomatica).toHaveBeenCalledWith("POL-1", { activa: false });
    expect(await screen.findByText("Desactivaste la renovación automática.")).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: "Renovar automáticamente" })).not.toBeChecked();
    expect(screen.getByText(/deberás renovar tu póliza manualmente/)).toBeInTheDocument();
  });

  it("registra la tarjeta enviando solo el token y los últimos dígitos", async () => {
    vi.mocked(configurarRenovacionAutomatica).mockResolvedValue({
      ...ESTADO,
      tarjeta: { ultimos_digitos: "1111" },
    });
    render(<RenovacionAutomatica polizaId="POL-1" puedeRegistrarTarjeta />);

    await userEvent.click(await screen.findByRole("button", { name: /Registrar tarjeta/ }));
    await userEvent.type(screen.getByLabelText("Número de tarjeta"), "4111111111111111");
    await userEvent.type(screen.getByLabelText("Vencimiento (MM/AA)"), "0829");
    await userEvent.type(screen.getByLabelText("CVV"), "123");
    await userEvent.click(screen.getByRole("button", { name: "Guardar tarjeta" }));

    const [, solicitud] = vi.mocked(configurarRenovacionAutomatica).mock.calls[0];
    expect(solicitud.activa).toBe(true);
    expect(solicitud.tarjeta?.token_tarjeta).toMatch(/^tok_visa_/);
    expect(solicitud.tarjeta?.ultimos_digitos).toBe("1111");
    expect(JSON.stringify(solicitud)).not.toContain("4111111111111111");
    expect(await screen.findByText("Terminada en 1111")).toBeInTheDocument();
  });

  it("el asesor no ve el registro de tarjetas", async () => {
    render(<RenovacionAutomatica polizaId="POL-1" puedeRegistrarTarjeta={false} />);

    await screen.findByRole("switch", { name: "Renovar automáticamente" });
    expect(screen.queryByRole("button", { name: /Registrar tarjeta/ })).not.toBeInTheDocument();
  });

  it("muestra el resultado de la renovación y descarga su documento", async () => {
    vi.mocked(consultarRenovacionAutomatica).mockResolvedValue({
      ...ESTADO,
      tarjeta: { ultimos_digitos: "4242" },
      ultimo_ciclo: {
        vence_el: "2026-12-31",
        estado: "RENOVADA",
        preaviso_enviado_en: "2026-12-01T15:00:00Z",
        prima_avisada: "420000.00",
        moneda: "COP",
        renovacion_id: "REN-POL-1-20270101",
        motivo: null,
        documento_disponible: true,
        contrato_enviado_en: "2026-12-31T15:00:00Z",
      },
    });
    render(<RenovacionAutomatica polizaId="POL-1" puedeRegistrarTarjeta />);

    expect(await screen.findByText(/se renovó automáticamente/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Descargar renovación/ }));

    expect(descargarDocumentoRenovacion).toHaveBeenCalledWith("POL-1", "REN-POL-1-20270101");
  });

  it("avisa cuando la tarjeta fue rechazada", async () => {
    vi.mocked(consultarRenovacionAutomatica).mockResolvedValue({
      ...ESTADO,
      ultimo_ciclo: {
        vence_el: "2026-12-31",
        estado: "COBRO_RECHAZADO",
        preaviso_enviado_en: null,
        prima_avisada: null,
        moneda: null,
        renovacion_id: "REN-1",
        motivo: "La tarjeta fue rechazada (FONDOS_INSUFICIENTES).",
        documento_disponible: false,
        contrato_enviado_en: null,
      },
    });
    render(<RenovacionAutomatica polizaId="POL-1" puedeRegistrarTarjeta />);

    expect(await screen.findByText(/La tarjeta fue rechazada. Registra otra/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Descargar renovación/ })).not.toBeInTheDocument();
  });

  it("muestra el error del servidor si no puede guardar", async () => {
    vi.mocked(configurarRenovacionAutomatica).mockRejectedValue(new Error("Servicio no disponible."));
    render(<RenovacionAutomatica polizaId="POL-1" puedeRegistrarTarjeta />);

    await userEvent.click(await screen.findByRole("switch", { name: "Renovar automáticamente" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Servicio no disponible.");
    expect(screen.getByRole("switch", { name: "Renovar automáticamente" })).toBeChecked();
  });

  it("no se muestra para seguros que no se renuevan", async () => {
    vi.mocked(consultarRenovacionAutomatica).mockResolvedValue({ ...ESTADO, disponible: false });
    const { container } = render(<RenovacionAutomatica polizaId="POL-1" puedeRegistrarTarjeta />);

    await vi.waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});

import { execFileSync } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import type { APIRequestContext, APIResponse } from "@playwright/test";

const API_URL = process.env.E2E_API_URL ?? process.env.VITE_API_URL ?? "http://localhost:8000";
const INFRA_DIR = fileURLToPath(new URL("../../../infra/", import.meta.url));

export const TEST_PASSWORD = "SolventaE2E-1234";

export interface TestUser {
  id: string;
  nombre: string;
  apellido: string;
  email: string;
  password: string;
  rol: string;
  documento: string;
}

interface LoginResponse {
  access_token: string;
}

interface QuoteResponse {
  cotizacion_id: string;
}

interface SignatureResponse {
  firma_id: string;
  huella_documento: string;
  poliza_id: string | null;
}

async function body(response: APIResponse): Promise<string> {
  return response.text().catch(() => "<sin cuerpo>");
}

async function expectStatus(response: APIResponse, expected: number, action: string): Promise<void> {
  if (response.status() !== expected) {
    throw new Error(`${action}: HTTP ${response.status()} - ${await body(response)}`);
  }
}

function approvedDocument(seed: string): string {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const document = `${seed.replace(/\D/g, "").slice(-8)}${attempt.toString().padStart(2, "0")}`;
    const bucket = BigInt(`0x${createHash("sha256").update(document).digest("hex")}`) % 10n;
    if (bucket < 7n) return document;
  }
  throw new Error("No fue posible generar un documento aprobado por el KYC simulado.");
}

function futureDate(days: number): string {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function uniqueUser(role = "CLIENTE"): TestUser {
  const suffix = `${Date.now()}${Math.floor(Math.random() * 10_000)}`;
  return {
    id: "",
    nombre: role === "ASESOR_VENTAS" ? "Andrea" : "Cliente",
    apellido: `E2E${suffix.slice(-5)}`,
    email: `e2e.${role.toLowerCase()}.${suffix}@solventa.co`,
    password: TEST_PASSWORD,
    rol: role,
    documento: approvedDocument(suffix),
  };
}

export class SolventaApi {
  private readonly request: APIRequestContext;

  constructor(request: APIRequestContext) {
    this.request = request;
  }

  private headers(token: string): Record<string, string> {
    return { Authorization: `Bearer ${token}` };
  }

  async registerClient(user = uniqueUser()): Promise<TestUser> {
    const response = await this.request.post(`${API_URL}/api/v1/auth/register`, {
      data: this.registrationData(user),
    });
    await expectStatus(response, 201, "Registrar cliente");
    const created = await response.json() as { id: string };
    return { ...user, id: created.id };
  }

  async login(user: Pick<TestUser, "email" | "password">): Promise<string> {
    const response = await this.request.post(`${API_URL}/api/v1/auth/login`, {
      data: { email: user.email, password: user.password },
    });
    await expectStatus(response, 200, `Autenticar ${user.email}`);
    return ((await response.json()) as LoginResponse).access_token;
  }

  async createAdvisor(): Promise<TestUser> {
    const email = process.env.E2E_ADMIN_EMAIL;
    const password = process.env.E2E_ADMIN_PASSWORD;
    if (!email || !password) {
      throw new Error("Configure E2E_ADMIN_EMAIL y E2E_ADMIN_PASSWORD para probar el flujo asesor.");
    }
    const adminToken = await this.login({ email, password });
    const advisor = uniqueUser("ASESOR_VENTAS");
    const response = await this.request.post(`${API_URL}/api/v1/auth/users`, {
      headers: this.headers(adminToken),
      data: { ...this.registrationData(advisor), rol: advisor.rol },
    });
    await expectStatus(response, 201, "Crear asesor");
    const created = await response.json() as { id: string };
    return { ...advisor, id: created.id };
  }

  async associateClient(advisorToken: string, client: TestUser): Promise<void> {
    const response = await this.request.post(`${API_URL}/api/v1/asesor/clientes`, {
      headers: this.headers(advisorToken),
      data: { email: client.email },
    });
    await expectStatus(response, 201, "Asociar cliente al asesor");
  }

  async createQuote(
    client: TestUser,
    actorToken?: string,
    risk: Record<string, unknown> = this.travelRisk(),
  ): Promise<string> {
    const token = actorToken ?? await this.login(client);
    const response = await this.request.post(`${API_URL}/api/v1/cotizaciones`, {
      headers: this.headers(token),
      data: { cliente_id: client.id, ramo: "VIAJE", datos_riesgo: risk },
    });
    await expectStatus(response, 201, "Crear cotización");
    return ((await response.json()) as QuoteResponse).cotizacion_id;
  }

  async issuePolicy(
    client: TestUser,
    advisorToken?: string,
    risk: Record<string, unknown> = this.travelRisk(),
  ): Promise<{ policyId: string; quoteId: string }> {
    const clientToken = await this.login(client);
    const quoteId = await this.createQuote(client, advisorToken ?? clientToken, risk);

    const paymentResponse = await this.request.post(`${API_URL}/api/v1/pagos`, {
      headers: {
        ...this.headers(clientToken),
        "Idempotency-Key": randomUUID(),
      },
      data: {
        cotizacion_id: quoteId,
        metodo: "TARJETA",
        token_tarjeta: `tok_visa_${randomUUID().replaceAll("-", "")}`,
      },
    });
    await expectStatus(paymentResponse, 201, "Pagar cotización");

    const contractResponse = await this.request.get(`${API_URL}/api/v1/firmas/${quoteId}`, {
      headers: this.headers(clientToken),
    });
    await expectStatus(contractResponse, 200, "Presentar contrato");
    const contract = await contractResponse.json() as SignatureResponse;

    const otpResponse = await this.request.post(`${API_URL}/api/v1/firmas/${quoteId}/otp`, {
      headers: this.headers(clientToken),
      data: { canal: "EMAIL" },
    });
    await expectStatus(otpResponse, 200, "Solicitar OTP");
    const otpProcess = await otpResponse.json() as SignatureResponse;
    const otp = readOtp(otpProcess.firma_id);

    const signatureResponse = await this.request.post(`${API_URL}/api/v1/firmas/${quoteId}/firma`, {
      headers: this.headers(clientToken),
      data: { codigo: otp, huella_documento: contract.huella_documento },
    });
    await expectStatus(signatureResponse, 200, "Firmar contrato");
    const signature = await signatureResponse.json() as SignatureResponse;
    if (!signature.poliza_id) throw new Error("La firma terminó sin emitir una póliza.");
    return { policyId: signature.poliza_id, quoteId };
  }

  travelRisk(startInDays = 30, endInDays = 40): Record<string, unknown> {
    return {
      destino: "México",
      fecha_inicio: futureDate(startInDays),
      fecha_fin: futureDate(endInDays),
      numero_viajeros: 1,
      valor_asegurado: 20_000_000,
    };
  }

  private registrationData(user: TestUser): Record<string, unknown> {
    return {
      nombre: user.nombre,
      apellido: user.apellido,
      email: user.email,
      password: user.password,
      tipo_documento: "CC",
      numero_documento: user.documento,
      fecha_nacimiento: "1994-02-21",
      celular: "3163033692",
      acepta_validacion_identidad: true,
      selfie_base64: null,
    };
  }
}

export function readOtp(signatureId: string): string {
  if (process.env.E2E_OTP) return process.env.E2E_OTP;
  let logs: string;
  try {
    logs = execFileSync(
      "docker",
      ["compose", "--env-file", ".env.local", "-f", "compose.local.yaml", "logs", "--since", "2m", "backend"],
      { cwd: INFRA_DIR, encoding: "utf8" },
    );
  } catch (error) {
    throw new Error("No se pudo leer el OTP local. Levante Docker o configure E2E_OTP.", { cause: error });
  }
  const match = logs.match(new RegExp(`\\[FIRMA SIMULADA] OTP (\\d{6}).*\\(proceso ${escapeRegex(signatureId)}\\)`));
  if (!match) throw new Error(`No se encontró el OTP del proceso ${signatureId} en el log local.`);
  return match[1];
}

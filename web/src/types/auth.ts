export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  refresh_expires_in: number;
}

export interface RegisterRequest {
  nombre: string;
  apellido: string;
  email: string;
  password: string;
  tipo_documento: string;
  numero_documento: string;
  fecha_nacimiento: string;
  acepta_validacion_identidad: boolean;
}

export interface RegisterResponse {
  id: string;
  nombre: string;
  apellido: string;
  email: string;
  rol: string;
  kyc_validado: boolean;
  fecha_creacion: string;
}

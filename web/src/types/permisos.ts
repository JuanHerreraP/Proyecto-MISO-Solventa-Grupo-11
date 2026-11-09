export const ROLES_ADMINISTRACION_SOCIOS = ["INGENIERO_INTEGRACIONES", "SERVICIO_INTERNO"] as const;

// Solo el manager (SERVICIO_INTERNO) puede crear usuarios administrativos como el asesor.
export const ROLES_CREAR_ASESOR = ["SERVICIO_INTERNO"] as const;
export const ROLES_CLIENTE = ["CLIENTE"] as const;
export const ROLES_OPERACIONES_SINIESTROS = ["OPERACIONES_SINIESTROS"] as const;

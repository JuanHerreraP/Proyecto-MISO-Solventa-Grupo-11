/**
 * Simula la tokenización que haría el SDK de la pasarela: el número de la tarjeta nunca se
 * envía al backend, solo un token y los últimos cuatro dígitos para reconocerla.
 * Para desarrollo, una tarjeta terminada en 0 queda como tarjeta sin fondos (cobro rechazado).
 */
export function tokenizarTarjeta(numero: string): string {
  const digitos = numero.replace(/\D/g, "");
  const prefijo = digitos.endsWith("0") ? "tok_rechazado" : "tok_visa";
  const aleatorio = crypto.randomUUID().replace(/-/g, "").slice(0, 16);
  return `${prefijo}_${aleatorio}`;
}

export function ultimosDigitos(numero: string): string {
  return numero.replace(/\D/g, "").slice(-4);
}

/** Agrupa los dígitos del número de tarjeta en bloques de 4 para mostrarlos. */
export function formatearNumeroTarjeta(valor: string): string {
  const digitos = valor.replace(/\D/g, "").slice(0, 16);
  return digitos.replace(/(.{4})/g, "$1 ").trim();
}

/** Formatea el vencimiento como MM/AA mientras se escribe. */
export function formatearVencimiento(valor: string): string {
  const digitos = valor.replace(/\D/g, "").slice(0, 4);
  if (digitos.length <= 2) return digitos;
  return `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
}

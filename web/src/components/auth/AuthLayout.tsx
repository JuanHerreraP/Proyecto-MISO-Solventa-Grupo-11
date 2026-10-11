import type { ReactNode } from "react";

import "../../styles/auth.css";

interface AuthLayoutProps {
  children: ReactNode;
  title?: string;
  description?: string;
  benefits?: string[];
}

export default function AuthLayout({
  children,
  title = "Seguros que se ajustan a tu vida",
  description =
    "Cotiza, contrata y gestiona tu protección desde un solo lugar, con la información de tu perfil financiero trabajando a tu favor.",
  benefits = [
    "Cotización personalizada en minutos",
    "Autorización de datos 100% transparente",
    "Emisión y firma electrónica del contrato",
  ],
}: AuthLayoutProps) {
  return (
    <main className="auth-page">
      <section className="auth-brand">
        <div className="brand-logo">
          <span className="material-symbols-outlined brand-symbol">
            shield
          </span>
        </div>

        <div className="brand-content">
          <h1>{title}</h1>

          <p className="brand-description">
            {description}
          </p>

          <div className="brand-benefits">
            {benefits.map((benefit) => (
              <p key={benefit}>
                {benefit}
              </p>
            ))}
          </div>
        </div>

        <footer className="brand-footer">
          © 2026 Solventa S.A. Todos los derechos reservados.
        </footer>
      </section>

      <section className="auth-content">
        {children}
      </section>
    </main>
  );
}
import type { ReactNode } from "react";

import "../../styles/auth.css";

import { t } from "../../i18n";
import SelectorIdioma from "../../i18n/SelectorIdioma";

interface AuthLayoutProps {
  children: ReactNode;
  title?: string;
  description?: string;
  benefits?: string[];
}

export default function AuthLayout({
  children,
  title = t("authLayout.seguros_que_se_ajustan_a"),
  description =
    t("authLayout.cotiza_contrata_y_gestiona_tu"),
  benefits = [
    t("authLayout.cotizacion_personalizada_en_minutos"),
    t("authLayout.autorizacion_de_datos_100_transparente"),
    t("authLayout.emision_y_firma_electronica_del"),
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
          {t("authLayout.2026_solventa_s_a_todos")}
        </footer>
      </section>

      <section className="auth-content">
        <SelectorIdioma className="auth-selector-idioma" />
        {children}
      </section>
    </main>
  );
}
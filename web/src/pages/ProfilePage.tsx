import { useEffect, useState, type PropsWithChildren } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import "../styles/profile.css";

import { idiomaActual, t } from "../i18n";
import SelectorIdioma from "../i18n/SelectorIdioma";

const disponible = (valor?: string) => valor?.trim() || t("profilePage.no_disponible");

function nombreRol(rol: string): string {
  return rol.split("_").map((palabra) =>
    palabra.charAt(0) + palabra.slice(1).toLowerCase()
  ).join(" ");
}

function iniciales(perfil: Perfil): string {
  return [perfil.nombre?.[0], perfil.apellido?.[0]].filter(Boolean).join("").toUpperCase() || "S";
}

export default function ProfilePage() {
  const navigate = useNavigate();
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      (datos) => { if (activo) setPerfil(datos); },
      (fallo: Error) => { if (activo) setError(fallo.message); },
    );
    return () => { activo = false; };
  }, []);

  if (error) {
    return (
      <AppLayout activo="Perfil" rol={null}>
        <p role="alert" className="home-aviso">{error}</p>
        <button type="button" className="profile-link" onClick={() => navigate("/login", { replace: true })}>
          {t("profilePage.volver_al_ingreso")}
        </button>
      </AppLayout>
    );
  }

  return (
    <AppLayout activo="Perfil" rol={perfil?.rol ?? null}>
      <div className="profile-page">
        <header className="home-header">
          <div>
            <h1>{t("profilePage.perfil_y_preferencias")}</h1>
            <p>{t("profilePage.consulta_los_datos_y_preferencias")}</p>
          </div>
        </header>

        {!perfil ? <p role="status">{t("profilePage.cargando_tu_perfil")}</p> : (
          <>
            <section className="profile-identity" aria-label={t("profilePage.identidad_de_la_cuenta")}>
              <span className="profile-avatar" aria-hidden="true">{iniciales(perfil)}</span>
              <div>
                <strong>{nombreRol(perfil.rol)}</strong>
                <span>{disponible(`${perfil.nombre ?? ""} ${perfil.apellido ?? ""}`)}</span>
                <small>{disponible(perfil.email)}</small>
              </div>
            </section>

            <div className="profile-grid">
              <Tarjeta titulo={t("profilePage.datos_personales")} icono="person">
                <Datos items={[
                  [t("profilePage.nombre_completo"), disponible(`${perfil.nombre ?? ""} ${perfil.apellido ?? ""}`)],
                  [t("profilePage.correo_electronico"), disponible(perfil.email)],
                  [t("profilePage.documento_de_identidad"), disponible(
                    [perfil.tipo_documento, perfil.numero_documento].filter(Boolean).join(" ")
                  )],
                  [t("profilePage.telefono"), disponible(perfil.celular)],
                ]} />
              </Tarjeta>

              <Tarjeta titulo={t("profilePage.seguridad_y_privacidad")} icono="shield">
                <Datos items={[
                  [t("profilePage.sesion"), t("profilePage.acceso_autenticado")],
                  [t("profilePage.datos_sin_conexion"), t("profilePage.no_almacenados_en_la_web")],
                ]} />
              </Tarjeta>

              <Tarjeta titulo={t("profilePage.idioma_y_moneda")} icono="language">
                <Datos items={[
                  [t("profilePage.idioma"), t(`idioma.nombre.${idiomaActual()}`)],
                  [t("profilePage.moneda"), t("profilePage.peso_colombiano_cop")],
                ]} />
                <SelectorIdioma className="profile-selector-idioma" />
              </Tarjeta>

              <Tarjeta titulo={t("profilePage.notificaciones")} icono="notifications" deshabilitada>
                <p>{t("profilePage.disponible_proximamente")}</p>
              </Tarjeta>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}

function Tarjeta({
  titulo,
  icono,
  deshabilitada = false,
  children,
}: PropsWithChildren<{ titulo: string; icono: string; deshabilitada?: boolean }>) {
  return (
    <section className={`profile-card${deshabilitada ? " profile-card-disabled" : ""}`}>
      <div className="profile-card-title">
        <span className="material-symbols-outlined" aria-hidden="true">{icono}</span>
        <h2>{titulo}</h2>
      </div>
      {children}
    </section>
  );
}

function Datos({ items }: { items: string[][] }) {
  return (
    <dl className="profile-data-grid">
      {items.map(([etiqueta, valor]) => <div key={etiqueta}><dt>{etiqueta}</dt><dd>{valor}</dd></div>)}
    </dl>
  );
}

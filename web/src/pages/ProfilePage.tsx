import { useEffect, useState, type PropsWithChildren } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { obtenerPerfil, type Perfil } from "../services/auth.service";
import "../styles/profile.css";

const disponible = (valor?: string) => valor?.trim() || "No disponible";

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
          Volver al ingreso
        </button>
      </AppLayout>
    );
  }

  return (
    <AppLayout activo="Perfil" rol={perfil?.rol ?? null}>
      <div className="profile-page">
        <header className="home-header">
          <div>
            <h1>Perfil y preferencias</h1>
            <p>Consulta los datos y preferencias asociados a tu cuenta.</p>
          </div>
        </header>

        {!perfil ? <p role="status">Cargando tu perfil…</p> : (
          <>
            <section className="profile-identity" aria-label="Identidad de la cuenta">
              <span className="profile-avatar" aria-hidden="true">{iniciales(perfil)}</span>
              <div>
                <strong>{nombreRol(perfil.rol)}</strong>
                <span>{disponible(`${perfil.nombre ?? ""} ${perfil.apellido ?? ""}`)}</span>
                <small>{disponible(perfil.email)}</small>
              </div>
            </section>

            <div className="profile-grid">
              <Tarjeta titulo="Datos personales" icono="person">
                <Datos items={[
                  ["Nombre completo", disponible(`${perfil.nombre ?? ""} ${perfil.apellido ?? ""}`)],
                  ["Correo electrónico", disponible(perfil.email)],
                  ["Documento de identidad", disponible(
                    [perfil.tipo_documento, perfil.numero_documento].filter(Boolean).join(" ")
                  )],
                  ["Teléfono", disponible(perfil.celular)],
                ]} />
              </Tarjeta>

              <Tarjeta titulo="Seguridad y privacidad" icono="shield">
                <Datos items={[
                  ["Sesión", "Acceso autenticado"],
                  ["Datos sin conexión", "No almacenados en la web"],
                ]} />
              </Tarjeta>

              <Tarjeta titulo="Idioma y moneda" icono="language">
                <Datos items={[
                  ["Idioma", "Español (Colombia)"],
                  ["Moneda", "Peso colombiano (COP)"],
                ]} />
              </Tarjeta>

              <Tarjeta titulo="Notificaciones" icono="notifications" deshabilitada>
                <p>Disponible próximamente</p>
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

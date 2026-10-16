import { useEffect, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { obtenerPerfil } from "../../services/auth.service";

type Props = { children: ReactNode; roles?: readonly string[] };

function ComprobarAcceso({ children, roles }: Props) {
  const [estado, setEstado] = useState<"pendiente" | "permitido" | "sin-sesion" | "denegado">("pendiente");
  useEffect(() => {
    let activo = true;
    obtenerPerfil().then(
      ({ rol }) => {
        if (activo) setEstado(!roles || roles.includes(rol) ? "permitido" : "denegado");
      },
      () => { if (activo) setEstado("sin-sesion"); },
    );
    return () => { activo = false; };
  }, [roles]);

  if (estado === "pendiente") return <p role="status">Verificando acceso…</p>;
  if (estado === "sin-sesion") return <Navigate to="/login" replace />;
  if (estado === "denegado") {
    return <Navigate to="/home" state={{ accesoDenegado: true }} replace />;
  }
  return children;
}

export default function RutaProtegida(props: Props) {
  const { pathname } = useLocation();
  // Cada destino se valida antes de montar la pantalla, sin reutilizar un permiso anterior.
  return <ComprobarAcceso key={pathname} {...props} />;
}

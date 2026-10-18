"""Materializa las llaves inyectadas por ECS sin guardarlas en la imagen."""

import os
import tempfile
from pathlib import Path
from urllib.parse import quote


def main() -> None:
    if os.environ.get("DB_HOST"):
        usuario = quote(os.environ.get("DB_USER", "solventa"), safe="")
        password = quote(os.environ.pop("DB_PASSWORD"), safe="")
        os.environ["DATABASE_URL"] = (
            f"postgresql+psycopg://{usuario}:{password}@{os.environ['DB_HOST']}"
            ":5432/solventa?sslmode=require"
        )
    directorio = None
    for tipo in ("PRIVATE", "PUBLIC"):
        valor = os.environ.pop(f"JWT_{tipo}_KEY_PEM", None)
        if valor:
            if directorio is None:
                directorio = Path(tempfile.mkdtemp(prefix="solventa-jwt-"))
            ruta = directorio / f"{tipo.lower()}.pem"
            ruta.touch(mode=0o600)
            ruta.write_text(valor)
            os.environ[f"JWT_{tipo}_KEY_PATH"] = str(ruta)
    os.execvp(
        "uvicorn",
        [
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--no-proxy-headers",
        ],
    )


if __name__ == "__main__":
    main()

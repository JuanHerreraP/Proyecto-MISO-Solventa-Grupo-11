"""Backend de Solventa."""

from pathlib import Path

from dotenv import load_dotenv

# Carga backend/.env en desarrollo lo antes posible (antes de importar cualquier submódulo
# que lea os.getenv). No sobreescribe variables ya definidas en el entorno real, por lo que
# en producción siguen mandando los valores exportados por el despliegue.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

__version__ = "0.1.0"

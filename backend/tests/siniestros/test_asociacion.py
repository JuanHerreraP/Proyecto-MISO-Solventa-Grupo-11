"""Pruebas de la asociación asesor-cliente y del bootstrap del manager (HU20)."""

from app.identidad.asociacion import (
    ClienteDeAsesor,
    RepositorioAsesorClienteEnMemoria,
)


def test_asociar_y_verificar() -> None:
    repo = RepositorioAsesorClienteEnMemoria()
    assert repo.existe_asociacion("ASE-1", "CLI-1") is False
    repo.asociar("ASE-1", "CLI-1")
    assert repo.existe_asociacion("ASE-1", "CLI-1") is True
    # Otra pareja no queda asociada por error.
    assert repo.existe_asociacion("ASE-2", "CLI-1") is False


def test_asociar_es_idempotente() -> None:
    repo = RepositorioAsesorClienteEnMemoria()
    repo.asociar("ASE-1", "CLI-1")
    repo.asociar("ASE-1", "CLI-1")
    assert len(repo.listar_clientes_de_asesor("ASE-1")) == 1


def test_listar_clientes_ordena_por_nombre() -> None:
    repo = RepositorioAsesorClienteEnMemoria()
    repo.asociar(
        "ASE-1",
        "CLI-2",
        ClienteDeAsesor(cliente_id="CLI-2", nombre="Zoe", apellido="Zapata", email="z@x.com"),
    )
    repo.asociar(
        "ASE-1",
        "CLI-1",
        ClienteDeAsesor(cliente_id="CLI-1", nombre="Ana", apellido="Alvarez", email="a@x.com"),
    )
    nombres = [c.nombre for c in repo.listar_clientes_de_asesor("ASE-1")]
    assert nombres == ["Ana", "Zoe"]

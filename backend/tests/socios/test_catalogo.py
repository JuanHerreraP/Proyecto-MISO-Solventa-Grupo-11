from app.socios.dominio.catalogo import CodigoEndpoint, MetodoHttp, consultar_catalogo


def test_catalogo_expone_cotizacion_y_emision() -> None:
    catalogo = consultar_catalogo()

    assert {endpoint.codigo for endpoint in catalogo} == {
        CodigoEndpoint.COTIZACIONES_CREAR,
        CodigoEndpoint.POLIZAS_EMITIR,
    }
    assert all(endpoint.metodo is MetodoHttp.POST for endpoint in catalogo)


def test_catalogo_no_repite_codigos_ni_rutas() -> None:
    catalogo = consultar_catalogo()
    codigos = [endpoint.codigo for endpoint in catalogo]
    contratos = [(endpoint.metodo, endpoint.ruta) for endpoint in catalogo]

    assert len(codigos) == len(set(codigos))
    assert len(contratos) == len(set(contratos))

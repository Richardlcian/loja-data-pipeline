import pandas as pd

from src import transform, validate

SKUS = {"CEL-001"}


def _linha(**sobrescrever):
    linha = {"data": "2026-11-03", "id_venda": "V1", "sku": "CEL-001", "quantidade": "1",
             "preco_unitario": "1500", "desconto": "0", "forma_pagamento": "Pix",
             "vendedor": "Maria", "cliente": "João"}
    linha.update(sobrescrever)
    return linha


def _validar(*linhas):
    df = transform.normalizar_vendas(pd.DataFrame(linhas))
    return validate.validar_vendas(df, SKUS)


def test_linha_correta_passa():
    validas, rejeitadas = _validar(_linha())
    assert len(validas) == 1 and len(rejeitadas) == 0


def test_rejeita_cada_tipo_de_erro():
    casos = {
        "SKU inexistente": _linha(id_venda="V2", sku="XXX-999"),
        "quantidade inválida": _linha(id_venda="V3", quantidade="0"),
        "pagamento inválido": _linha(id_venda="V4", forma_pagamento="Cheque"),
        "data inválida": _linha(id_venda="V5", data="31/02/2026"),
        "preço inválido": _linha(id_venda="V6", preco_unitario="-5"),
        "desconto inválido": _linha(id_venda="V7", desconto="9999"),
        "id_venda vazio": _linha(id_venda=""),
    }
    for motivo, linha in casos.items():
        validas, rejeitadas = _validar(linha)
        assert len(validas) == 0, motivo
        assert motivo in rejeitadas.iloc[0]["motivo_rejeicao"], motivo


def test_rejeita_linha_duplicada_e_mantem_a_primeira():
    validas, rejeitadas = _validar(_linha(), _linha())
    assert len(validas) == 1 and len(rejeitadas) == 1
    assert "linha duplicada" in rejeitadas.iloc[0]["motivo_rejeicao"]


def test_pagamento_somente_pix_cartao_e_dinheiro():
    for forma in ["Pix", "Cartão de débito", "Cartão de crédito", "Dinheiro"]:
        validas, _ = _validar(_linha(forma_pagamento=forma))
        assert len(validas) == 1
    _, rejeitadas = _validar(_linha(forma_pagamento="Boleto"))
    assert len(rejeitadas) == 1

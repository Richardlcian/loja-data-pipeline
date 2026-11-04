import pandas as pd

from src import transform


def _vendas_brutas(**sobrescrever):
    linha = {"data": "2026-11-03", "id_venda": "V1", "sku": " cel-001 ", "quantidade": "2",
             "preco_unitario": "1500.00", "desconto": "100", "forma_pagamento": "Pix",
             "vendedor": "Maria", "cliente": "João"}
    linha.update(sobrescrever)
    return pd.DataFrame([linha])


def test_valor_e_custo_total_consideram_desconto_e_quantidade():
    produtos = pd.DataFrame({"sku": ["CEL-001"], "custo_unitario": [900.0]})
    vendas = transform.normalizar_vendas(_vendas_brutas())
    r = transform.calcular_vendas(vendas, produtos)
    assert r.loc[0, "sku"] == "CEL-001"          # espaços removidos e maiúsculas
    assert r.loc[0, "valor_total"] == 2900.0     # 2 x 1500 - 100
    assert r.loc[0, "custo_total"] == 1800.0     # 2 x 900


def test_numero_aceita_rs_e_separador_de_milhar():
    v = transform.normalizar_vendas(_vendas_brutas(preco_unitario="R$ 1,499.00"))
    assert v.loc[0, "preco_unitario"] == 1499.0


def test_numero_invalido_vira_nan():
    v = transform.normalizar_vendas(_vendas_brutas(preco_unitario="abc"))
    assert pd.isna(v.loc[0, "preco_unitario"])


def test_desconto_em_branco_vira_zero():
    v = transform.normalizar_vendas(_vendas_brutas(desconto=""))
    assert v.loc[0, "desconto"] == 0


def test_dim_tempo_inclui_datas_de_vendas_e_compras():
    dim = transform.gerar_dim_tempo(pd.Series(["2026-11-03"]), pd.Series(["2026-11-01", "2026-11-03"]))
    assert list(dim["data"]) == ["2026-11-01", "2026-11-03"]
    assert dim.loc[1, "nome_dia"] == "Terça"

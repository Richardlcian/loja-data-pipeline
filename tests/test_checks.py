from datetime import date

import pandas as pd

from src import checks, load, pipeline


def _dados(preco="1499", qtd_venda="1", qtd_compra="5", linhas_ruins=0):
    produtos = pd.DataFrame({"sku": ["CEL-001"], "nome": ["Celular"], "categoria": ["Celular"],
                             "marca": ["Alfa"], "custo_unitario": ["900"], "preco_tabela": ["1499"]})
    vendas = pd.DataFrame({"data": ["2026-11-03"], "id_venda": ["V1"], "sku": ["CEL-001"],
                           "quantidade": [qtd_venda], "preco_unitario": [preco], "desconto": ["0"],
                           "forma_pagamento": ["Pix"], "vendedor": ["Maria"], "cliente": ["a"]})
    for i in range(linhas_ruins):  # linhas com SKU inexistente
        ruim = vendas.iloc[[0]].copy()
        ruim["id_venda"] = f"X{i}"
        ruim["sku"] = "XXX-999"
        vendas = pd.concat([vendas, ruim], ignore_index=True)
    compras = pd.DataFrame({"data": ["2026-11-01"], "sku": ["CEL-001"], "quantidade": [qtd_compra],
                            "custo_unitario": ["900"], "fornecedor": ["Distribuidora"]})
    return {"produtos": produtos, "vendas": vendas, "compras": compras}


def _alertas(dados, hoje=date(2026, 11, 4), verificar_frescor=True):
    con = load.conectar(":memory:")
    resumo = pipeline.executar(dados, con)
    return checks.verificar(con, resumo, verificar_frescor=verificar_frescor, hoje=hoje)


def test_dados_saudaveis_nao_geram_alerta():
    assert _alertas(_dados()) == []


def test_alerta_de_dados_parados():
    alertas = _alertas(_dados(), hoje=date(2026, 11, 20))
    assert len(alertas) == 1 and "Sem venda registrada há 17 dias" in alertas[0]


def test_frescor_pode_ser_desligado_para_dados_ficticios():
    assert _alertas(_dados(), hoje=date(2026, 11, 20), verificar_frescor=False) == []


def test_alerta_de_estoque_negativo():
    alertas = _alertas(_dados(qtd_venda="3", qtd_compra="1"))
    assert any("estoque negativo" in a and "CEL-001" in a for a in alertas)


def test_alerta_de_venda_abaixo_do_custo():
    alertas = _alertas(_dados(preco="800"))
    assert any("abaixo do custo" in a and "V1" in a for a in alertas)


def test_alerta_de_muitas_linhas_rejeitadas():
    alertas = _alertas(_dados(linhas_ruins=1))      # 1 de 2 linhas = 50%
    assert any("rejeitadas" in a and "'vendas'" in a for a in alertas)

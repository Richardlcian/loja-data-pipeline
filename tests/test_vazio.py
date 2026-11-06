"""Começar a loja com a planilha vazia (só cabeçalhos) e ir cadastrando aos poucos."""
from datetime import date

import pandas as pd

from config import settings
from src import checks, load, pipeline


def _vazios():
    return {nome: pd.DataFrame(columns=colunas, dtype=str) for nome, colunas in settings.COLUNAS.items()}


def _com_produto(skus=("CEL-001",)):
    dados = _vazios()
    dados["produtos"] = pd.DataFrame({
        "sku": list(skus), "nome": ["Produto " + s for s in skus], "categoria": ["Celular"] * len(skus),
        "marca": ["Alfa"] * len(skus), "custo_unitario": ["900"] * len(skus), "preco_tabela": ["1499"] * len(skus)})
    return dados


def _contagem(con, tabela):
    return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def test_planilha_totalmente_vazia_roda_sem_erro():
    con = load.conectar(":memory:")
    r = pipeline.executar(_vazios(), con)
    assert r["vendas_carregadas"] == 0 and r["compras_carregadas"] == 0
    assert _contagem(con, "dim_produto") == 0


def test_so_cadastro_de_produto_sem_vendas():
    con = load.conectar(":memory:")
    pipeline.executar(_com_produto(), con)
    assert _contagem(con, "dim_produto") == 1 and _contagem(con, "fato_vendas") == 0


def test_estoque_vem_das_compras_mesmo_sem_vendas():
    dados = _com_produto()
    dados["compras"] = pd.DataFrame({"data": ["2026-11-06"], "sku": ["CEL-001"], "quantidade": ["4"],
                                     "custo_unitario": ["900"], "fornecedor": ["Distribuidora"]})
    con = load.conectar(":memory:")
    pipeline.executar(dados, con)
    assert con.execute("SELECT estoque_atual FROM vw_estoque_atual WHERE sku='CEL-001'").fetchone()[0] == 4


def test_sem_nenhuma_venda_nao_ha_alerta_de_dados_parados():
    con = load.conectar(":memory:")
    resumo = pipeline.executar(_vazios(), con)
    assert checks.verificar(con, resumo, verificar_frescor=True, hoje=date(2026, 11, 6)) == []


def test_produto_apagado_da_planilha_some_do_banco():
    con = load.conectar(":memory:")
    pipeline.executar(_com_produto(("CEL-001", "CEL-002")), con)
    assert _contagem(con, "dim_produto") == 2
    pipeline.executar(_com_produto(("CEL-001",)), con)
    skus = [s for (s,) in con.execute("SELECT sku FROM dim_produto")]
    assert skus == ["CEL-001"]

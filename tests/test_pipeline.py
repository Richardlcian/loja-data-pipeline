import pandas as pd

from src import load, pipeline


def _dados():
    produtos = pd.DataFrame({
        "sku": ["CEL-001", "PERF-001"], "nome": ["Smartphone", "Perfume"],
        "categoria": ["Celular", "Perfume"], "marca": ["Alfa", "Aurora"],
        "custo_unitario": ["900", "95"], "preco_tabela": ["1499", "219.90"]})
    vendas = pd.DataFrame({
        "data": ["2026-11-03", "2026-11-03", "2026-11-04"],
        "id_venda": ["V1", "V1", "V2"], "sku": ["CEL-001", "PERF-001", "XXX-999"],
        "quantidade": ["1", "2", "1"], "preco_unitario": ["1499", "219.90", "10"],
        "desconto": ["0", "", "0"], "forma_pagamento": ["Pix", "Pix", "Dinheiro"],
        "vendedor": ["Maria", "Maria", "Ana"], "cliente": ["a", "a", "b"]})
    # a compra é anterior à primeira venda: a data precisa existir em dim_tempo
    compras = pd.DataFrame({
        "data": ["2026-11-01"], "sku": ["CEL-001"], "quantidade": ["5"],
        "custo_unitario": ["900"], "fornecedor": ["Distribuidora"]})
    return {"produtos": produtos, "vendas": vendas, "compras": compras}


def _contagens(con):
    return (con.execute("SELECT COUNT(*) FROM fato_vendas").fetchone()[0],
            con.execute("SELECT COUNT(*) FROM fato_compras").fetchone()[0],
            con.execute("SELECT COUNT(*) FROM dim_produto").fetchone()[0])


def test_pipeline_carrega_e_separa_linhas_invalidas():
    con = load.conectar(":memory:")
    r = pipeline.executar(_dados(), con)
    assert _contagens(con) == (2, 1, 2)
    assert len(r["rejeitadas"]["vendas"]) == 1      # SKU inexistente
    assert "motivo_rejeicao" in r["rejeitadas"]["vendas"].columns
    assert round(r["faturamento"], 2) == round(1499 + 2 * 219.90, 2)


def test_pipeline_e_idempotente():
    con = load.conectar(":memory:")
    pipeline.executar(_dados(), con)
    primeira = _contagens(con)
    pipeline.executar(_dados(), con)
    pipeline.executar(_dados(), con)
    assert _contagens(con) == primeira


def test_correcao_na_planilha_chega_ao_banco():
    con = load.conectar(":memory:")
    pipeline.executar(_dados(), con)
    dados = _dados()
    dados["vendas"].loc[0, "preco_unitario"] = "1400"
    pipeline.executar(dados, con)
    preco = con.execute("SELECT preco_unitario FROM fato_vendas WHERE id_venda='V1' "
                        "AND id_produto=(SELECT id_produto FROM dim_produto WHERE sku='CEL-001')").fetchone()[0]
    assert preco == 1400.0

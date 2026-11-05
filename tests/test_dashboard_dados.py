import pandas as pd

from dashboards import dados


def _vendas():
    linhas = [
        # data, id_venda, sku, produto, categoria, qtd, pagamento, vendedor, valor, custo
        ("2026-11-01", "V1", "CEL-001", "Celular A", "Celular", 1, "Pix", "Maria", 1000.0, 600.0),
        ("2026-11-01", "V1", "ACE-001", "Capa", "Acessório", 2, "Pix", "Maria", 60.0, 10.0),
        ("2026-11-03", "V2", "PERF-001", "Perfume", "Perfume", 1, "Dinheiro", "Ana", 200.0, 90.0),
        ("2026-11-10", "V3", "CEL-001", "Celular A", "Celular", 1, "Cartão de crédito", "Ana", 1000.0, 600.0),
    ]
    df = pd.DataFrame(linhas, columns=["data", "id_venda", "sku", "produto", "categoria", "quantidade",
                                       "forma_pagamento", "vendedor", "valor_total", "custo_total"])
    df["data"] = pd.to_datetime(df["data"])
    df["lucro"] = df["valor_total"] - df["custo_total"]
    return df


def test_kpis():
    k = dados.kpis(_vendas())
    assert k["faturamento"] == 2260.0
    assert k["vendas"] == 3                         # V1 tem dois itens, mas é uma venda
    assert round(k["ticket"], 2) == round(2260 / 3, 2)
    assert round(k["margem"], 1) == round(100 * (2260 - 1300) / 2260, 1)


def test_kpis_sem_vendas_nao_divide_por_zero():
    k = dados.kpis(_vendas().iloc[0:0])
    assert k["faturamento"] == 0 and k["margem"] == 0 and k["ticket"] == 0


def test_filtrar_por_periodo_e_categoria():
    v = dados.filtrar(_vendas(), "2026-11-01", "2026-11-05", ["Celular", "Perfume"])
    assert set(v["id_venda"]) == {"V1", "V2"} and len(v) == 2
    assert len(dados.filtrar(_vendas(), "2026-11-01", "2026-11-30", [])) == 0


def test_periodo_anterior_tem_mesmo_tamanho_e_vem_antes():
    # período 08 a 14/11 (7 dias) -> anterior 01 a 07/11
    anterior = dados.periodo_anterior(_vendas(), "2026-11-08", "2026-11-14")
    assert set(anterior["id_venda"]) == {"V1", "V2"}


def test_variacao():
    assert dados.variacao(110, 100) == 10
    assert dados.variacao(50, 0) is None


def test_serie_diaria_inclui_dias_sem_venda_e_media_movel():
    v = dados.filtrar(_vendas(), "2026-11-01", "2026-11-05")
    s = dados.serie_temporal(v, "Dia", "2026-11-01", "2026-11-05")
    assert len(s) == 5
    assert s.loc["2026-11-02", "Faturamento"] == 0
    assert "Média móvel 7 dias" in s.columns


def test_serie_semanal_comeca_na_segunda():
    s = dados.serie_temporal(_vendas(), "Semana", "2026-11-01", "2026-11-10")
    assert all(d.dayofweek == 0 for d in s.index)
    assert round(s["Faturamento"].sum(), 2) == 2260.0


def test_curva_abc_classifica_e_soma_100():
    abc = dados.curva_abc(_vendas())
    assert abc.iloc[0]["produto"] == "Celular A" and abc.iloc[0]["classe"] == "A"
    assert round(abc["pct_individual"].sum(), 0) == 100


def test_estoque_cobertura_e_dias_sem_vender():
    estoque = pd.DataFrame({"sku": ["CEL-001", "ACE-001", "PERF-009"],
                            "produto": ["Celular A", "Capa", "Nunca vendido"],
                            "categoria": ["Celular", "Acessório", "Perfume"],
                            "estoque_atual": [3, 10, 5]})
    e = dados.estoque_com_cobertura(estoque, _vendas(), janela=30).set_index("sku")
    assert e.loc["CEL-001", "venda_diaria"] == round(2 / 30, 2)
    assert e.loc["CEL-001", "dias_sem_vender"] == 0           # vendeu na data mais recente (10/11)
    assert e.loc["ACE-001", "dias_sem_vender"] == 9
    assert pd.isna(e.loc["PERF-009", "dias_cobertura"])       # nunca vendeu: sem cobertura calculável
    assert pd.isna(e.loc["PERF-009", "dias_sem_vender"])

"""Camada de dados do dashboard: lê o banco e calcula as métricas.
Sem nada de Streamlit aqui, para poder ser testada (tests/test_dashboard_dados.py)."""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

BANCO = Path(__file__).resolve().parent.parent / "loja.db"
FREQUENCIAS = {"Dia": "D", "Semana": "W-MON", "Mês": "MS"}


# ---------------------------------------------------------------- leitura
def carregar_vendas(banco=BANCO) -> pd.DataFrame:
    """Uma linha por item vendido, já com produto, categoria e vendedor."""
    sql = """
        SELECT f.id_venda, f.data, p.sku, p.nome AS produto, p.categoria,
               f.quantidade, f.preco_unitario, f.desconto, f.forma_pagamento,
               COALESCE(v.nome, '(sem vendedor)') AS vendedor,
               f.valor_total, f.custo_total
        FROM fato_vendas f
        JOIN dim_produto p USING (id_produto)
        LEFT JOIN dim_vendedor v USING (id_vendedor)
    """
    con = sqlite3.connect(banco)
    try:
        df = pd.read_sql(sql, con, parse_dates=["data"])
    finally:
        con.close()
    df["lucro"] = df["valor_total"] - df["custo_total"]
    return df


def carregar_estoque(banco=BANCO) -> pd.DataFrame:
    con = sqlite3.connect(banco)
    try:
        return pd.read_sql(
            "SELECT sku, nome AS produto, categoria, estoque_atual FROM vw_estoque_atual", con)
    finally:
        con.close()


# ---------------------------------------------------------------- filtros
def filtrar(vendas: pd.DataFrame, inicio, fim, categorias=None) -> pd.DataFrame:
    mascara = (vendas["data"] >= pd.Timestamp(inicio)) & (vendas["data"] <= pd.Timestamp(fim))
    if categorias is not None:
        mascara &= vendas["categoria"].isin(categorias)
    return vendas[mascara]


def periodo_anterior(vendas: pd.DataFrame, inicio, fim, categorias=None) -> pd.DataFrame:
    """Janela de mesmo tamanho imediatamente antes do período escolhido."""
    inicio, fim = pd.Timestamp(inicio), pd.Timestamp(fim)
    dias = (fim - inicio).days + 1
    fim_ant = inicio - pd.Timedelta(days=1)
    inicio_ant = fim_ant - pd.Timedelta(days=dias - 1)
    return filtrar(vendas, inicio_ant, fim_ant, categorias)


# ---------------------------------------------------------------- métricas
def kpis(v: pd.DataFrame) -> dict:
    faturamento = float(v["valor_total"].sum())
    lucro = float(v["lucro"].sum())
    n_vendas = int(v["id_venda"].nunique())
    return {
        "faturamento": faturamento,
        "lucro": lucro,
        "margem": 100 * lucro / faturamento if faturamento else 0.0,
        "vendas": n_vendas,
        "ticket": faturamento / n_vendas if n_vendas else 0.0,
    }


def variacao(atual: float, anterior: float):
    """Variação percentual; None quando não há base de comparação."""
    if not anterior:
        return None
    return 100 * (atual - anterior) / anterior


def serie_temporal(v: pd.DataFrame, frequencia: str, inicio, fim) -> pd.DataFrame:
    regra = FREQUENCIAS[frequencia]
    base = v.set_index("data")[["valor_total", "lucro"]]
    opcoes = {"closed": "left", "label": "left"} if regra.startswith("W") else {}
    s = base.resample(regra, **opcoes).sum()
    if frequencia == "Dia":  # mostra também os dias sem venda, com zero
        s = s.reindex(pd.date_range(inicio, fim, freq="D"), fill_value=0.0)
    s = s.rename(columns={"valor_total": "Faturamento", "lucro": "Lucro bruto"})
    if frequencia == "Dia":
        s["Média móvel 7 dias"] = s["Faturamento"].rolling(7, min_periods=1).mean()
    return s.round(2)


def por_categoria(v: pd.DataFrame) -> pd.DataFrame:
    t = v.groupby("categoria").agg(unidades=("quantidade", "sum"),
                                   faturamento=("valor_total", "sum"),
                                   lucro=("lucro", "sum")).reset_index()
    t["margem_pct"] = (100 * t["lucro"] / t["faturamento"]).round(1)
    return t.sort_values("faturamento", ascending=False).reset_index(drop=True)


def top_produtos(v: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    t = v.groupby(["produto", "categoria"]).agg(unidades=("quantidade", "sum"),
                                                faturamento=("valor_total", "sum"),
                                                lucro=("lucro", "sum")).reset_index()
    t["margem_pct"] = (100 * t["lucro"] / t["faturamento"]).round(1)
    return t.sort_values("faturamento", ascending=False).head(n).reset_index(drop=True)


def por_pagamento(v: pd.DataFrame) -> pd.DataFrame:
    t = v.groupby("forma_pagamento").agg(vendas=("id_venda", "nunique"),
                                         faturamento=("valor_total", "sum")).reset_index()
    total = t["faturamento"].sum()
    t["pct_faturamento"] = (100 * t["faturamento"] / total).round(1) if total else 0.0
    return t.sort_values("faturamento", ascending=False).reset_index(drop=True)


def por_vendedor(v: pd.DataFrame) -> pd.DataFrame:
    t = v.groupby("vendedor").agg(vendas=("id_venda", "nunique"),
                                  faturamento=("valor_total", "sum")).reset_index()
    t["ticket_medio"] = (t["faturamento"] / t["vendas"]).round(2)
    return t.sort_values("faturamento", ascending=False).reset_index(drop=True)


def curva_abc(v: pd.DataFrame) -> pd.DataFrame:
    """A = produtos que formam os primeiros 80% do faturamento, B = até 95%, C = o resto."""
    t = v.groupby(["sku", "produto", "categoria"], as_index=False)["valor_total"].sum()
    t = t.rename(columns={"valor_total": "faturamento"}).sort_values("faturamento", ascending=False)
    total = t["faturamento"].sum()
    t["pct_individual"] = 100 * t["faturamento"] / total if total else 0.0
    t["pct_acumulado"] = t["pct_individual"].cumsum()
    anterior = t["pct_acumulado"] - t["pct_individual"]
    t["classe"] = np.where(anterior < 80, "A", np.where(anterior < 95, "B", "C"))
    return t.round({"pct_individual": 1, "pct_acumulado": 1}).reset_index(drop=True)


def estoque_com_cobertura(estoque: pd.DataFrame, vendas: pd.DataFrame, janela: int = 30) -> pd.DataFrame:
    """Junta estoque, venda média dos últimos `janela` dias e há quantos dias o item não vende.
    'Hoje' é a data da última venda registrada."""
    hoje = vendas["data"].max()
    recentes = vendas[vendas["data"] > hoje - pd.Timedelta(days=janela)]
    venda_diaria = recentes.groupby("sku")["quantidade"].sum() / janela
    ultima_venda = vendas.groupby("sku")["data"].max()

    e = estoque.copy()
    e["venda_diaria"] = e["sku"].map(venda_diaria).fillna(0.0).round(2)
    e["dias_cobertura"] = np.where(e["venda_diaria"] > 0,
                                   (e["estoque_atual"] / e["venda_diaria"]).round(1), np.nan)
    e["ultima_venda"] = e["sku"].map(ultima_venda)
    e["dias_sem_vender"] = (hoje - e["ultima_venda"]).dt.days
    return e

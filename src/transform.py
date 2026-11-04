"""Limpeza e padronização. Não descarta linhas: quem rejeita é o validate.py."""
import pandas as pd

NOMES_DIA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _texto(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().fillna("")


def _numero(s: pd.Series) -> pd.Series:
    """Converte texto em número (ponto decimal). Aceita 'R$ 29.90' e '1,499.00'.
    O que não der para converter vira NaN e é rejeitado na validação."""
    limpo = (
        s.astype("string")
        .str.replace(r"R\$|\s", "", regex=True)
        .str.replace(r"(?<=\d),(?=\d{3}(?:\D|$))", "", regex=True)  # separador de milhar
        .astype(object)
    )
    return pd.to_numeric(limpo, errors="coerce")


def _data(s: pd.Series) -> pd.Series:
    return pd.to_datetime(_texto(s), format="%Y-%m-%d", errors="coerce")


def normalizar_produtos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sku"] = _texto(df["sku"]).str.upper()
    for col in ["nome", "categoria", "marca"]:
        df[col] = _texto(df[col])
    df["custo_unitario"] = _numero(df["custo_unitario"])
    df["preco_tabela"] = _numero(df["preco_tabela"])
    return df.drop_duplicates(subset="sku", keep="last")


def normalizar_vendas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["data"] = _data(df["data"])
    df["id_venda"] = _texto(df["id_venda"])
    df["sku"] = _texto(df["sku"]).str.upper()
    df["quantidade"] = _numero(df["quantidade"])
    df["preco_unitario"] = _numero(df["preco_unitario"])
    vazio = _texto(df["desconto"]) == ""          # desconto em branco = sem desconto
    df["desconto"] = _numero(df["desconto"]).mask(vazio, 0.0)
    for col in ["forma_pagamento", "vendedor", "cliente"]:
        df[col] = _texto(df[col])
    return df


def normalizar_compras(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["data"] = _data(df["data"])
    df["sku"] = _texto(df["sku"]).str.upper()
    df["quantidade"] = _numero(df["quantidade"])
    df["custo_unitario"] = _numero(df["custo_unitario"])
    df["fornecedor"] = _texto(df["fornecedor"])
    return df


def calcular_vendas(vendas: pd.DataFrame, produtos: pd.DataFrame) -> pd.DataFrame:
    """Recebe vendas já validadas. Grava o custo no momento da venda."""
    df = vendas.merge(produtos[["sku", "custo_unitario"]], on="sku", how="left")
    df["data"] = df["data"].dt.strftime("%Y-%m-%d")
    df["quantidade"] = df["quantidade"].astype(int)
    df["valor_total"] = (df["quantidade"] * df["preco_unitario"] - df["desconto"]).round(2)
    df["custo_total"] = (df["quantidade"] * df["custo_unitario"]).round(2)
    return df.drop(columns="custo_unitario")


def preparar_compras(compras: pd.DataFrame) -> pd.DataFrame:
    df = compras.copy()
    df["data"] = df["data"].dt.strftime("%Y-%m-%d")
    df["quantidade"] = df["quantidade"].astype(int)
    return df


def gerar_dim_tempo(*series_de_datas: pd.Series) -> pd.DataFrame:
    """Calendário com todas as datas que aparecem em vendas e compras."""
    todas = pd.concat(series_de_datas).dropna().unique()
    d = pd.to_datetime(pd.Series(sorted(todas)))
    return pd.DataFrame({
        "data": d.dt.strftime("%Y-%m-%d"),
        "ano": d.dt.year,
        "mes": d.dt.month,
        "dia": d.dt.day,
        "dia_semana": d.dt.dayofweek,
        "nome_dia": d.dt.dayofweek.map(dict(enumerate(NOMES_DIA))),
        "trimestre": d.dt.quarter,
    })

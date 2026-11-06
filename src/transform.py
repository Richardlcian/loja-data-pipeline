"""Limpeza e padronização. Não descarta linhas: quem rejeita é o validate.py."""
import pandas as pd

from config import settings

NOMES_DIA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _texto(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().fillna("")


# número no formato brasileiro: 1499 | 1499,90 | 1.499 | 1.499,90
_NUMERO_BR = r"^-?\d{1,3}(?:\.\d{3})*(?:,\d+)?$|^-?\d+(?:,\d+)?$"


def _numero(s: pd.Series) -> pd.Series:
    """Converte texto em número, conforme a localidade da planilha (LOCALE_PLANILHA).
    en-US: aceita 'R$ 29.90' e '1,499.00'.  pt-BR: aceita 'R$ 29,90' e '1.499,00'.
    O que não der para converter com segurança vira NaN e é rejeitado na validação
    (por exemplo, '29.9' numa planilha pt-BR, que poderia ser lido errado)."""
    limpo = s.astype("string").str.replace(r"R\$|\s", "", regex=True)
    if settings.LOCALE_PLANILHA == "pt-BR":
        valido = limpo.str.match(_NUMERO_BR).fillna(False)
        limpo = (limpo.where(valido)
                 .str.replace(".", "", regex=False)       # ponto = separador de milhar
                 .str.replace(",", ".", regex=False))     # vírgula = decimal
    else:
        limpo = limpo.str.replace(r"(?<=\d),(?=\d{3}(?:\D|$))", "", regex=True)  # vírgula = milhar
    return pd.to_numeric(limpo.astype(object), errors="coerce")


def _data(s: pd.Series) -> pd.Series:
    """Aceita aaaa-mm-dd; na planilha pt-BR aceita também dd/mm/aaaa."""
    texto = _texto(s)
    datas = pd.to_datetime(texto, format="%Y-%m-%d", errors="coerce")
    if settings.LOCALE_PLANILHA == "pt-BR":
        datas = datas.fillna(pd.to_datetime(texto, format="%d/%m/%Y", errors="coerce"))
    return datas


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


def calcular_vendas(vendas: pd.DataFrame, produtos: pd.DataFrame, compras: pd.DataFrame | None = None) -> pd.DataFrame:
    """Recebe vendas já validadas e calcula valor_total e custo_total.

    O custo de cada venda é o da ÚLTIMA COMPRA registrada até a data da venda. Assim, mudar o custo
    no cadastro de produtos não altera a margem de vendas antigas. Se o produto ainda não tem
    nenhuma compra até aquela data, usa o custo do cadastro."""
    df = vendas.sort_values("data", kind="stable").merge(
        produtos[["sku", "custo_unitario"]].rename(columns={"custo_unitario": "custo_cadastro"}),
        on="sku", how="left")

    if compras is not None and len(compras) and len(df):
        ultimas = compras[["data", "sku", "custo_unitario"]].sort_values("data", kind="stable")
        ultimas["sku"] = ultimas["sku"].astype(object)   # as chaves precisam ter o mesmo tipo
        ultimas["data"] = ultimas["data"].astype(df["data"].dtype)
        df["sku"] = df["sku"].astype(object)
        df = pd.merge_asof(df, ultimas, on="data", by="sku", direction="backward")
        df["custo_unit"] = df["custo_unitario"].fillna(df["custo_cadastro"])
        df = df.drop(columns="custo_unitario")
    else:
        df["custo_unit"] = df["custo_cadastro"]

    df["data"] = df["data"].dt.strftime("%Y-%m-%d")
    df["quantidade"] = df["quantidade"].astype(int)
    df["valor_total"] = (df["quantidade"] * df["preco_unitario"] - df["desconto"]).round(2)
    df["custo_total"] = (df["quantidade"] * df["custo_unit"]).round(2)
    return df.drop(columns=["custo_cadastro", "custo_unit"]).reset_index(drop=True)


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

"""Regras de qualidade. Linhas inválidas são separadas e registradas, não derrubam o pipeline."""
import logging

import pandas as pd

from config import settings

log = logging.getLogger(__name__)


def _separar(df: pd.DataFrame, regras, nome: str):
    """Aplica as regras e devolve (validas, rejeitadas). A rejeitada ganha a coluna motivo_rejeicao."""
    df = df.copy()
    df["motivo_rejeicao"] = ""
    for motivo, mascara in regras(df).items():
        df.loc[mascara, "motivo_rejeicao"] += motivo + "; "

    rejeitadas = df[df["motivo_rejeicao"] != ""]
    validas = df[df["motivo_rejeicao"] == ""].drop(columns="motivo_rejeicao")
    if len(rejeitadas):
        log.warning("%s: %d de %d linhas rejeitadas", nome, len(rejeitadas), len(df))
    return validas, rejeitadas


def validar_produtos(df: pd.DataFrame):
    def regras(p):
        return {
            "sku vazio": p["sku"] == "",
            "nome vazio": p["nome"] == "",
            "categoria vazia": p["categoria"] == "",
            "custo inválido": p["custo_unitario"].isna() | (p["custo_unitario"] < 0),
            "preço inválido": p["preco_tabela"].isna() | (p["preco_tabela"] < 0),
        }
    return _separar(df, regras, "produtos")


def validar_vendas(df: pd.DataFrame, skus_validos: set):
    def regras(v):
        return {
            "data inválida": v["data"].isna(),
            "quantidade inválida": v["quantidade"].isna() | (v["quantidade"] <= 0),
            "quantidade não inteira": v["quantidade"].notna() & (v["quantidade"] % 1 != 0),
            "preço inválido": v["preco_unitario"].isna() | (v["preco_unitario"] < 0),
            "desconto inválido": v["desconto"].isna() | (v["desconto"] < 0)
                                 | (v["desconto"] > v["quantidade"] * v["preco_unitario"]),
            "id_venda vazio": v["id_venda"] == "",
            "SKU inexistente": ~v["sku"].isin(skus_validos),
            "pagamento inválido": ~v["forma_pagamento"].isin(settings.FORMAS_PAGAMENTO),
            "linha duplicada": v.duplicated(["id_venda", "sku"], keep="first"),
        }
    return _separar(df, regras, "vendas")


def validar_compras(df: pd.DataFrame, skus_validos: set):
    def regras(c):
        return {
            "data inválida": c["data"].isna(),
            "quantidade inválida": c["quantidade"].isna() | (c["quantidade"] <= 0),
            "quantidade não inteira": c["quantidade"].notna() & (c["quantidade"] % 1 != 0),
            "custo inválido": c["custo_unitario"].isna() | (c["custo_unitario"] < 0),
            "SKU inexistente": ~c["sku"].isin(skus_validos),
        }
    return _separar(df, regras, "compras")

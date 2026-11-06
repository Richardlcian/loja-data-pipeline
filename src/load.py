"""Carga no SQLite. As tabelas fato são recarregadas por inteiro a cada execução
(full refresh): rodar o pipeline duas vezes dá o mesmo resultado, e correções feitas
na planilha chegam ao banco."""
import logging
import sqlite3

import pandas as pd

from config import settings

log = logging.getLogger(__name__)


def conectar(caminho=None) -> sqlite3.Connection:
    con = sqlite3.connect(caminho or settings.DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def criar_schema(con: sqlite3.Connection) -> None:
    for arquivo in ["01_create_tables.sql", "02_views.sql"]:
        sql = (settings.SQL_DIR / arquivo).read_text(encoding="utf-8")
        con.executescript(sql)


def _linhas(df: pd.DataFrame) -> list:
    """DataFrame -> lista de tuplas com tipos nativos do Python (NaN vira None)."""
    return list(df.astype(object).where(df.notna(), None).itertuples(index=False, name=None))


def sincronizar_produtos(con, produtos: pd.DataFrame) -> None:
    cols = ["sku", "nome", "categoria", "marca", "custo_unitario", "preco_tabela"]
    con.executemany(
        """INSERT INTO dim_produto (sku, nome, categoria, marca, custo_unitario, preco_tabela)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(sku) DO UPDATE SET
               nome = excluded.nome, categoria = excluded.categoria, marca = excluded.marca,
               custo_unitario = excluded.custo_unitario, preco_tabela = excluded.preco_tabela""",
        _linhas(produtos[cols]),
    )


def sincronizar_vendedores(con, vendas: pd.DataFrame) -> None:
    nomes = sorted(n for n in vendas["vendedor"].unique() if n)
    con.executemany("INSERT OR IGNORE INTO dim_vendedor (nome) VALUES (?)", [(n,) for n in nomes])


def sincronizar_dim_tempo(con, dim_tempo: pd.DataFrame) -> None:
    con.executemany("INSERT OR IGNORE INTO dim_tempo VALUES (?, ?, ?, ?, ?, ?, ?)", _linhas(dim_tempo))


def recarregar_fatos(con, vendas: pd.DataFrame, compras: pd.DataFrame) -> None:
    ids_produto = dict(con.execute("SELECT sku, id_produto FROM dim_produto"))
    ids_vendedor = dict(con.execute("SELECT nome, id_vendedor FROM dim_vendedor"))

    v = vendas.copy()
    v["id_produto"] = v["sku"].map(ids_produto).astype("Int64")
    v["id_vendedor"] = v["vendedor"].map(ids_vendedor).astype("Int64")
    c = compras.copy()
    c["id_produto"] = c["sku"].map(ids_produto).astype("Int64")

    con.execute("DELETE FROM fato_vendas")
    con.execute("DELETE FROM fato_compras")

    con.executemany(
        """INSERT INTO fato_vendas
           (id_venda, data, id_produto, id_vendedor, quantidade, preco_unitario,
            desconto, forma_pagamento, valor_total, custo_total)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        _linhas(v[["id_venda", "data", "id_produto", "id_vendedor", "quantidade",
                   "preco_unitario", "desconto", "forma_pagamento", "valor_total", "custo_total"]]),
    )
    con.executemany(
        """INSERT INTO fato_compras (data, id_produto, quantidade, custo_unitario, fornecedor)
           VALUES (?, ?, ?, ?, ?)""",
        _linhas(c[["data", "id_produto", "quantidade", "custo_unitario", "fornecedor"]]),
    )
    log.info("Carga concluída: %d vendas, %d compras", len(v), len(c))


def remover_produtos_ausentes(con, skus_da_planilha: set) -> int:
    """Produtos apagados da planilha também saem do banco. Só roda depois de recarregar_fatos:
    as vendas e compras carregadas só usam SKUs que existem na planilha, então nada fica órfão."""
    no_banco = {sku for (sku,) in con.execute("SELECT sku FROM dim_produto")}
    sobras = no_banco - set(skus_da_planilha)
    con.executemany("DELETE FROM dim_produto WHERE sku = ?", [(s,) for s in sobras])
    if sobras:
        log.info("Removidos do banco %d produto(s) que não estão mais na planilha", len(sobras))
    return len(sobras)

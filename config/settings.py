import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "loja.db"
SQL_DIR = BASE_DIR / "sql"
SAMPLE_DIR = BASE_DIR / "data" / "sample"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"

SHEET_ID = os.getenv("SHEET_ID", "")
# true = lê os CSVs fictícios de data/sample | false = lê a planilha real
USE_SAMPLE = os.getenv("USE_SAMPLE", "true").lower() == "true"

# gid de cada aba da planilha (aparece na URL: #gid=...)
ABAS = {
    "produtos": 0,
    "vendas": 1527734175,
    "compras": 1653085149,
}

# colunas obrigatórias de cada aba (os nomes precisam ser exatamente estes)
COLUNAS = {
    "produtos": ["sku", "nome", "categoria", "marca", "custo_unitario", "preco_tabela"],
    "vendas": ["data", "id_venda", "sku", "quantidade", "preco_unitario", "desconto",
               "forma_pagamento", "vendedor", "cliente"],
    "compras": ["data", "sku", "quantidade", "custo_unitario", "fornecedor"],
}

# a loja aceita somente Pix, cartão e dinheiro
FORMAS_PAGAMENTO = {"Pix", "Cartão de débito", "Cartão de crédito", "Dinheiro"}

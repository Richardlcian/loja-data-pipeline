import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
# Banco de dados. Para testar sem tocar no banco real: DB_PATH=loja_teste.db python -m src.pipeline
_db = Path(os.getenv("DB_PATH", "loja.db"))
DB_PATH = _db if _db.is_absolute() else BASE_DIR / _db
SQL_DIR = BASE_DIR / "sql"
SAMPLE_DIR = BASE_DIR / "data" / "sample"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"

SHEET_ID = os.getenv("SHEET_ID", "")
# true = lê os CSVs fictícios de data/sample | false = lê a planilha real
USE_SAMPLE = os.getenv("USE_SAMPLE", "true").lower() == "true"

# Localidade da planilha (Arquivo > Configurações > Localidade):
#   en-US = Estados Unidos (ponto decimal, datas aaaa-mm-dd)
#   pt-BR = Brasil (vírgula decimal, e datas digitadas como 06/11/2026 são lidas como dia/mês/ano)
LOCALE_PLANILHA = os.getenv("LOCALE_PLANILHA", "en-US")

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

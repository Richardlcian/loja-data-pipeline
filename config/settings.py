import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "loja.db"
SHEET_ID = os.getenv("SHEET_ID", "")

# Em desenvolvimento, use os CSVs de exemplo
USE_SAMPLE = os.getenv("USE_SAMPLE", "true").lower() == "true"
SAMPLE_DIR = BASE_DIR / "data" / "sample"

# gid de cada aba da planilha (aparece na URL: #gid=...)
ABAS = {
    "produtos": 0,
    "vendas": 1527734175,
    "compras": 1653085149,
}

FORMAS_PAGAMENTO = {
    "Pix", "Débito", "Crédito à vista",
    "Crédito parcelado", "Dinheiro", "Boleto",
}
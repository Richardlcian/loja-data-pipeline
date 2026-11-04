import logging

import pandas as pd

from config import settings

log = logging.getLogger(__name__)


def _url_aba(gid: int) -> str:
    return (f"https://docs.google.com/spreadsheets/d/{settings.SHEET_ID}"
            f"/export?format=csv&gid={gid}")


def extrair_aba(nome: str) -> pd.DataFrame:
    if settings.USE_SAMPLE:
        origem = settings.SAMPLE_DIR / f"{nome}.csv"
    else:
        if not settings.SHEET_ID:
            raise ValueError("SHEET_ID está vazio no .env")
        origem = _url_aba(settings.ABAS[nome])

    # tudo como texto: a conversão de tipos é feita (e validada) na transformação
    df = pd.read_csv(origem, dtype=str)

    faltando = [c for c in settings.COLUNAS[nome] if c not in df.columns]
    if faltando:
        raise ValueError(f"Aba '{nome}' sem as colunas: {faltando}")

    df = df[settings.COLUNAS[nome]]
    log.info("Extraídas %d linhas da aba '%s'", len(df), nome)
    return df


def extrair_tudo() -> dict[str, pd.DataFrame]:
    return {nome: extrair_aba(nome) for nome in settings.ABAS}

import logging
from datetime import date
from pathlib import Path

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

    # A planilha pode exportar linhas totalmente em branco (só vírgulas ou espaços), por exemplo
    # depois de apagar dados ou com linhas vazias no meio. Elas não são dados: são ignoradas.
    texto = df.fillna("").apply(lambda coluna: coluna.str.strip())
    em_branco = (texto == "").all(axis=1)
    if em_branco.any():
        log.info("Ignoradas %d linhas em branco da aba '%s'", int(em_branco.sum()), nome)
    df = df[~em_branco]

    log.info("Extraídas %d linhas da aba '%s'", len(df), nome)
    return df


def extrair_tudo() -> dict[str, pd.DataFrame]:
    return {nome: extrair_aba(nome) for nome in settings.ABAS}


def salvar_snapshot(dados: dict[str, pd.DataFrame], hoje: date | None = None) -> Path:
    """Guarda uma cópia bruta da planilha do dia em data/raw/AAAA-MM-DD/.
    Se alguém apagar ou alterar algo na planilha, dá para recuperar o que havia antes."""
    pasta = settings.BASE_DIR / "data" / "raw" / (hoje or date.today()).isoformat()
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, df in dados.items():
        df.to_csv(pasta / f"{nome}.csv", index=False, encoding="utf-8")
    log.info("Snapshot da planilha salvo em %s", pasta)
    return pasta

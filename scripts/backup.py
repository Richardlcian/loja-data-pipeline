"""Backup do banco e limpeza de cópias antigas.

    python scripts/backup.py

- loja.db  ->  backups/loja_AAAA-MM-DD.db   (cópia consistente, mesmo com o banco aberto)
- mantém os 14 backups e os 30 snapshots da planilha (data/raw/AAAA-MM-DD) mais recentes
- se BACKUP_EXTRA_DIR estiver no .env (por exemplo, uma pasta do Google Drive ou OneDrive),
  copia também para lá: um backup no mesmo computador não protege contra perder o computador
"""
import os
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

BANCO = RAIZ / "loja.db"
PASTA_BACKUPS = RAIZ / "backups"
PASTA_SNAPSHOTS = RAIZ / "data" / "raw"
MANTER_BACKUPS = 14
MANTER_SNAPSHOTS = 30


def fazer_backup(banco: Path, pasta: Path, hoje: date | None = None) -> Path:
    """Usa a API de backup do SQLite, que gera uma cópia íntegra do banco."""
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"loja_{(hoje or date.today()).isoformat()}.db"
    origem = sqlite3.connect(banco)
    copia = sqlite3.connect(destino)
    try:
        origem.backup(copia)
    finally:
        copia.close()
        origem.close()
    return destino


def podar(itens, manter: int) -> list[Path]:
    """Apaga os mais antigos (o nome tem a data), deixando os `manter` mais recentes."""
    ordenados = sorted(itens, key=lambda p: p.name)
    removidos = ordenados[:-manter] if manter > 0 else ordenados
    for item in removidos:
        shutil.rmtree(item) if item.is_dir() else item.unlink()
    return removidos


def _snapshots(pasta: Path) -> list[Path]:
    return [p for p in pasta.glob("20??-??-??") if p.is_dir()] if pasta.exists() else []


def copiar_para_extra(destino: Path, pasta_extra: Path, snapshot_hoje: Path | None) -> None:
    pasta_extra.mkdir(parents=True, exist_ok=True)
    shutil.copy2(destino, pasta_extra / destino.name)
    podar(pasta_extra.glob("loja_*.db"), MANTER_BACKUPS)
    if snapshot_hoje is not None and snapshot_hoje.exists():
        shutil.copytree(snapshot_hoje, pasta_extra / "raw" / snapshot_hoje.name, dirs_exist_ok=True)
        podar(_snapshots(pasta_extra / "raw"), MANTER_SNAPSHOTS)


def main() -> int:
    if not BANCO.exists():
        print("loja.db não encontrado. Rode antes: python -m src.pipeline")
        return 1

    destino = fazer_backup(BANCO, PASTA_BACKUPS)
    print(f"Backup criado: {destino}")
    podar(PASTA_BACKUPS.glob("loja_*.db"), MANTER_BACKUPS)
    podar(_snapshots(PASTA_SNAPSHOTS), MANTER_SNAPSHOTS)

    extra = os.getenv("BACKUP_EXTRA_DIR")
    if extra:
        try:
            copiar_para_extra(destino, Path(extra), PASTA_SNAPSHOTS / date.today().isoformat())
            print(f"Cópia extra salva em {extra}")
        except OSError as erro:
            print(f"ATENÇÃO: não foi possível copiar para {extra}: {erro}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

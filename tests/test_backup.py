import importlib.util
import sqlite3
import tempfile
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from config import settings
from src import extract

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("backup", RAIZ / "scripts" / "backup.py")
backup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backup)


def test_backup_gera_copia_com_os_mesmos_dados():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        banco = tmp / "loja.db"
        con = sqlite3.connect(banco)
        con.execute("CREATE TABLE t (x INTEGER)")
        con.execute("INSERT INTO t VALUES (42)")
        con.commit()
        con.close()

        destino = backup.fazer_backup(banco, tmp / "backups", hoje=date(2026, 11, 5))
        assert destino.name == "loja_2026-11-05.db"
        copia = sqlite3.connect(destino)
        assert copia.execute("SELECT x FROM t").fetchone() == (42,)
        copia.close()


def test_poda_mantem_so_os_mais_recentes():
    with tempfile.TemporaryDirectory() as tmp:
        pasta = Path(tmp)
        for dia in ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04"]:
            (pasta / f"loja_{dia}.db").write_text("x")
        backup.podar(pasta.glob("loja_*.db"), manter=2)
        assert sorted(p.name for p in pasta.glob("*.db")) == ["loja_2026-11-03.db", "loja_2026-11-04.db"]


def test_snapshot_salva_um_csv_por_aba():
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(settings, "BASE_DIR", Path(tmp)):
        dados = {"produtos": pd.DataFrame({"sku": ["A"]}), "vendas": pd.DataFrame({"id": [1]})}
        pasta = extract.salvar_snapshot(dados, hoje=date(2026, 11, 5))
        assert pasta.name == "2026-11-05"
        assert sorted(p.name for p in pasta.iterdir()) == ["produtos.csv", "vendas.csv"]

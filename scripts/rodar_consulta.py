"""
Executa as consultas de sql/03_analises.sql pelo terminal.

    python scripts/rodar_consulta.py          # lista as consultas
    python scripts/rodar_consulta.py 3        # roda a consulta 3 e mostra o resultado
    python scripts/rodar_consulta.py 3 --csv  # também salva em data/processed/consulta_3.csv
"""
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_SQL = RAIZ / "sql" / "03_analises.sql"
BANCO = RAIZ / "loja.db"


def carregar_consultas() -> dict[int, tuple[str, str]]:
    texto = ARQUIVO_SQL.read_text(encoding="utf-8")
    blocos = re.split(r"^-- ## (\d+)\.\s*(.*)$", texto, flags=re.MULTILINE)
    # blocos = [cabeçalho, num, título, sql, num, título, sql, ...]
    return {int(blocos[i]): (blocos[i + 1].strip(), blocos[i + 2].strip())
            for i in range(1, len(blocos), 3)}


def main() -> None:
    consultas = carregar_consultas()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        for n, (titulo, _) in consultas.items():
            print(f"{n:>2}. {titulo}")
        return

    n = int(args[0])
    if n not in consultas:
        sys.exit(f"Consulta {n} não existe. Rode sem argumentos para ver a lista.")

    titulo, sql = consultas[n]
    con = sqlite3.connect(BANCO)
    df = pd.read_sql(sql, con)
    con.close()

    print(f"\n{n}. {titulo}\n")
    print(df.to_string(index=False) if len(df) else "(sem resultados)")

    if "--csv" in sys.argv:
        destino = RAIZ / "data" / "processed" / f"consulta_{n}.csv"
        destino.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(destino, index=False, encoding="utf-8")
        print(f"\nSalvo em {destino}")


if __name__ == "__main__":
    main()

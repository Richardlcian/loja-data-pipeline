import tempfile
from pathlib import Path
from unittest import mock

from config import settings
from src import extract


def _ler(nome, conteudo):
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / f"{nome}.csv").write_text(conteudo, encoding="utf-8")
        with mock.patch.object(settings, "USE_SAMPLE", True), mock.patch.object(settings, "SAMPLE_DIR", Path(tmp)):
            return extract.extrair_aba(nome)


CABECALHO = "data,id_venda,sku,quantidade,preco_unitario,desconto,forma_pagamento,vendedor,cliente\n"


def test_ignora_linhas_so_com_virgulas_e_com_espacos():
    csv = (CABECALHO + ",,,,,,,,\n" + "2026-11-06,V0001,CEL-001,1,1499,0,Pix,Maria,\n"
           + " , , , , , , , , \n" + ",,,,,,,,\n")
    df = _ler("vendas", csv)
    assert len(df) == 1 and df.iloc[0]["id_venda"] == "V0001"


def test_planilha_so_com_linhas_em_branco_fica_vazia():
    df = _ler("vendas", CABECALHO + ",,,,,,,,\n" * 199)
    assert len(df) == 0 and list(df.columns) == settings.COLUNAS["vendas"]


def test_so_cabecalho_fica_vazia():
    assert len(_ler("vendas", CABECALHO)) == 0


def test_linha_parcialmente_preenchida_e_mantida():
    df = _ler("vendas", CABECALHO + ",V0002,,,,,,,\n")      # incompleta: a validação é quem rejeita
    assert len(df) == 1

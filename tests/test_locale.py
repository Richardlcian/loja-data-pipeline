from unittest import mock

import pandas as pd

from config import settings
from src import transform


def _numeros(valores, locale):
    with mock.patch.object(settings, "LOCALE_PLANILHA", locale):
        return list(transform._numero(pd.Series(valores)))


def _datas(valores, locale):
    with mock.patch.object(settings, "LOCALE_PLANILHA", locale):
        return [d.strftime("%Y-%m-%d") if pd.notna(d) else None for d in transform._data(pd.Series(valores))]


def test_numeros_pt_br():
    r = _numeros(["1499", "29,90", "R$ 1.499,00", "1.499", "-5,5", "0"], "pt-BR")
    assert r == [1499.0, 29.9, 1499.0, 1499.0, -5.5, 0.0]


def test_pt_br_rejeita_ponto_decimal_ambiguo():
    r = _numeros(["29.9", "1.5", "abc", ""], "pt-BR")
    assert all(pd.isna(x) for x in r)           # nunca vira 299 ou 15 em silêncio


def test_numeros_en_us_continuam_iguais():
    r = _numeros(["29.90", "R$ 1,499.00", "29,9"], "en-US")
    assert r[0] == 29.9 and r[1] == 1499.0 and pd.isna(r[2])


def test_datas_pt_br_aceitam_barra_e_iso():
    assert _datas(["06/11/2026", "2026-11-06", "25/12/2026"], "pt-BR") == ["2026-11-06", "2026-11-06", "2026-12-25"]


def test_datas_pt_br_rejeitam_data_impossivel():
    assert _datas(["31/02/2026", "texto"], "pt-BR") == [None, None]


def test_datas_en_us_so_aceitam_iso():
    assert _datas(["2026-11-06", "06/11/2026"], "en-US") == ["2026-11-06", None]

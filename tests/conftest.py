"""Configuração comum dos testes: eles não podem depender do .env de quem os executa."""
import pytest

from config import settings


@pytest.fixture(autouse=True)
def ambiente_isolado(monkeypatch):
    # planilha em inglês (ponto decimal, datas aaaa-mm-dd), mesmo que o .env use pt-BR
    monkeypatch.setattr(settings, "LOCALE_PLANILHA", "en-US")
    # nenhum teste pode enviar e-mail de verdade com as credenciais do .env
    for chave in ("EMAIL_REMETENTE", "EMAIL_SENHA", "EMAIL_DESTINO"):
        monkeypatch.delenv(chave, raising=False)

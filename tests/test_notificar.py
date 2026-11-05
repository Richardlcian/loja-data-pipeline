import os
from unittest import mock

from src import notificar

CONFIG = {"EMAIL_REMETENTE": "loja@exemplo.com", "EMAIL_SENHA": "senha-de-app",
          "EMAIL_DESTINO": "dono@exemplo.com"}


def test_sem_configuracao_nao_envia_nada():
    with mock.patch.dict(os.environ, {k: "" for k in CONFIG}), \
         mock.patch("src.notificar.smtplib.SMTP_SSL") as smtp:
        assert notificar.enviar_email("assunto", "corpo") is False
        smtp.assert_not_called()


def test_com_configuracao_envia_a_mensagem():
    with mock.patch.dict(os.environ, CONFIG), \
         mock.patch("src.notificar.smtplib.SMTP_SSL") as smtp:
        assert notificar.enviar_email("[Loja] Teste", "corpo") is True
        servidor = smtp.return_value.__enter__.return_value
        servidor.login.assert_called_once_with("loja@exemplo.com", "senha-de-app")
        assert servidor.send_message.call_args[0][0]["Subject"] == "[Loja] Teste"


def test_falha_no_envio_nao_levanta_erro():
    with mock.patch.dict(os.environ, CONFIG), \
         mock.patch("src.notificar.smtplib.SMTP_SSL", side_effect=OSError("sem rede")):
        assert notificar.enviar_email("assunto", "corpo") is False

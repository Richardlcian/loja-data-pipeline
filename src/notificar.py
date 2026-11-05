"""Envio opcional de alertas por e-mail. Sem configuração no .env, não faz nada
(o alerta continua registrado em log e em logs/ALERTAS.txt)."""
import logging
import os
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)


def configurado() -> bool:
    return all(os.getenv(chave) for chave in ("EMAIL_REMETENTE", "EMAIL_SENHA", "EMAIL_DESTINO"))


def enviar_email(assunto: str, corpo: str) -> bool:
    """Retorna True se enviou. Nunca levanta erro: falha de e-mail não pode derrubar o pipeline."""
    if not configurado():
        log.info("E-mail não configurado; alerta registrado apenas em log.")
        return False

    remetente = os.getenv("EMAIL_REMETENTE")
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = os.getenv("EMAIL_DESTINO")
    msg.set_content(corpo)
    try:
        with smtplib.SMTP_SSL(os.getenv("EMAIL_SMTP", "smtp.gmail.com"),
                              int(os.getenv("EMAIL_PORTA", "465")), timeout=30) as servidor:
            servidor.login(remetente, os.getenv("EMAIL_SENHA"))
            servidor.send_message(msg)
        log.info("E-mail de alerta enviado")
        return True
    except Exception:
        log.exception("Não foi possível enviar o e-mail de alerta")
        return False

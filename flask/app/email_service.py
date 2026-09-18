## Inmetro/Dimci/Diele/Lampe
# Camada de envio de e-mail do dccGenerator.
# - independente da logica de negocio
# - configuracao via variaveis de ambiente
# - SMTP corporativo (Exchange), sem TLS/autenticacao por padrao
#
# Variaveis de ambiente:
#   DCC_EMAIL_ENABLED  (padrao: true)
#   SMTP_HOST          (obrigatorio; definir no .env)
#   SMTP_PORT          (padrao: 587)
#   SMTP_USERNAME      (padrao: vazio)
#   SMTP_PASSWORD      (padrao: vazio)
#   SMTP_USE_AUTH      (padrao: false)
#   SMTP_USE_TLS       (padrao: false; STARTTLS)
#   SMTP_FROM          (obrigatorio; definir no .env)
#   SMTP_TIMEOUT       (padrao: 15 segundos)

# Author: Gean Marcos Geronymo

# This file is part of Inmetro DCC Tools.
#
# Inmetro DCC Tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Inmetro DCC Tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Inmetro DCC Tools. If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger('dcc.email')


def _bool_env(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'sim', 'on')


def get_config():
    """Le a configuracao SMTP das variaveis de ambiente."""
    try:
        port = int(os.environ.get('SMTP_PORT', '587'))
    except ValueError:
        port = 587
    try:
        timeout = int(os.environ.get('SMTP_TIMEOUT', '15'))
    except ValueError:
        timeout = 15

    return {
        'enabled': _bool_env('DCC_EMAIL_ENABLED', True),
        'host': (os.environ.get('SMTP_HOST', '') or '').strip(),
        'port': port,
        'username': os.environ.get('SMTP_USERNAME', ''),
        'password': os.environ.get('SMTP_PASSWORD', ''),
        'use_auth': _bool_env('SMTP_USE_AUTH', False),
        'use_tls': _bool_env('SMTP_USE_TLS', False),
        'from_addr': (os.environ.get('SMTP_FROM', '') or '').strip(),
        'timeout': timeout,
    }


def is_enabled():
    cfg = get_config()
    return bool(cfg['enabled'] and cfg['host'] and cfg['from_addr'])


def send_email(to, subject, body, html=None):
    """Envia um e-mail de texto simples (e opcionalmente HTML).

    Retorna True em sucesso e False em falha/configuracao ausente.
    Nao levanta excecao (falhas sao registradas no log, sem expor segredos).
    """
    cfg = get_config()

    if not cfg['enabled']:
        logger.warning("Envio de e-mail desabilitado (DCC_EMAIL_ENABLED=false); "
                       "mensagem para %s nao enviada.", to)
        return False
    if not cfg['host'] or not cfg['from_addr']:
        logger.error("Configuracao SMTP incompleta (SMTP_HOST/SMTP_FROM); "
                     "mensagem para %s nao enviada.", to)
        return False

    message = EmailMessage()
    message['From'] = cfg['from_addr']
    message['To'] = to
    message['Subject'] = subject
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype='html')

    try:
        with smtplib.SMTP(cfg['host'], cfg['port'], timeout=cfg['timeout']) as server:
            server.ehlo()
            if cfg['use_tls']:
                server.starttls()
                server.ehlo()
            if cfg['use_auth'] and cfg['username']:
                server.login(cfg['username'], cfg['password'])
            server.send_message(message)
        logger.info("E-mail enviado para %s (assunto: %s).", to, subject)
        return True
    except Exception as e:
        # nao registrar corpo/token nem credenciais
        logger.error("Falha ao enviar e-mail para %s: %s", to, e)
        return False

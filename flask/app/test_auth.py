## Inmetro/Dimci/Diele/Lampe
# Testes automatizados da autenticacao (usuario/senha + API-KEY + recuperacao) do dccGenerator.

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

import json
import os
import sqlite3
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

# Configura um banco isolado e desabilita o envio de e-mail ANTES de importar a app.
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix='dcc_auth_test_'), 'dcc_auth.db')
os.environ['DCC_DB_PATH'] = _TMP_DB
os.environ['DCC_SECRET_KEY'] = 'secret-test-key'
os.environ['DCC_EMAIL_ENABLED'] = 'false'

import main  # noqa: E402
from main import app  # noqa: E402
import auth  # noqa: E402
import email_service  # noqa: E402
from werkzeug.security import check_password_hash  # noqa: E402

EXEMPLO_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'examples',
    'dcc_json.json',
)

SENHA = 'senha12345'


def email_de(username):
    return '%s@inmetro.gov.br' % username


def _limpar_banco():
    for path in (_TMP_DB, _TMP_DB + '-wal', _TMP_DB + '-shm'):
        if os.path.exists(path):
            os.remove(path)


def _fetchone(sql, params=()):
    conn = sqlite3.connect(_TMP_DB)
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


class AuthTestBase(unittest.TestCase):

    def setUp(self):
        _limpar_banco()
        auth.init_db()
        app.config['TESTING'] = True
        self.client = app.test_client()

    def registrar(self, username='alice', password=SENHA, email=None):
        payload = {'username': username, 'password': password, 'email': email or email_de(username)}
        return self.client.post('/dcc/register', json=payload)

    def api_key(self, username='alice', password=SENHA):
        resp = self.registrar(username, password)
        self.assertEqual(resp.status_code, 201)
        return resp.get_json()['api_key']

    def criar_usuario(self, username='alice', password=SENHA, email=None):
        return auth.create_user(username, password, email or email_de(username))

    def login(self, username='alice', password=SENHA):
        return self.client.post('/dcc/login', data={'username': username, 'password': password})

    def dados_exemplo(self):
        with open(EXEMPLO_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)


class TestRegistro(AuthTestBase):

    def test_registro_json_cria_usuario_e_retorna_chave(self):
        resp = self.registrar('alice', SENHA, 'alice@inmetro.gov.br')
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data['username'], 'alice')
        self.assertEqual(data['email'], 'alice@inmetro.gov.br')
        self.assertTrue(data['api_key'].startswith('dcc_'))

    def test_registro_duplicado_retorna_erro(self):
        self.assertEqual(self.registrar('alice').status_code, 201)
        resp = self.registrar('alice')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_registro_email_duplicado_retorna_erro(self):
        self.assertEqual(self.registrar('alice').status_code, 201)
        resp = self.registrar('bob', email='alice@inmetro.gov.br')
        self.assertEqual(resp.status_code, 400)

    def test_registro_usuario_invalido(self):
        self.assertEqual(self.registrar('usuario com espacos').status_code, 400)

    def test_registro_senha_curta(self):
        self.assertEqual(self.registrar('bob', password='123').status_code, 400)

    def test_registro_email_obrigatorio(self):
        resp = self.client.post(
            '/dcc/register', json={'username': 'bob', 'password': SENHA}
        )
        self.assertEqual(resp.status_code, 400)

    def test_registro_email_fora_do_dominio(self):
        resp = self.registrar('bob', email='bob@example.com')
        self.assertEqual(resp.status_code, 400)

    def test_registro_via_formulario_exibe_chave(self):
        resp = self.client.post(
            '/dcc/register',
            data={'username': 'bob', 'password': SENHA, 'email': 'bob@inmetro.gov.br'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'dcc_', resp.data)


class TestApiKey(AuthTestBase):

    def test_endpoint_protegido_sem_chave(self):
        resp = self.client.post('/dcc/generate', json={})
        self.assertEqual(resp.status_code, 401)

    def test_endpoint_protegido_chave_invalida(self):
        resp = self.client.post('/dcc/generate', json={}, headers={'X-API-Key': 'dcc_invalida'})
        self.assertEqual(resp.status_code, 401)

    def test_endpoint_protegido_chave_valida(self):
        key = self.api_key('alice')
        resp = self.client.post(
            '/dcc/generate', json=self.dados_exemplo(), headers={'X-API-Key': key}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'digitalCalibrationCertificate', resp.data)

    def test_chave_revogada_bloqueia_acesso(self):
        key = self.api_key('alice')
        self.assertTrue(auth.set_user_active('alice', False))
        resp = self.client.post(
            '/dcc/generate', json=self.dados_exemplo(), headers={'X-API-Key': key}
        )
        self.assertEqual(resp.status_code, 401)

    def test_chave_recuperavel_no_banco(self):
        key = self.api_key('alice')
        user = auth.get_user_by_api_key(key)
        self.assertIsNotNone(user)
        self.assertEqual(user['api_key'], key)


class TestInterfaceWeb(AuthTestBase):

    def test_pagina_protegida_redireciona_para_login(self):
        resp = self.client.get('/dcc/form_dcc')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/dcc/login', resp.headers['Location'])
        self.assertIn('auth_required=1', resp.headers['Location'])

    def test_pagina_publica_permanece_aberta(self):
        rotas = ['/dcc/', '/dcc/api_doc', '/dcc/exemplos', '/dcc/faq',
                 '/dcc/upload_xml_hr', '/dcc/validate_xml', '/dcc/esqueci-senha']
        for rota in rotas:
            self.assertEqual(self.client.get(rota).status_code, 200, rota)

    def test_ferramenta_visualizar_aberta(self):
        resp = self.client.post('/dcc/visualizar_dcc', data={})
        self.assertEqual(resp.status_code, 400)

    def test_ferramenta_validar_aberta(self):
        resp = self.client.post('/dcc/validate_xml', data={})
        self.assertEqual(resp.status_code, 400)

    def test_login_correto_libera_acesso(self):
        self.api_key('alice')
        resp = self.login('alice', SENHA)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.client.get('/dcc/form_dcc').status_code, 200)

    def test_login_senha_incorreta_nao_libera(self):
        self.api_key('alice')
        resp = self.login('alice', 'senha-errada')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.get('/dcc/form_dcc').status_code, 302)

    def test_logout_encerra_sessao(self):
        self.api_key('alice')
        self.login('alice', SENHA)
        self.assertEqual(self.client.get('/dcc/form_dcc').status_code, 200)
        self.client.get('/dcc/logout')
        self.assertEqual(self.client.get('/dcc/form_dcc').status_code, 302)

    def test_usuario_revogado_perde_sessao(self):
        self.api_key('alice')
        self.login('alice', SENHA)
        self.assertEqual(self.client.get('/dcc/form_dcc').status_code, 200)
        auth.set_user_active('alice', False)
        self.assertEqual(self.client.get('/dcc/form_dcc').status_code, 302)

    def test_sessao_permite_chamada_de_api(self):
        self.api_key('alice')
        self.login('alice', SENHA)
        resp = self.client.post('/dcc/generate', json=self.dados_exemplo())
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'digitalCalibrationCertificate', resp.data)


class TestPerfil(AuthTestBase):

    def test_perfil_requer_login(self):
        resp = self.client.get('/dcc/perfil')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/dcc/login', resp.headers['Location'])

    def test_perfil_exibe_api_key(self):
        key = self.api_key('alice')
        self.login('alice', SENHA)
        resp = self.client.get('/dcc/perfil')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(key.encode(), resp.data)

    def test_regenerar_api_key_invalida_a_anterior(self):
        old_key = self.api_key('alice')
        self.login('alice', SENHA)

        resp = self.client.post('/dcc/perfil/regenerar')
        self.assertEqual(resp.status_code, 302)

        self.assertIsNone(auth.get_user_by_api_key(old_key))

        current = auth.get_user_by_id(1)
        self.assertNotEqual(current['api_key'], old_key)

        anon = app.test_client()
        resp = anon.post(
            '/dcc/generate', json=self.dados_exemplo(), headers={'X-API-Key': old_key}
        )
        self.assertEqual(resp.status_code, 401)

        resp = anon.post(
            '/dcc/generate', json=self.dados_exemplo(),
            headers={'X-API-Key': current['api_key']},
        )
        self.assertEqual(resp.status_code, 200)


class TestTrocaSenha(AuthTestBase):

    def test_troca_requer_login(self):
        resp = self.client.get('/dcc/perfil/senha')
        self.assertEqual(resp.status_code, 302)

    def test_troca_senha_com_sucesso(self):
        self.api_key('alice')
        self.login('alice', SENHA)

        resp = self.client.post('/dcc/perfil/senha', data={
            'current_password': SENHA,
            'new_password': 'novaSenha123',
            'new_password_confirm': 'novaSenha123',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(auth.authenticate('alice', SENHA))
        self.assertIsNotNone(auth.authenticate('alice', 'novaSenha123'))

    def test_troca_senha_atual_incorreta(self):
        self.api_key('alice')
        self.login('alice', SENHA)

        resp = self.client.post('/dcc/perfil/senha', data={
            'current_password': 'errada',
            'new_password': 'novaSenha123',
            'new_password_confirm': 'novaSenha123',
        })
        self.assertIn(b'Senha atual incorreta', resp.data)
        self.assertIsNotNone(auth.authenticate('alice', SENHA))

    def test_troca_senha_confirmacao_diferente(self):
        self.api_key('alice')
        self.login('alice', SENHA)

        resp = self.client.post('/dcc/perfil/senha', data={
            'current_password': SENHA,
            'new_password': 'novaSenha123',
            'new_password_confirm': 'outra12345',
        })
        self.assertIn('confirmação', resp.get_data(as_text=True).lower())

    def test_troca_senha_curta(self):
        self.api_key('alice')
        self.login('alice', SENHA)

        resp = self.client.post('/dcc/perfil/senha', data={
            'current_password': SENHA,
            'new_password': '123',
            'new_password_confirm': '123',
        })
        self.assertIn(b'pelo menos', resp.data)


class TestRecuperacaoSenha(AuthTestBase):

    def test_esqueci_senha_email_desconhecido_resposta_generica(self):
        resp = self.client.post('/dcc/esqueci-senha', data={'email': 'naoexiste@inmetro.gov.br'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Se o endereço estiver cadastrado', resp.get_data(as_text=True))

    def test_esqueci_senha_email_conhecido_resposta_generica(self):
        self.api_key('alice')
        resp = self.client.post('/dcc/esqueci-senha', data={'email': email_de('alice')})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Se o endereço estiver cadastrado', resp.get_data(as_text=True))

    def test_token_uso_unico(self):
        self.criar_usuario('alice')
        token = auth.create_password_reset_token(1)
        self.assertEqual(auth.consume_password_reset_token(token, 'novaSenha123'), 'alice')
        self.assertIsNone(auth.consume_password_reset_token(token, 'outraSenha123'))
        self.assertIsNotNone(auth.authenticate('alice', 'novaSenha123'))

    def test_token_expirado(self):
        self.criar_usuario('alice')
        token = auth.create_password_reset_token(1, ttl_minutes=-1)
        self.assertIsNone(auth.consume_password_reset_token(token, 'novaSenha123'))

    def test_novo_token_invalida_anterior(self):
        self.criar_usuario('alice')
        token1 = auth.create_password_reset_token(1)
        token2 = auth.create_password_reset_token(1)
        self.assertIsNone(auth.consume_password_reset_token(token1, 'novaSenha123'))
        self.assertEqual(auth.consume_password_reset_token(token2, 'novaSenha123'), 'alice')

    def test_limite_de_solicitacoes(self):
        self.criar_usuario('alice')
        for _ in range(auth.MAX_RESET_REQUESTS_PER_HOUR):
            auth.create_password_reset_token(1)
        self.assertGreaterEqual(
            auth.count_recent_reset_requests(1), auth.MAX_RESET_REQUESTS_PER_HOUR
        )

    def test_fluxo_completo_esqueci_e_redefinir(self):
        self.criar_usuario('alice')

        capturado = {}

        def fake_send(user, link):
            capturado['link'] = link
            return True

        original = main.send_password_reset_email
        main.send_password_reset_email = fake_send
        try:
            resp = self.client.post('/dcc/esqueci-senha', data={'email': email_de('alice')})
            self.assertEqual(resp.status_code, 200)
        finally:
            main.send_password_reset_email = original

        self.assertIn('link', capturado)
        self.assertTrue(capturado['link'].startswith('https://sig-dimci.inmetro.gov.br/dcc/redefinir-senha'))
        token = parse_qs(urlparse(capturado['link']).query)['token'][0]

        resp = self.client.post('/dcc/redefinir-senha', data={
            'token': token,
            'new_password': 'novaSenha123',
            'new_password_confirm': 'novaSenha123',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('reset=1', resp.headers['Location'])
        self.assertIsNotNone(auth.authenticate('alice', 'novaSenha123'))

    def test_link_usa_base_padrao(self):
        os.environ.pop('APP_BASE_URL', None)
        with app.test_request_context():
            link = main._reset_password_link('tok123')
        self.assertEqual(
            link, 'https://sig-dimci.inmetro.gov.br/dcc/redefinir-senha?token=tok123'
        )

    def test_link_usa_app_base_url(self):
        os.environ['APP_BASE_URL'] = 'https://exemplo.local/'
        try:
            with app.test_request_context():
                link = main._reset_password_link('tok123')
        finally:
            os.environ.pop('APP_BASE_URL', None)
        self.assertEqual(link, 'https://exemplo.local/dcc/redefinir-senha?token=tok123')

    def test_redefinir_com_token_invalido(self):
        resp = self.client.post('/dcc/redefinir-senha', data={
            'token': 'inexistente',
            'new_password': 'novaSenha123',
            'new_password_confirm': 'novaSenha123',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('inválido ou expirado', resp.get_data(as_text=True))


class TestRespostaTransicao(AuthTestBase):

    def test_api_sem_autenticacao_recebe_xml(self):
        resp = self.client.post('/dcc/generate', json={})
        self.assertEqual(resp.status_code, 401)
        self.assertIn('xml', resp.content_type)
        body = resp.get_data(as_text=True)
        self.assertIn('autenticacaoNecessaria', body)
        self.assertIn('X-API-Key', body)
        self.assertIn('/dcc/register', body)

    def test_navegador_get_recebe_redirect(self):
        resp = self.client.get('/dcc/form_dcc')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/dcc/login', resp.headers['Location'])


class TestAuthUnit(AuthTestBase):

    def test_tamanho_maximo_usuario(self):
        with self.assertRaises(ValueError):
            auth.create_user('a' * 65, SENHA, email_de('a'))

    def test_usuario_vazio(self):
        with self.assertRaises(ValueError):
            auth.create_user('   ', SENHA, email_de('a'))

    def test_senha_curta(self):
        with self.assertRaises(ValueError):
            auth.create_user('bob', '123', email_de('bob'))

    def test_email_obrigatorio(self):
        with self.assertRaises(ValueError):
            auth.create_user('bob', SENHA, '')

    def test_email_fora_do_dominio(self):
        with self.assertRaises(ValueError):
            auth.create_user('bob', SENHA, 'bob@example.com')

    def test_email_case_insensitive(self):
        created = auth.create_user('bob', SENHA, 'BOB@INMETRO.GOV.BR')
        self.assertEqual(created['email'], 'bob@inmetro.gov.br')
        self.assertIsNotNone(auth.get_user_by_email('BOB@INMETRO.GOV.BR'))

    def test_authenticate(self):
        self.criar_usuario('carol')
        self.assertIsNotNone(auth.authenticate('carol', SENHA))
        self.assertIsNone(auth.authenticate('carol', 'errada'))
        self.assertIsNone(auth.authenticate('ninguem', SENHA))

    def test_senha_armazenada_com_hash(self):
        self.criar_usuario('carol')
        row = _fetchone('SELECT password_hash FROM users WHERE username = ?', ('carol',))
        self.assertNotEqual(row[0], SENHA)
        self.assertTrue(check_password_hash(row[0], SENHA))

    def test_set_password(self):
        self.criar_usuario('carol')
        self.assertTrue(auth.set_password('carol', 'novasenha123'))
        self.assertIsNone(auth.authenticate('carol', SENHA))
        self.assertIsNotNone(auth.authenticate('carol', 'novasenha123'))

    def test_get_user_by_id(self):
        self.criar_usuario('carol')
        user = auth.get_user_by_id(1)
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'carol')
        self.assertIsNone(auth.get_user_by_id(999))

    def test_migracao_adiciona_colunas(self):
        _limpar_banco()
        conn = sqlite3.connect(_TMP_DB)
        try:
            conn.execute(
                'CREATE TABLE users ('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, email TEXT, '
                'api_key_hash TEXT NOT NULL UNIQUE, api_key_prefix TEXT NOT NULL, '
                'active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, last_used_at TEXT)'
            )
            conn.execute(
                "INSERT INTO users (username, api_key_hash, api_key_prefix, active, created_at) "
                "VALUES ('old', 'hash', 'dcc_old', 1, '2020-01-01T00:00:00+00:00')"
            )
            conn.commit()
        finally:
            conn.close()

        auth.init_db()
        conn = sqlite3.connect(_TMP_DB)
        try:
            cols = {r[1] for r in conn.execute('PRAGMA table_info(users)')}
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
        finally:
            conn.close()
        self.assertIn('password_hash', cols)
        self.assertIn('api_key', cols)
        self.assertIn('password_reset_tokens', tables)


class TestEmailService(unittest.TestCase):

    def tearDown(self):
        os.environ['DCC_EMAIL_ENABLED'] = 'false'
        os.environ.pop('SMTP_HOST', None)

    def test_envio_desabilitado_retorna_false(self):
        os.environ['DCC_EMAIL_ENABLED'] = 'false'
        self.assertFalse(email_service.send_email('x@inmetro.gov.br', 'assunto', 'corpo'))

    def test_envio_monta_mensagem(self):
        os.environ['DCC_EMAIL_ENABLED'] = 'true'
        os.environ['SMTP_HOST'] = 'smtp.test.local'

        capturado = {}

        class FakeSMTP:
            def __init__(self, host, port, timeout=None):
                capturado['host'] = host
                capturado['port'] = port

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def ehlo(self):
                pass

            def send_message(self, message):
                capturado['message'] = message

        original = email_service.smtplib.SMTP
        email_service.smtplib.SMTP = FakeSMTP
        try:
            ok = email_service.send_email('dest@inmetro.gov.br', 'Assunto', 'Corpo')
        finally:
            email_service.smtplib.SMTP = original

        self.assertTrue(ok)
        self.assertEqual(capturado['host'], 'smtp.test.local')
        self.assertEqual(capturado['port'], 587)
        self.assertEqual(capturado['message']['To'], 'dest@inmetro.gov.br')
        self.assertEqual(capturado['message']['Subject'], 'Assunto')
        self.assertIn('Corpo', capturado['message'].get_content())


if __name__ == '__main__':
    unittest.main()

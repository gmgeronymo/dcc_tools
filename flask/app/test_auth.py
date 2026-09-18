## Inmetro/Dimci/Diele/Lampe
# Testes automatizados da autenticacao (usuario/senha + API-KEY) do dccGenerator.

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

# Configura um banco isolado ANTES de importar a app.
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix='dcc_auth_test_'), 'dcc_auth.db')
os.environ['DCC_DB_PATH'] = _TMP_DB
os.environ['DCC_SECRET_KEY'] = 'secret-test-key'

from main import app  # noqa: E402
import auth  # noqa: E402
from werkzeug.security import check_password_hash  # noqa: E402

EXEMPLO_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'examples',
    'dcc_json.json',
)

SENHA = 'senha12345'


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
        payload = {'username': username, 'password': password}
        if email:
            payload['email'] = email
        return self.client.post('/dcc/register', json=payload)

    def api_key(self, username='alice', password=SENHA):
        resp = self.registrar(username, password)
        self.assertEqual(resp.status_code, 201)
        return resp.get_json()['api_key']

    def login(self, username='alice', password=SENHA):
        return self.client.post('/dcc/login', data={'username': username, 'password': password})

    def dados_exemplo(self):
        with open(EXEMPLO_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)


class TestRegistro(AuthTestBase):

    def test_registro_json_cria_usuario_e_retorna_chave(self):
        resp = self.registrar('alice', SENHA, 'alice@example.com')
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data['username'], 'alice')
        self.assertEqual(data['email'], 'alice@example.com')
        self.assertTrue(data['api_key'].startswith('dcc_'))

    def test_registro_duplicado_retorna_erro(self):
        self.assertEqual(self.registrar('alice').status_code, 201)
        resp = self.registrar('alice')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_registro_usuario_invalido(self):
        resp = self.registrar('usuario com espacos')
        self.assertEqual(resp.status_code, 400)

    def test_registro_senha_curta(self):
        resp = self.registrar('bob', password='123')
        self.assertEqual(resp.status_code, 400)

    def test_registro_via_formulario_exibe_chave(self):
        resp = self.client.post('/dcc/register', data={'username': 'bob', 'password': SENHA})
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
        for rota in ['/dcc/', '/dcc/api_doc', '/dcc/exemplos', '/dcc/faq']:
            self.assertEqual(self.client.get(rota).status_code, 200, rota)

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

    def test_login_nao_aceita_api_key_como_senha(self):
        key = self.api_key('alice')
        resp = self.login('alice', key)
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


class TestRespostaTransicao(AuthTestBase):

    def test_api_sem_autenticacao_recebe_xml(self):
        resp = self.client.post('/dcc/generate', json={})
        self.assertEqual(resp.status_code, 401)
        self.assertIn('xml', resp.content_type)
        body = resp.get_data(as_text=True)
        self.assertIn('autenticacaoNecessaria', body)
        self.assertIn('X-API-Key', body)
        self.assertIn('/dcc/register', body)
        self.assertIn('/dcc/api_doc', body)

    def test_api_com_accept_xml_recebe_xml(self):
        resp = self.client.post(
            '/dcc/generate', json={}, headers={'Accept': 'application/xml'}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn('autenticacaoNecessaria', resp.get_data(as_text=True))

    def test_chave_invalida_recebe_xml_com_instrucoes(self):
        resp = self.client.post(
            '/dcc/generate', json={}, headers={'X-API-Key': 'dcc_invalida'}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn('autenticacaoNecessaria', resp.get_data(as_text=True))

    def test_navegador_get_recebe_redirect(self):
        resp = self.client.get('/dcc/form_dcc')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/dcc/login', resp.headers['Location'])

    def test_formulario_browser_recebe_redirect(self):
        resp = self.client.post('/dcc/generate', data={}, headers={'Accept': 'text/html'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/dcc/login', resp.headers['Location'])


class TestAuthUnit(AuthTestBase):

    def test_tamanho_maximo_usuario(self):
        with self.assertRaises(ValueError):
            auth.create_user('a' * 65, SENHA)

    def test_usuario_vazio(self):
        with self.assertRaises(ValueError):
            auth.create_user('   ', SENHA)

    def test_senha_curta(self):
        with self.assertRaises(ValueError):
            auth.create_user('bob', '123')

    def test_authenticate(self):
        auth.create_user('carol', SENHA)
        self.assertIsNotNone(auth.authenticate('carol', SENHA))
        self.assertIsNone(auth.authenticate('carol', 'errada'))
        self.assertIsNone(auth.authenticate('ninguem', SENHA))

    def test_senha_armazenada_com_hash(self):
        auth.create_user('carol', SENHA)
        row = _fetchone('SELECT password_hash FROM users WHERE username = ?', ('carol',))
        self.assertNotEqual(row[0], SENHA)
        self.assertTrue(check_password_hash(row[0], SENHA))

    def test_set_password(self):
        auth.create_user('carol', SENHA)
        self.assertTrue(auth.set_password('carol', 'novasenha123'))
        self.assertIsNone(auth.authenticate('carol', SENHA))
        self.assertIsNotNone(auth.authenticate('carol', 'novasenha123'))

    def test_get_user_by_id(self):
        auth.create_user('carol', SENHA)
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
        finally:
            conn.close()
        self.assertIn('password_hash', cols)
        self.assertIn('api_key', cols)


if __name__ == '__main__':
    unittest.main()

## Inmetro/Dimci/Diele/Lampe
# Testes da validacao de XML e da allowlist de hosts de schema (anti-SSRF).

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

import os
import tempfile
import unittest
from io import BytesIO

os.environ.setdefault('DCC_DB_PATH', os.path.join(tempfile.mkdtemp(prefix='dcc_val_'), 'dcc_auth.db'))
os.environ.setdefault('DCC_SECRET_KEY', 'secret-test-key')

from main import app, is_allowed_schema_url, validate_dcc_xml_upload  # noqa: E402


class TestAllowlistSchema(unittest.TestCase):

    def test_hosts_permitidos(self):
        permitidos = [
            'https://ptb.de/si/v2.2.1/SI_Format.xsd',
            'https://www.ptb.de/dcc/v3.3.0/dcc.xsd',
            'http://sig.ptb.de/schema.xsd',
        ]
        for url in permitidos:
            self.assertTrue(is_allowed_schema_url(url), url)

    def test_hosts_bloqueados(self):
        bloqueados = [
            'http://169.254.169.254/latest/meta-data.xsd',   # link-local (cloud metadata)
            'http://127.0.0.1/schema.xsd',                    # loopback
            'http://localhost/schema.xsd',                    # localhost
            'http://10.0.0.5/schema.xsd',                     # rede privada
            'http://192.168.0.1/schema.xsd',                  # rede privada
            'ftp://www.ptb.de/schema.xsd',                    # esquema nao http(s)
            'https://evil.example/schema.xsd',                # host externo
            'https://ptb.de.evil.example/schema.xsd',         # truque de sufixo
            'https://notptb.de/schema.xsd',                   # termina parecido
            'https://user:pass@www.ptb.de/schema.xsd',        # credenciais embutidas
            'schema.xsd',                                     # relativo, sem host
        ]
        for url in bloqueados:
            self.assertFalse(is_allowed_schema_url(url), url)

    def test_allowlist_por_variavel_de_ambiente(self):
        os.environ['DCC_ALLOWED_SCHEMA_HOSTS'] = 'example.org, outro.net'
        try:
            self.assertTrue(is_allowed_schema_url('https://example.org/x.xsd'))
            self.assertTrue(is_allowed_schema_url('https://sub.example.org/x.xsd'))
            self.assertTrue(is_allowed_schema_url('https://outro.net/x.xsd'))
            self.assertFalse(is_allowed_schema_url('https://ptb.de/x.xsd'))
        finally:
            os.environ.pop('DCC_ALLOWED_SCHEMA_HOSTS', None)


class TestValidacaoBloqueiaSchemaNaoConfiavel(unittest.TestCase):

    def _validar(self, xml_content):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.xml', mode='w')
        try:
            tmp.write(xml_content)
            tmp.close()
            return validate_dcc_xml_upload(tmp.name)
        finally:
            os.unlink(tmp.name)

    def test_schema_em_host_privado_e_bloqueado(self):
        xml = (
            '<?xml version="1.0"?>'
            '<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="http://exemplo/ns http://169.254.169.254/evil.xsd"/>'
        )
        is_valid, errors = self._validar(xml)
        self.assertFalse(is_valid)
        self.assertTrue(any('não confiável' in e for e in errors), errors)

    def test_schema_em_host_externo_e_bloqueado(self):
        xml = (
            '<?xml version="1.0"?>'
            '<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="http://exemplo/ns https://evil.example/x.xsd"/>'
        )
        is_valid, errors = self._validar(xml)
        self.assertFalse(is_valid)
        self.assertTrue(any('não confiável' in e for e in errors), errors)


class TestRotaValidacao(unittest.TestCase):

    def test_rota_bloqueia_schema_nao_confiavel(self):
        xml = (
            '<?xml version="1.0"?>'
            '<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="http://exemplo/ns http://169.254.169.254/evil.xsd"/>'
        )
        client = app.test_client()
        resp = client.post(
            '/dcc/validate_xml',
            data={'xml_file': (BytesIO(xml.encode('utf-8')), 'teste.xml')},
            content_type='multipart/form-data',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('não confiável', resp.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()

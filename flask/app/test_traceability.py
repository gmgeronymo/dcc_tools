## Inmetro/Dimci/Diele/Lampe
# Testes automatizados da referencia a certificados de rastreabilidade que
# tambem sao DCC (hash SHA-256 em dcc:certificate).

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

import copy
import json
import os
import tempfile
import unittest
import uuid

# Configura um banco isolado ANTES de importar a app. Usa setdefault para
# nao sobrescrever a configuracao de outro modulo de teste na mesma execucao.
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix='dcc_trace_test_'), 'dcc_auth.db')
os.environ.setdefault('DCC_DB_PATH', _TMP_DB)
os.environ.setdefault('DCC_SECRET_KEY', 'secret-test-key')
os.environ.setdefault('DCC_EMAIL_ENABLED', 'false')

from lxml import etree  # noqa: E402

import auth  # noqa: E402
from main import (  # noqa: E402
    app,
    dccGen,
    declaracoes,
    excel_to_json,
    resolve_dcc_version,
    resolve_traceability_hash,
)

DCC_NS = '{https://ptb.de/dcc}'

EXEMPLO_PONTO_UNICO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'examples',
    'CC_DIMCI_0496_2025.json',
)

EXEMPLO_XLSX = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'examples',
    'CC_DIMCI_0496_2025.xlsx',
)

HASH = 'a' * 64


def carregar(caminho):
    with open(caminho, 'r', encoding='utf-8') as f:
        return json.load(f)


def preprocessar(dados):
    dados = copy.deepcopy(dados)
    if 'desc_chefe_div' in dados:
        dados['desc_chefe_div'] = dados['desc_chefe_div'] + ' da ' + dados['nome_div']
    else:
        dados['desc_chefe_div'] = 'Chefe da ' + dados['nome_div']

    if 'desc_chefe_lab' in dados:
        dados['desc_chefe_lab'] = dados['desc_chefe_lab'] + ' do ' + dados['nome_lab']
    else:
        dados['desc_chefe_lab'] = 'Chefe do ' + dados['nome_lab']

    return dados


def gerar(dados):
    dados = preprocessar(dados)
    declaracao = declaracoes(dados)
    versao = resolve_dcc_version(dados)
    return dccGen(versao, dados, declaracao)


def arvore(xml_bytes):
    return etree.fromstring(xml_bytes)


def certificado_rastreabilidade(root, name):
    for equipamento in root.iter(DCC_NS + 'measuringEquipment'):
        if equipamento.findtext(DCC_NS + 'name/' + DCC_NS + 'content') == name:
            return equipamento.find(DCC_NS + 'certificate')
    return None


class TestResolveTraceabilityHash(unittest.TestCase):

    def test_sem_hash_mantem_analogico(self):
        self.assertEqual(
            resolve_traceability_hash({'name': 'Padrão'}),
            ('analogue', 'analogue'))

    def test_hash_vazio_mantem_analogico(self):
        self.assertEqual(
            resolve_traceability_hash({'hash_sha256': '   '}),
            ('analogue', 'analogue'))

    def test_hash_sha256_valido(self):
        self.assertEqual(
            resolve_traceability_hash({'hash_sha256': HASH}),
            ('sha256', HASH))

    def test_hash_maiusculo_e_normalizado(self):
        self.assertEqual(
            resolve_traceability_hash({'hash_sha256': HASH.upper()}),
            ('sha256', HASH))

    def test_hash_procedure_personalizado(self):
        self.assertEqual(
            resolve_traceability_hash({
                'hash_sha256': HASH,
                'hash_procedure': 'enveloped-c14n-sha256',
            }),
            ('enveloped-c14n-sha256', HASH))

    def test_hash_procedure_invalido_gera_erro(self):
        with self.assertRaises(ValueError):
            resolve_traceability_hash({
                'hash_sha256': HASH,
                'hash_procedure': 'sha 256',
            })

    def test_hash_curto_gera_erro(self):
        with self.assertRaises(ValueError):
            resolve_traceability_hash({'hash_sha256': 'abc123'})

    def test_hash_nao_hexadecimal_gera_erro(self):
        with self.assertRaises(ValueError):
            resolve_traceability_hash({'hash_sha256': 'z' * 64})


class TestGeracaoTraceability(unittest.TestCase):

    def test_sem_hash_gera_certificado_analogico(self):
        root = arvore(gerar(carregar(EXEMPLO_PONTO_UNICO)))
        certificate = certificado_rastreabilidade(root, 'Resistor Padrão')

        self.assertIsNotNone(certificate)
        self.assertEqual(certificate.findtext(DCC_NS + 'procedure'), 'analogue')
        self.assertEqual(certificate.findtext(DCC_NS + 'value'), 'analogue')

    def test_hash_gera_procedure_sha256(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['tabela_rastreabilidade'][0]['hash_sha256'] = HASH.upper()

        root = arvore(gerar(dados))
        certificate = certificado_rastreabilidade(root, 'Resistor Padrão')

        self.assertEqual(certificate.findtext(DCC_NS + 'procedure'), 'sha256')
        self.assertEqual(certificate.findtext(DCC_NS + 'value'), HASH)

    def test_hash_em_uma_linha_nao_afeta_as_demais(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['tabela_rastreabilidade'].append({
            'name': 'Padrão analógico',
            'origem': 'PTB',
            'certificado': 'PTB 123/2020',
            'cod_id': 'PR 999',
        })
        dados['tabela_rastreabilidade'][0]['hash_sha256'] = HASH

        root = arvore(gerar(dados))

        dcc_certificate = certificado_rastreabilidade(root, 'Resistor Padrão')
        analog_certificate = certificado_rastreabilidade(root, 'Padrão analógico')

        self.assertEqual(dcc_certificate.findtext(DCC_NS + 'procedure'), 'sha256')
        self.assertEqual(dcc_certificate.findtext(DCC_NS + 'value'), HASH)
        self.assertEqual(analog_certificate.findtext(DCC_NS + 'procedure'), 'analogue')
        self.assertEqual(analog_certificate.findtext(DCC_NS + 'value'), 'analogue')


class TestExcelTraceability(unittest.TestCase):

    def _xlsx_com_hash(self, hash_value=None):
        from openpyxl import load_workbook

        wb = load_workbook(EXEMPLO_XLSX)
        ws = wb['Rastreabilidade']
        coluna = ws.max_column + 1
        ws.cell(row=1, column=coluna, value='hash_sha256')
        if hash_value is not None:
            ws.cell(row=2, column=coluna, value=hash_value)

        caminho = os.path.join(
            tempfile.mkdtemp(prefix='dcc_trace_xlsx_'), 'exemplo.xlsx')
        wb.save(caminho)
        return caminho

    def test_coluna_hash_vazia_nao_gera_valor_nan(self):
        dados = excel_to_json(self._xlsx_com_hash())

        self.assertTrue(dados['tabela_rastreabilidade'])
        for linha in dados['tabela_rastreabilidade']:
            self.assertNotIn('hash_sha256', linha)

    def test_coluna_hash_preenchida_e_convertida(self):
        dados = excel_to_json(self._xlsx_com_hash(HASH.upper()))

        self.assertEqual(
            dados['tabela_rastreabilidade'][0]['hash_sha256'],
            HASH.upper())


class TestRotaGenerateTraceability(unittest.TestCase):

    def setUp(self):
        auth.init_db()
        app.config['TESTING'] = True
        self.client = app.test_client()

    def api_key(self):
        sufixo = uuid.uuid4().hex[:10]
        username = 'trace_%s' % sufixo
        user = auth.create_user(
            username,
            'senha12345',
            '%s@inmetro.gov.br' % username,
        )
        return user['api_key']

    def test_hash_invalido_retorna_400(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['tabela_rastreabilidade'][0]['hash_sha256'] = 'abc'

        resp = self.client.post(
            '/dcc/generate', json=dados,
            headers={'X-API-Key': self.api_key()})

        self.assertEqual(resp.status_code, 400)
        self.assertIn('hash_sha256', resp.get_json()['error'])

    def test_hash_valido_gera_xml_200(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['tabela_rastreabilidade'][0]['hash_sha256'] = HASH

        resp = self.client.post(
            '/dcc/generate', json=dados,
            headers={'X-API-Key': self.api_key()})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'text/xml')

        certificate = certificado_rastreabilidade(arvore(resp.data), 'Resistor Padrão')
        self.assertEqual(certificate.findtext(DCC_NS + 'procedure'), 'sha256')
        self.assertEqual(certificate.findtext(DCC_NS + 'value'), HASH)


if __name__ == '__main__':
    unittest.main()

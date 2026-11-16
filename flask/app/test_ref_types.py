## Inmetro/Dimci/Diele/Lampe
# Testes do comportamento pass-through de refTypes no gerador DCC.
# O dcc_tools nao infere refType nem adiciona definicoes: o cliente envia.

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

# Configura um banco isolado ANTES de importar a app.
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix='dcc_ref_type_test_'), 'dcc_auth.db')
os.environ.setdefault('DCC_DB_PATH', _TMP_DB)
os.environ.setdefault('DCC_SECRET_KEY', 'secret-test-key')
os.environ.setdefault('DCC_EMAIL_ENABLED', 'false')

from lxml import etree  # noqa: E402

import auth  # noqa: E402
from main import (  # noqa: E402
    app,
    declaracoes,
    dccGen,
    excel_to_json,
    resolve_dcc_version,
)

DCC_NS = '{https://ptb.de/dcc}'
EXEMPLO_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'examples',
    'dcc_json.json',
)
EXEMPLO_XLSX = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'examples',
    'CC_DIMCI_0515_2025.xlsx',
)


def carregar(caminho=EXEMPLO_JSON):
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


def quantity_por_nome(root, nome):
    for quantity in root.iter(DCC_NS + 'quantity'):
        if quantity.findtext(DCC_NS + 'name/' + DCC_NS + 'content') == nome:
            return quantity
    return None


def definicoes(root, namespace):
    return [
        definicao for definicao in root.iter(DCC_NS + 'refTypeDefinition')
        if definicao.findtext(DCC_NS + 'namespace') == namespace
    ]


def indice_current(dados):
    for indice in dados.get('indices', []) or []:
        if str(indice.get('label', '')).lower() == 'current':
            return indice
    raise AssertionError('indice current nao encontrado no exemplo')


def remover_ref_type_current(dados):
    indice_current(dados).pop('refType', None)
    return dados


def remover_definicao_electromagnetic(dados):
    dados['refTypeDefinitions'] = [
        definicao for definicao in dados.get('refTypeDefinitions', []) or []
        if definicao.get('namespace') != 'electromagnetic'
    ]
    return dados


class TestRefTypePassThrough(unittest.TestCase):

    def test_exemplo_tem_refType_e_definicao(self):
        dados = carregar()
        self.assertEqual(
            indice_current(dados).get('refType'),
            'electromagnetic_measuringCurrent',
        )
        self.assertEqual(
            len([
                d for d in dados.get('refTypeDefinitions', [])
                if d.get('namespace') == 'electromagnetic'
            ]), 1,
        )

    def test_quantity_current_mantem_refType_enviado(self):
        root = arvore(gerar(carregar()))
        quantidade = quantity_por_nome(root, 'Corrente')

        self.assertIsNotNone(quantidade)
        self.assertEqual(
            quantidade.get('refType'),
            'electromagnetic_measuringCurrent',
        )
        self.assertEqual(len(definicoes(root, 'electromagnetic')), 1)

    def test_sem_refType_current_nao_infere(self):
        dados = remover_ref_type_current(carregar())
        remover_definicao_electromagnetic(dados)

        root = arvore(gerar(dados))
        quantidade = quantity_por_nome(root, 'Corrente')

        self.assertIsNotNone(quantidade)
        self.assertIsNone(quantidade.get('refType'))
        self.assertEqual(len(definicoes(root, 'electromagnetic')), 0)

    def test_refType_sem_definicao_nao_adiciona_definicao(self):
        dados = remover_definicao_electromagnetic(carregar())

        root = arvore(gerar(dados))
        quantidade = quantity_por_nome(root, 'Corrente')

        self.assertEqual(
            quantidade.get('refType'),
            'electromagnetic_measuringCurrent',
        )
        self.assertEqual(len(definicoes(root, 'electromagnetic')), 0)

    def test_definicao_do_cliente_e_preservada(self):
        dados = carregar()
        for definicao in dados.get('refTypeDefinitions', []):
            if definicao.get('namespace') == 'electromagnetic':
                definicao['name'] = 'Definicao do cliente'
                definicao['link'] = 'https://example.org/vocab'

        root = arvore(gerar(dados))
        encontradas = definicoes(root, 'electromagnetic')

        self.assertEqual(len(encontradas), 1)
        self.assertEqual(
            encontradas[0].findtext(DCC_NS + 'link'),
            'https://example.org/vocab',
        )
        self.assertEqual(
            encontradas[0].findtext(DCC_NS + 'name/' + DCC_NS + 'content'),
            'Definicao do cliente',
        )

    def test_excel_nao_infere_refType_nem_definicao(self):
        dados = excel_to_json(EXEMPLO_XLSX)
        current = indice_current(dados)

        self.assertNotIn('refType', current)
        self.assertEqual(
            len([
                d for d in dados.get('refTypeDefinitions', []) or []
                if d.get('namespace') == 'electromagnetic'
            ]), 0,
        )


class TestRotaGenerateRefType(unittest.TestCase):

    def setUp(self):
        caminho = auth._db_path()
        for path in (caminho, caminho + '-wal', caminho + '-shm'):
            if os.path.exists(path):
                os.remove(path)
        auth.init_db()
        app.config['TESTING'] = True
        self.client = app.test_client()

    def _api_key(self):
        resp = self.client.post('/dcc/register', json={
            'username': 'ref_type_user',
            'password': 'senha12345',
            'email': 'ref_type_user@inmetro.gov.br',
        })
        self.assertEqual(resp.status_code, 201)
        return resp.get_json()['api_key']

    def test_payload_sem_refType_retorna_200_sem_inferencia(self):
        dados = remover_ref_type_current(carregar())
        remover_definicao_electromagnetic(dados)

        resp = self.client.post(
            '/dcc/generate', json=dados,
            headers={'X-API-Key': self._api_key()})

        self.assertEqual(resp.status_code, 200)
        root = arvore(resp.data)
        quantidade = quantity_por_nome(root, 'Corrente')
        self.assertIsNone(quantidade.get('refType'))
        self.assertEqual(len(definicoes(root, 'electromagnetic')), 0)

    def test_payload_com_refType_e_definicao_retorna_200(self):
        resp = self.client.post(
            '/dcc/generate', json=carregar(),
            headers={'X-API-Key': self._api_key()})

        self.assertEqual(resp.status_code, 200)
        root = arvore(resp.data)
        quantidade = quantity_por_nome(root, 'Corrente')
        self.assertEqual(
            quantidade.get('refType'),
            'electromagnetic_measuringCurrent',
        )
        self.assertEqual(len(definicoes(root, 'electromagnetic')), 1)


if __name__ == '__main__':
    unittest.main()

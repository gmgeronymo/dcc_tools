## Inmetro/Dimci/Diele/Lampe
# Testes automatizados do valor nominal estruturado do item (DKD-E 1-1).
#
# Author: Gean Marcos Geronymo
#
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
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix='dcc_nominal_test_'), 'dcc_auth.db')
os.environ.setdefault('DCC_DB_PATH', _TMP_DB)
os.environ.setdefault('DCC_SECRET_KEY', 'secret-test-key')
os.environ.setdefault('DCC_EMAIL_ENABLED', 'false')

from lxml import etree  # noqa: E402

import auth  # noqa: E402
from main import (  # noqa: E402
    app,
    declaracoes,
    dccGen,
    resolve_dcc_version,
    resolve_nominal_value,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_DIR = os.path.join(BASE_DIR, 'static', 'examples')
XSLT_PATH = os.path.join(EXAMPLES_DIR, 'xslt', 'hr_template.xsl')
EXEMPLO_PONTO_UNICO = os.path.join(EXAMPLES_DIR, 'CC_DIMCI_0496_2025.json')

DCC_NS = '{https://ptb.de/dcc}'
SI_NS = '{https://ptb.de/si}'

BASIC_DEFINITION = {
    'name': 'Namespace for Cross-Community RefTypes',
    'description': "The 'basic' namespace contains RefTypes common for multiple communities.",
    'namespace': 'basic',
    'link': 'https://digilab.ptb.de/dkd/refType/vocab/index.php?tema=2',
}


def adicionar_basic(dados):
    definicoes = dados.setdefault('refTypeDefinitions', [])
    if any(
            isinstance(definicao, dict)
            and definicao.get('namespace') == 'basic'
            for definicao in definicoes):
        return dados
    definicoes.append(dict(BASIC_DEFINITION))
    return dados


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


def gerar(dados, basic=True):
    dados = preprocessar(dados)
    if basic:
        adicionar_basic(dados)
    declaracao = declaracoes(dados)
    versao = resolve_dcc_version(dados)
    return dccGen(versao, dados, declaracao)


def transformar(xml_bytes):
    xml_doc = etree.fromstring(xml_bytes)
    xslt_doc = etree.parse(XSLT_PATH)
    return str(etree.XSLT(xslt_doc)(xml_doc))


class TestResolveNominalValue(unittest.TestCase):

    def test_ausente_retorna_none(self):
        self.assertIsNone(resolve_nominal_value({}))
        self.assertIsNone(resolve_nominal_value({'valor_nominal': ''}))

    def test_objeto_estruturado(self):
        config = resolve_nominal_value({
            'valor_nominal': {'valor': '100', 'unidade': '\\ohm'},
        })

        self.assertEqual(config['valor'], '100')
        self.assertEqual(config['unidade'], '\\ohm')
        self.assertEqual(config['nome'], 'Valor nominal')
        self.assertIsNone(config['descricao'])

    def test_nome_e_descricao_personalizados(self):
        config = resolve_nominal_value({
            'valor_nominal': {
                'valor': '1',
                'unidade': '\\kilo\\ohm',
                'nome': 'Resistência nominal',
                'descricao': 'Valor impresso no painel',
            },
        })

        self.assertEqual(config['nome'], 'Resistência nominal')
        self.assertEqual(config['descricao'], 'Valor impresso no painel')

    def test_formato_legado_com_valnom_unit(self):
        config = resolve_nominal_value({
            'valor_nominal': '1',
            'valnom_unit': '\\ohm',
        })

        self.assertEqual(config['valor'], '1')
        self.assertEqual(config['unidade'], '\\ohm')

    def test_valor_obrigatorio(self):
        with self.assertRaises(ValueError):
            resolve_nominal_value({'valor_nominal': {'unidade': '\\ohm'}})

    def test_unidade_obrigatoria(self):
        with self.assertRaises(ValueError):
            resolve_nominal_value({'valor_nominal': {'valor': '100'}})

    def test_tipo_invalido(self):
        with self.assertRaises(ValueError):
            resolve_nominal_value({'valor_nominal': ['100', '\\ohm']})


class TestGeracaoNominal(unittest.TestCase):

    def test_emite_item_quantity_estruturado(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['valor_nominal'] = {
            'valor': '100',
            'unidade': '\\kilo\\ohm',
            'nome': 'Valor nominal',
            'descricao': 'Valor impresso no item',
        }

        root = etree.fromstring(gerar(dados))
        quantidade = root.find(
            './/' + DCC_NS + 'item/' + DCC_NS + 'itemQuantities/'
            + DCC_NS + 'itemQuantity')

        self.assertIsNotNone(quantidade)
        self.assertEqual(quantidade.get('refType'), 'basic_nominalValue')
        self.assertEqual(
            quantidade.findtext(DCC_NS + 'name/' + DCC_NS + 'content'),
            'Valor nominal',
        )
        self.assertEqual(
            quantidade.findtext(DCC_NS + 'description/' + DCC_NS + 'content'),
            'Valor impresso no item',
        )
        self.assertEqual(
            quantidade.findtext(SI_NS + 'real/' + SI_NS + 'value'),
            '100',
        )
        self.assertEqual(
            quantidade.findtext(SI_NS + 'real/' + SI_NS + 'unit'),
            '\\kilo\\ohm',
        )

    def test_declara_namespace_basic_informado_pelo_usuario(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['valor_nominal'] = {'valor': '100', 'unidade': '\\ohm'}

        root = etree.fromstring(gerar(dados))
        definicoes = root.findall(
            './/' + DCC_NS + 'refTypeDefinition['
            + DCC_NS + 'namespace="basic"]')

        self.assertEqual(len(definicoes), 1)

    def test_valor_nominal_sem_basic_declarado_automaticamente(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['valor_nominal'] = {'valor': '100', 'unidade': '\\ohm'}

        root = etree.fromstring(gerar(dados, basic=False))

        self.assertIsNotNone(root.find('.//' + DCC_NS + 'itemQuantity'))
        self.assertEqual(
            len(root.findall(
                './/' + DCC_NS + 'refTypeDefinition['
                + DCC_NS + 'namespace="basic"]')),
            1,
        )

    def test_sem_valor_nominal_nao_emite_item_quantities(self):
        root = etree.fromstring(gerar(carregar(EXEMPLO_PONTO_UNICO)))

        self.assertIsNone(
            root.find('.//' + DCC_NS + 'item/' + DCC_NS + 'itemQuantities'))

    def test_cmc_e_nominal_nao_duplicam_namespace_basic(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['cmc'] = True
        dados['valor_nominal'] = {'valor': '100', 'unidade': '\\ohm'}

        root = etree.fromstring(gerar(dados))
        definicoes = root.findall(
            './/' + DCC_NS + 'refTypeDefinition['
            + DCC_NS + 'namespace="basic"]')

        self.assertEqual(len(definicoes), 1)


class TestCaracteristicasItemOpcional(unittest.TestCase):

    def _statements_caracteristicas(self, root):
        statements = []
        for statement in root.iter(DCC_NS + 'statement'):
            name = statement.findtext(DCC_NS + 'name/' + DCC_NS + 'content')
            if name == 'Características do Item':
                statements.append(statement)
        return statements

    def test_sem_caracteristicas_com_valor_nominal(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados.pop('caracteristicas_item', None)
        dados['valor_nominal'] = {'valor': '100', 'unidade': '\\ohm'}

        root = etree.fromstring(gerar(dados))

        self.assertEqual(self._statements_caracteristicas(root), [])
        self.assertIsNotNone(root.find('.//' + DCC_NS + 'itemQuantity'))

    def test_caracteristicas_vazio_nao_emite_statement(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['caracteristicas_item'] = '   '

        root = etree.fromstring(gerar(dados))

        self.assertEqual(self._statements_caracteristicas(root), [])

    def test_sem_caracteristicas_e_sem_valor_nominal(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados.pop('caracteristicas_item', None)

        root = etree.fromstring(gerar(dados))

        self.assertEqual(self._statements_caracteristicas(root), [])
        self.assertIsNone(root.find('.//' + DCC_NS + 'itemQuantities'))

    def test_caracteristicas_informado_continua_emitindo(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['caracteristicas_item'] = 'Descrição do item'

        root = etree.fromstring(gerar(dados))
        statements = self._statements_caracteristicas(root)

        self.assertEqual(len(statements), 1)
        self.assertEqual(
            statements[0].findtext(DCC_NS + 'description/' + DCC_NS + 'content'),
            'Descrição do item',
        )


class TestVisualizacaoNominal(unittest.TestCase):
    def test_exibe_valor_nominal_nas_caracteristicas(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['valor_nominal'] = {
            'valor': '100',
            'unidade': '\\kilo\\ohm',
        }

        html = transformar(gerar(dados))

        self.assertIn('Características do Item', html)
        self.assertIn('Valor nominal: ', html)
        self.assertIn('100 kΩ', html)

    def test_exibe_valor_nominal_sem_caracteristicas(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['caracteristicas_item'] = ''
        dados['valor_nominal'] = {
            'valor': '100',
            'unidade': '\\kilo\\ohm',
        }

        html = transformar(gerar(dados))

        self.assertIn('Características do Item', html)
        self.assertIn('Valor nominal: ', html)


class TestRotaGenerateNominal(unittest.TestCase):

    def setUp(self):
        caminho = auth._db_path()
        for path in (caminho, caminho + '-wal', caminho + '-shm'):
            if os.path.exists(path):
                os.remove(path)
        auth.init_db()
        app.config['TESTING'] = True
        self.client = app.test_client()

    def _api_key(self, username='nominal_user'):
        resp = self.client.post('/dcc/register', json={
            'username': username,
            'password': 'senha12345',
            'email': '%s@inmetro.gov.br' % username,
        })
        self.assertEqual(resp.status_code, 201)
        return resp.get_json()['api_key']

    def test_valor_nominal_sem_basic_retorna_200(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['valor_nominal'] = {'valor': '100', 'unidade': '\\ohm'}

        resp = self.client.post(
            '/dcc/generate', json=dados,
            headers={'X-API-Key': self._api_key()})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'text/xml')
        root = etree.fromstring(resp.data)
        self.assertIsNotNone(root.find('.//' + DCC_NS + 'itemQuantity'))

    def test_valor_nominal_com_basic_retorna_200(self):
        dados = adicionar_basic(carregar(EXEMPLO_PONTO_UNICO))
        dados['valor_nominal'] = {'valor': '100', 'unidade': '\\ohm'}

        resp = self.client.post(
            '/dcc/generate', json=dados,
            headers={'X-API-Key': self._api_key('nominal_user_2')})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'text/xml')
        root = etree.fromstring(resp.data)
        self.assertIsNotNone(root.find('.//' + DCC_NS + 'itemQuantity'))


if __name__ == '__main__':
    unittest.main()

## Inmetro/Dimci/Diele/Lampe
# Testes automatizados da marcacao de pontos dentro/fora da CMC
# (basic_isInCMC) no gerador DCC (dccGenerator).

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

# Configura um banco isolado ANTES de importar a app. Usa setdefault para
# nao sobrescrever a configuracao de outro modulo de teste na mesma execucao.
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix='dcc_cmc_test_'), 'dcc_auth.db')
os.environ.setdefault('DCC_DB_PATH', _TMP_DB)
os.environ.setdefault('DCC_SECRET_KEY', 'secret-test-key')
os.environ.setdefault('DCC_EMAIL_ENABLED', 'false')

from lxml import etree  # noqa: E402

import auth  # noqa: E402
from main import (  # noqa: E402
    app,
    dccGen,
    declaracoes,
    resolve_cmc_config,
    resolve_dcc_version,
)

DCC_NS = '{https://ptb.de/dcc}'

EXEMPLO_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'examples',
    'dcc_json.json',
)
EXEMPLO_PONTO_UNICO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'examples',
    'CC_DIMCI_0496_2025.json',
)


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


def statement_cmc(root):
    for statement in root.iter(DCC_NS + 'statement'):
        if statement.get('refType') == 'basic_isInCMC':
            return statement
    return None


def quantidade_resultado(root, name):
    for quantity in root.iter(DCC_NS + 'quantity'):
        if quantity.findtext(DCC_NS + 'name/' + DCC_NS + 'content') == name:
            if quantity.find(DCC_NS + 'measurementMetaData') is not None:
                return quantity
    return None


def metadados_cmc(root, ref_id='inCMC'):
    encontrados = []
    for meta in root.iter(DCC_NS + 'metaData'):
        if meta.get('refId') == ref_id:
            encontrados.append(meta)
    return encontrados


class TestResolveCmcConfig(unittest.TestCase):

    def test_sem_marcacao_nao_ativa_vinculos(self):
        config = resolve_cmc_config(carregar(EXEMPLO_JSON))
        self.assertFalse(config['enabled'])
        self.assertFalse(config['default'])
        self.assertTrue(config['statement'])

    def test_sem_cmc_sem_marcacao_nao_emite_statement(self):
        dados = carregar(EXEMPLO_JSON)
        dados['cmc'] = False
        config = resolve_cmc_config(dados)
        self.assertFalse(config['enabled'])
        self.assertFalse(config['statement'])

    def test_in_cmc_ativa_marcacao(self):
        dados = carregar(EXEMPLO_JSON)
        dados['resultados'][0]['in_cmc'] = 'Sim'
        config = resolve_cmc_config(dados)
        self.assertTrue(config['enabled'])
        self.assertFalse(config['default'])

    def test_cmc_padrao_ativa_marcacao(self):
        dados = carregar(EXEMPLO_JSON)
        dados['cmc_padrao'] = True
        config = resolve_cmc_config(dados)
        self.assertTrue(config['enabled'])
        self.assertTrue(config['default'])

    def test_valor_invalido_gera_erro(self):
        dados = carregar(EXEMPLO_JSON)
        dados['resultados'][0]['in_cmc'] = 'talvez'
        with self.assertRaises(ValueError):
            resolve_cmc_config(dados)

    def test_cmc_padrao_invalido_gera_erro(self):
        dados = carregar(EXEMPLO_JSON)
        dados['cmc_padrao'] = 'talvez'
        with self.assertRaises(ValueError):
            resolve_cmc_config(dados)

    def test_id_invalido_gera_erro(self):
        dados = carregar(EXEMPLO_JSON)
        dados['cmc_padrao'] = True
        dados['cmc_declaracao'] = {'id': 'id com espaço'}
        with self.assertRaises(ValueError):
            resolve_cmc_config(dados)


class TestGeracaoCmc(unittest.TestCase):

    def test_cmc_true_sem_in_cmc_emite_statement_estruturado(self):
        root = arvore(gerar(carregar(EXEMPLO_JSON)))
        statement = statement_cmc(root)
        self.assertIsNotNone(statement)
        self.assertEqual(statement.get('id'), 'inCMC')
        self.assertIsNotNone(statement.find(DCC_NS + 'declaration'))
        self.assertEqual(metadados_cmc(root), [])

    def test_sem_cmc_sem_marcacao_nao_emite_statement(self):
        dados = carregar(EXEMPLO_JSON)
        dados['cmc'] = False
        root = arvore(gerar(dados))
        self.assertIsNone(statement_cmc(root))
        self.assertEqual(metadados_cmc(root), [])

    def test_marcacao_por_ponto_com_lista_mista(self):
        dados = carregar(EXEMPLO_JSON)
        resultados = [r for r in dados['resultados'] if r['mensurando'] == 'acdc']
        self.assertGreater(len(resultados), 2)
        for i, resultado in enumerate(resultados):
            resultado['in_cmc'] = 'true' if i < 2 else 'false'

        root = arvore(gerar(dados))

        statement = statement_cmc(root)
        self.assertIsNotNone(statement)
        self.assertEqual(statement.get('id'), 'inCMC')
        self.assertEqual(statement.findtext(DCC_NS + 'name/' + DCC_NS + 'content'), 'CIPM-MRA')
        self.assertIsNotNone(statement.find(DCC_NS + 'reference'))
        self.assertIsNotNone(statement.find(DCC_NS + 'link'))
        self.assertIsNotNone(statement.find(DCC_NS + 'respAuthority'))
        self.assertIsNone(statement.find(DCC_NS + 'valid'))

        quantity = quantidade_resultado(root, '\\delta_u')
        self.assertIsNotNone(quantity)
        meta = quantity.find(DCC_NS + 'measurementMetaData/' + DCC_NS + 'metaData')
        self.assertEqual(meta.get('refId'), 'inCMC')
        valid_list = meta.findtext(DCC_NS + 'validXMLList')
        self.assertIsNotNone(valid_list)
        self.assertEqual(valid_list.split(), ['true', 'true'] + ['false'] * (len(resultados) - 2))

    def test_marcacao_reaproveita_statement_sem_duplicar(self):
        dados = carregar(EXEMPLO_JSON)
        dados['resultados'][0]['in_cmc'] = True

        root = arvore(gerar(dados))
        statements = list(root.iter(DCC_NS + 'statement'))

        cmc_statements = [s for s in statements if s.get('refType') == 'basic_isInCMC']
        self.assertEqual(len(cmc_statements), 1)

        declaracoes_mra = [
            s for s in statements
            if (s.findtext(DCC_NS + 'declaration/' + DCC_NS + 'content') or '')
            .find('Acordo de Reconhecimento') >= 0
        ]
        self.assertEqual(len(declaracoes_mra), 1)

    def test_cmc_padrao_aplica_a_pontos_sem_in_cmc(self):
        dados = carregar(EXEMPLO_JSON)
        resultados = [r for r in dados['resultados'] if r['mensurando'] == 'acdc']
        dados['cmc_padrao'] = True
        resultados[1]['in_cmc'] = False

        root = arvore(gerar(dados))
        quantity = quantidade_resultado(root, '\\delta_u')
        meta = quantity.find(DCC_NS + 'measurementMetaData/' + DCC_NS + 'metaData')
        valores = meta.findtext(DCC_NS + 'validXMLList').split()

        self.assertEqual(valores[1], 'false')
        self.assertTrue(all(v == 'true' for i, v in enumerate(valores) if i != 1))

    def test_cmc_padrao_false_torna_pontos_nao_marcados_false(self):
        dados = carregar(EXEMPLO_JSON)
        resultados = [r for r in dados['resultados'] if r['mensurando'] == 'acdc']
        dados['cmc_padrao'] = False
        resultados[0]['in_cmc'] = True

        root = arvore(gerar(dados))
        quantity = quantidade_resultado(root, '\\delta_u')
        meta = quantity.find(DCC_NS + 'measurementMetaData/' + DCC_NS + 'metaData')
        valores = meta.findtext(DCC_NS + 'validXMLList').split()

        self.assertEqual(valores[0], 'true')
        self.assertTrue(all(v == 'false' for v in valores[1:]))

    def test_ponto_unico_usa_valid(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['resultados'][0]['in_cmc'] = 'Não'

        root = arvore(gerar(dados))
        quantity = quantidade_resultado(root, 'V.m.')
        self.assertIsNotNone(quantity)
        meta = quantity.find(DCC_NS + 'measurementMetaData/' + DCC_NS + 'metaData')
        self.assertEqual(meta.findtext(DCC_NS + 'valid'), 'false')
        self.assertIsNone(meta.find(DCC_NS + 'validXMLList'))

    def test_declaracao_personalizada(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['resultados'][0]['in_cmc'] = True
        dados['cmc_declaracao'] = {
            'id': 'escopoRBC',
            'nome': 'Cgcre/RBC',
            'referencia': 'Escopo de acreditação RBC 1234',
            'link': 'https://www.gov.br/inmetro/pt-br/acesso-a-informacao/acreditacao',
            'descricao': 'Cobertura conforme escopo acreditado.',
            'autoridade': {
                'nome': 'Cgcre/Inmetro',
                'cidade': 'Duque de Caxias',
                'pais': 'BR',
            },
        }

        root = arvore(gerar(dados))
        statement = statement_cmc(root)
        self.assertEqual(statement.get('id'), 'escopoRBC')
        self.assertEqual(
            statement.findtext(DCC_NS + 'name/' + DCC_NS + 'content'), 'Cgcre/RBC')
        self.assertEqual(
            statement.findtext(DCC_NS + 'respAuthority/' + DCC_NS + 'name/' + DCC_NS + 'content'),
            'Cgcre/Inmetro')

        meta = metadados_cmc(root, 'escopoRBC')
        self.assertEqual(len(meta), 1)
        self.assertEqual(meta[0].findtext(DCC_NS + 'valid'), 'true')

    def test_namespace_basic_declarado_automaticamente(self):
        dados = carregar(EXEMPLO_JSON)
        dados['resultados'][0]['in_cmc'] = True

        root = arvore(gerar(dados))
        definicoes = [
            d for d in root.iter(DCC_NS + 'refTypeDefinition')
            if d.findtext(DCC_NS + 'namespace') == 'basic'
        ]
        self.assertEqual(len(definicoes), 1)

    def test_namespace_basic_nao_duplicado(self):
        dados = carregar(EXEMPLO_JSON)
        dados['resultados'][0]['in_cmc'] = True
        dados.setdefault('refTypeDefinitions', []).append({
            'name': 'Basic',
            'description': 'Definicao informada pelo usuario.',
            'namespace': 'basic',
            'link': 'https://digilab.ptb.de/dkd/refType/vocab/index.php?tema=2',
        })

        root = arvore(gerar(dados))
        definicoes = [
            d for d in root.iter(DCC_NS + 'refTypeDefinition')
            if d.findtext(DCC_NS + 'namespace') == 'basic'
        ]
        self.assertEqual(len(definicoes), 1)
        self.assertEqual(
            definicoes[0].findtext(DCC_NS + 'description/' + DCC_NS + 'content'),
            'Definicao informada pelo usuario.')

    def test_ordem_dos_elementos_no_statement_e_na_quantity(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['resultados'][0]['in_cmc'] = True
        dados['mensurando'][0]['relative_uncertainty_in_dcc'] = True

        root = arvore(gerar(dados))

        statement = statement_cmc(root)
        filhos = [etree.QName(filho).localname for filho in statement]
        self.assertEqual(
            filhos,
            ['name', 'description', 'reference', 'link', 'declaration', 'respAuthority'])

        quantity = quantidade_resultado(root, 'V.m.')
        filhos_quantity = [etree.QName(filho).localname for filho in quantity]
        self.assertIn('relativeUncertainty', filhos_quantity)
        self.assertIn('measurementMetaData', filhos_quantity)
        self.assertLess(
            filhos_quantity.index('relativeUncertainty'),
            filhos_quantity.index('measurementMetaData'))


class TestRotaGenerateCmc(unittest.TestCase):

    def setUp(self):
        # garante banco limpo mesmo quando outro modulo definiu o caminho
        caminho = auth._db_path()
        for path in (caminho, caminho + '-wal', caminho + '-shm'):
            if os.path.exists(path):
                os.remove(path)
        auth.init_db()
        app.config['TESTING'] = True
        self.client = app.test_client()

    def api_key(self, username='cmc_user'):
        resp = self.client.post('/dcc/register', json={
            'username': username,
            'password': 'senha12345',
            'email': '%s@inmetro.gov.br' % username,
        })
        self.assertEqual(resp.status_code, 201)
        return resp.get_json()['api_key']

    def test_in_cmc_invalido_retorna_400(self):
        dados = carregar(EXEMPLO_JSON)
        dados['resultados'][0]['in_cmc'] = 'talvez'
        resp = self.client.post(
            '/dcc/generate', json=dados,
            headers={'X-API-Key': self.api_key()})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('in_cmc', resp.get_json()['error'])

    def test_marcacao_gera_xml_200(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['resultados'][0]['in_cmc'] = False
        resp = self.client.post(
            '/dcc/generate', json=dados,
            headers={'X-API-Key': self.api_key('cmc_user_2')})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'text/xml')
        root = arvore(resp.data)
        self.assertIsNotNone(statement_cmc(root))


if __name__ == '__main__':
    unittest.main()

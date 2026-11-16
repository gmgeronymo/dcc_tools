## Inmetro/Dimci/Diele/Lampe
# Testes da migracao da incerteza expandida para D-SI 2.2.1 (expandedMU)
# e da validacao da incerteza relativa.

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
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix='dcc_uncertainty_test_'), 'dcc_auth.db')
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
    resolve_uncertainty_norm,
    validate_relative_uncertainty,
)

DCC_NS = '{https://ptb.de/dcc}'
EXEMPLO_PONTO_UNICO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'examples',
    'CC_DIMCI_0496_2025.json',
)


def carregar(caminho=EXEMPLO_PONTO_UNICO):
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


def used_method_incerteza(root):
    for method in root.iter(DCC_NS + 'usedMethod'):
        if method.findtext(
                DCC_NS + 'name/' + DCC_NS + 'content') == 'Declaração da Incerteza de Medição':
            return method
    return None


class TestResolveDccVersion(unittest.TestCase):

    def test_versao_omitida_usa_330(self):
        self.assertEqual(resolve_dcc_version({}), '3.3.0')

    def test_versao_330_aceita(self):
        self.assertEqual(resolve_dcc_version({'dcc_version': '3.3.0'}), '3.3.0')

    def test_alias_schema_version_aceito(self):
        self.assertEqual(resolve_dcc_version({'schema_version': '3.3.0'}), '3.3.0')

    def test_versao_320_rejeitada(self):
        with self.assertRaises(ValueError):
            resolve_dcc_version({'dcc_version': '3.2.0'})

    def test_versao_desconhecida_rejeitada(self):
        with self.assertRaises(ValueError):
            resolve_dcc_version({'dcc_version': '9.9.9'})


class TestValidateRelativeUncertainty(unittest.TestCase):

    def test_combinacao_valida(self):
        dados = {'mensurando': [{'label': 'rstdc', 'unc_relativa': True,
                                 'relative_uncertainty_in_dcc': True}]}
        validate_relative_uncertainty(dados)

    def test_sem_bloco_relativo(self):
        dados = {'mensurando': [{'label': 'rstdc', 'unc_relativa': False,
                                 'relative_uncertainty_in_dcc': False}]}
        validate_relative_uncertainty(dados)

    def test_bloco_relativo_sem_unc_relativa(self):
        dados = {'mensurando': [{'label': 'rstdc', 'unc_relativa': False,
                                 'relative_uncertainty_in_dcc': True}]}
        with self.assertRaises(ValueError):
            validate_relative_uncertainty(dados)

    def test_aceita_string_sim(self):
        dados = {'mensurando': [{'label': 'rstdc', 'unc_relativa': 'Sim',
                                 'relative_uncertainty_in_dcc': 'Sim'}]}
        validate_relative_uncertainty(dados)


class TestResolveUncertaintyNorm(unittest.TestCase):

    def test_ausente_retorna_lista_vazia(self):
        self.assertEqual(resolve_uncertainty_norm({}), [])
        self.assertEqual(resolve_uncertainty_norm({'declaracao_incerteza_norm': ''}), [])

    def test_texto_unico(self):
        self.assertEqual(
            resolve_uncertainty_norm({'declaracao_incerteza_norm': ' JCGM 100:2008 '}),
            ['JCGM 100:2008'],
        )

    def test_lista_preserva_ordem(self):
        self.assertEqual(
            resolve_uncertainty_norm({
                'declaracao_incerteza_norm': ['JCGM 100:2008', 'ISO/IEC Guide 98-3:2008'],
            }),
            ['JCGM 100:2008', 'ISO/IEC Guide 98-3:2008'],
        )

    def test_lista_ignora_vazios(self):
        self.assertEqual(
            resolve_uncertainty_norm({
                'declaracao_incerteza_norm': ['', '  ', 'JCGM 100:2008'],
            }),
            ['JCGM 100:2008'],
        )

    def test_tipo_invalido_gera_erro(self):
        with self.assertRaises(ValueError):
            resolve_uncertainty_norm({'declaracao_incerteza_norm': 2008})

    def test_lista_com_tipo_invalido_gera_erro(self):
        with self.assertRaises(ValueError):
            resolve_uncertainty_norm({'declaracao_incerteza_norm': ['JCGM 100:2008', 2008]})


class TestGeracaoUncertaintyNorm(unittest.TestCase):

    def test_sem_norm_nao_emite_dcc_norm(self):
        root = etree.fromstring(gerar(carregar()))
        method = used_method_incerteza(root)

        self.assertIsNotNone(method)
        self.assertEqual(method.findall(DCC_NS + 'norm'), [])

    def test_norm_texto_emite_dcc_norm(self):
        dados = carregar()
        dados['declaracao_incerteza_norm'] = 'JCGM 100:2008'

        root = etree.fromstring(gerar(dados))
        method = used_method_incerteza(root)
        normas = method.findall(DCC_NS + 'norm')

        self.assertEqual(len(normas), 1)
        self.assertEqual(normas[0].text, 'JCGM 100:2008')
        self.assertEqual(
            [etree.QName(filho).localname for filho in method],
            ['name', 'description', 'norm'],
        )

    def test_norm_lista_emite_multiplos_na_ordem(self):
        dados = carregar()
        dados['declaracao_incerteza_norm'] = [
            'JCGM 100:2008',
            'ISO/IEC Guide 98-3:2008',
        ]

        root = etree.fromstring(gerar(dados))
        method = used_method_incerteza(root)
        normas = [norma.text for norma in method.findall(DCC_NS + 'norm')]

        self.assertEqual(
            normas,
            ['JCGM 100:2008', 'ISO/IEC Guide 98-3:2008'],
        )


class TestRotaGenerateUncertaintyNorm(unittest.TestCase):

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
            'username': 'uncertainty_norm_user',
            'password': 'senha12345',
            'email': 'uncertainty_norm_user@inmetro.gov.br',
        })
        self.assertEqual(resp.status_code, 201)
        return resp.get_json()['api_key']

    def test_norm_invalido_retorna_400(self):
        dados = carregar()
        dados['declaracao_incerteza_norm'] = 2008

        resp = self.client.post(
            '/dcc/generate', json=dados,
            headers={'X-API-Key': self._api_key()})

        self.assertEqual(resp.status_code, 400)
        self.assertIn('declaracao_incerteza_norm', resp.get_json()['error'])

    def test_norm_valido_retorna_200(self):
        dados = carregar()
        dados['declaracao_incerteza_norm'] = 'JCGM 100:2008'

        resp = self.client.post(
            '/dcc/generate', json=dados,
            headers={'X-API-Key': self._api_key()})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'text/xml')
        root = etree.fromstring(resp.data)
        method = used_method_incerteza(root)
        self.assertEqual(
            method.findtext(DCC_NS + 'norm'), 'JCGM 100:2008')


if __name__ == '__main__':
    unittest.main()

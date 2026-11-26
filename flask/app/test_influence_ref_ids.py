## Inmetro/Dimci/Diele/Lampe
# Testes do vinculo entre condicoes de influencia (id) e resultados (refId).
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
_TMP_DB = os.path.join(
    tempfile.mkdtemp(prefix='dcc_ref_id_test_'), 'dcc_auth.db')
os.environ.setdefault('DCC_DB_PATH', _TMP_DB)
os.environ.setdefault('DCC_SECRET_KEY', 'secret-test-key')
os.environ.setdefault('DCC_EMAIL_ENABLED', 'false')

from lxml import etree  # noqa: E402

import auth  # noqa: E402
from main import (  # noqa: E402
    declaracoes,
    dccGen,
    resolve_dcc_version,
)

DCC_NS = '{https://ptb.de/dcc}'
SI_NS = '{https://ptb.de/si}'
EXEMPLO_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'examples',
    'dcc_json.json',
)


def carregar():
    with open(EXEMPLO_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def preprocessar(dados):
    dados = copy.deepcopy(dados)
    if 'desc_chefe_div' in dados:
        dados['desc_chefe_div'] = (
            dados['desc_chefe_div'] + ' da ' + dados['nome_div'])
    else:
        dados['desc_chefe_div'] = 'Chefe da ' + dados['nome_div']

    if 'desc_chefe_lab' in dados:
        dados['desc_chefe_lab'] = (
            dados['desc_chefe_lab'] + ' do ' + dados['nome_lab'])
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


def quantidade_resultado(result, col_name):
    for quantity in result.iter(DCC_NS + 'quantity'):
        nome = quantity.findtext(
            DCC_NS + 'name/' + DCC_NS + 'content')
        if nome == col_name:
            return quantity
    return None


def metadados_ref(quantity):
    refs = []
    for meta in quantity.iter(DCC_NS + 'metaData'):
        if meta.get('refId'):
            refs.append(meta.get('refId'))
    return refs


def valores_resultado(quantity):
    texto = quantity.findtext(
        SI_NS + 'realListXMLList/' + SI_NS + 'valueXMLList')
    return texto.split() if texto else []


class TestSemRefIds(unittest.TestCase):

    def test_payload_antigo_nao_muda(self):
        root = arvore(gerar(carregar()))
        resultados = list(root.iter(DCC_NS + 'result'))
        self.assertEqual(len(resultados), 2)

        for result in resultados:
            for quantity in result.iter(DCC_NS + 'quantity'):
                self.assertEqual(metadados_ref(quantity), [])


class TestIdCondicao(unittest.TestCase):

    def test_id_em_informacao_pertinente(self):
        dados = carregar()
        dados['informacoes_pertinentes'][0]['id'] = 'iC_temp'

        root = arvore(gerar(dados))
        condicoes = list(root.iter(DCC_NS + 'influenceCondition'))
        temperatura = [
            c for c in condicoes
            if c.findtext(
                DCC_NS + 'name/' + DCC_NS + 'content') == 'Temperatura'
        ]
        self.assertEqual(len(temperatura), 1)
        self.assertEqual(temperatura[0].get('id'), 'iC_temp')

    def test_id_invalido_gera_erro(self):
        dados = carregar()
        dados['informacoes_pertinentes'][0]['id'] = 'id com espaço'
        with self.assertRaises(ValueError):
            gerar(dados)

    def test_id_duplicado_gera_erro(self):
        dados = carregar()
        dados['informacoes_pertinentes'][0]['id'] = 'iC_temp'
        dados['informacoes_pertinentes'][1]['id'] = 'iC_temp'
        with self.assertRaises(ValueError):
            gerar(dados)

    def test_id_conflita_com_cmc_gera_erro(self):
        dados = carregar()
        dados['cmc_padrao'] = True
        dados['informacoes_pertinentes'][0]['id'] = 'inCMC'
        with self.assertRaises(ValueError):
            gerar(dados)


class TestRefIdResultado(unittest.TestCase):

    def _dados_com_grupos(self):
        dados = carregar()
        dados['informacoes_pertinentes'][0]['id'] = 'iC_temp_20'
        dados['informacoes_pertinentes'].append({
            'id': 'iC_temp_23',
            'name': 'Temperatura 23',
            'value': '23.0',
            'unc': '0.1',
            'unit': '\\degreecelsius'
        })

        vistos_acdc = 0
        for resultado in dados['resultados']:
            if resultado['mensurando'] == 'rstdc':
                resultado['refId'] = 'iC_temp_20'
            elif resultado['mensurando'] == 'acdc':
                vistos_acdc += 1
                resultado['refId'] = (
                    'iC_temp_20' if vistos_acdc <= 2 else 'iC_temp_23')

        return dados

    def test_refid_agrupa_resultados_por_condicao(self):
        root = arvore(gerar(self._dados_com_grupos()))
        resultados = list(root.iter(DCC_NS + 'result'))

        # 1 grupo rstdc + 2 grupos acdc (20 e 23)
        self.assertEqual(len(resultados), 3)

        grupos = {}
        for result in resultados:
            col_name = None
            for candidato in ('V.m.', '\\delta_u'):
                quantity = quantidade_resultado(result, candidato)
                if quantity is not None:
                    col_name = candidato
                    break
            self.assertIsNotNone(col_name)
            refs = metadados_ref(quantity)
            self.assertEqual(len(refs), 1)
            grupos[(col_name, refs[0])] = valores_resultado(quantity)

        self.assertEqual(grupos[('V.m.', 'iC_temp_20')], ['1.0002341'])
        self.assertEqual(
            grupos[('\\delta_u', 'iC_temp_20')], ['-280', '3'])
        self.assertEqual(
            len(grupos[('\\delta_u', 'iC_temp_23')]),
            len([r for r in self._dados_com_grupos()['resultados']
                 if r['mensurando'] == 'acdc']) - 2)

    def test_refid_em_lista(self):
        dados = carregar()
        dados['informacoes_pertinentes'][0]['id'] = 'iC_temp'
        dados['informacoes_pertinentes'][1]['id'] = 'iC_hum'
        dados['resultados'][0]['refId'] = ['iC_temp', 'iC_hum']

        root = arvore(gerar(dados))
        for result in root.iter(DCC_NS + 'result'):
            quantity = quantidade_resultado(result, 'V.m.')
            if quantity is not None:
                self.assertEqual(
                    metadados_ref(quantity), ['iC_temp iC_hum'])
                return
        self.fail('resultado rstdc não encontrado')

    def test_refid_desconhecido_gera_erro(self):
        dados = carregar()
        dados['informacoes_pertinentes'][0]['id'] = 'iC_temp'
        dados['resultados'][0]['refId'] = 'iC_inexistente'
        with self.assertRaises(ValueError):
            gerar(dados)

    def test_refid_sem_ids_gera_erro(self):
        dados = carregar()
        dados['resultados'][0]['refId'] = 'iC_temp'
        with self.assertRaises(ValueError):
            gerar(dados)

    def test_refid_tipo_invalido_gera_erro(self):
        dados = carregar()
        dados['informacoes_pertinentes'][0]['id'] = 'iC_temp'
        dados['resultados'][0]['refId'] = 123
        with self.assertRaises(ValueError):
            gerar(dados)

    def test_cmc_e_refid_compartilham_measurement_metadata(self):
        dados = carregar()
        dados['cmc_padrao'] = True
        dados['informacoes_pertinentes'][0]['id'] = 'iC_temp'
        for resultado in dados['resultados']:
            resultado['refId'] = 'iC_temp'

        root = arvore(gerar(dados))
        for result in root.iter(DCC_NS + 'result'):
            quantity = quantidade_resultado(result, 'V.m.')
            if quantity is None:
                continue

            measurement_metadata = quantity.find(
                DCC_NS + 'measurementMetaData')
            self.assertIsNotNone(measurement_metadata)
            meta_data = list(measurement_metadata.findall(
                DCC_NS + 'metaData'))
            self.assertEqual(len(meta_data), 2)
            self.assertEqual(meta_data[0].get('refId'), 'inCMC')
            self.assertEqual(meta_data[1].get('refId'), 'iC_temp')
            return

        self.fail('resultado rstdc não encontrado')


if __name__ == '__main__':
    unittest.main()

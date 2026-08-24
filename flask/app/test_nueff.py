## Inmetro/Dimci/Diele/Lampe
# Testes automatizados para o suporte aos graus de liberdade efetivos (nueff)
# no gerador DCC (dccGenerator).

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
import unittest

from lxml import etree

from main import (
    dccGen,
    declaracoes,
    resolve_dcc_version,
    validate_nueff,
)

DCC_NS = '{https://ptb.de/dcc}'
SI_NS = '{https://ptb.de/si}'

EXEMPLO_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'static',
    'examples',
    'dcc_json.json',
)


def base_dados():
    with open(EXEMPLO_JSON, 'r', encoding='utf-8') as f:
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


def encontrar_quantidade_nueff(xml_bytes):
    tree = etree.fromstring(xml_bytes)
    quantidades = []
    for q in tree.iter(DCC_NS + 'quantity'):
        name = q.find(DCC_NS + 'name')
        if name is not None:
            for content in name.findall(DCC_NS + 'content'):
                if content.text and 'liberdade' in content.text.lower():
                    quantidades.append(q)
    return quantidades


class TestValidateNueff(unittest.TestCase):

    def test_valores_validos_fracionarios(self):
        self.assertTrue(validate_nueff([10.5, 20.3, 35.7], 3))

    def test_valores_nao_inteiros_preservados(self):
        self.assertTrue(validate_nueff(['12.7'], 1))

    def test_comprimento_incompativel(self):
        with self.assertRaises(ValueError):
            validate_nueff([10.5, 20.3], 3)

    def test_nao_e_lista(self):
        with self.assertRaises(ValueError):
            validate_nueff('10.5', 1)

    def test_valor_nulo(self):
        with self.assertRaises(ValueError):
            validate_nueff([None], 1)

    def test_valor_vazio(self):
        with self.assertRaises(ValueError):
            validate_nueff([''], 1)

    def test_valor_espacos(self):
        with self.assertRaises(ValueError):
            validate_nueff(['   '], 1)

    def test_valor_nan(self):
        with self.assertRaises(ValueError):
            validate_nueff([float('nan')], 1)

    def test_valor_infinito(self):
        with self.assertRaises(ValueError):
            validate_nueff([float('inf')], 1)

    def test_valor_negativo(self):
        with self.assertRaises(ValueError):
            validate_nueff([-1], 1)

    def test_valor_zero(self):
        with self.assertRaises(ValueError):
            validate_nueff([0], 1)

    def test_valor_nao_numerico(self):
        with self.assertRaises(ValueError):
            validate_nueff(['abc'], 1)


class TestNueffGeneration(unittest.TestCase):

    def test_nueff_presente_gera_quantidade(self):
        dados = base_dados()
        n = sum(1 for r in dados['resultados'] if r['mensurando'] == 'acdc')
        valores = [str(round(10.0 + i * 1.3, 2)) for i in range(n)]
        i = 0
        for r in dados['resultados']:
            if r['mensurando'] == 'acdc':
                r['nueff'] = valores[i]
                i += 1

        xml = gerar(dados)
        quantidades = encontrar_quantidade_nueff(xml)

        self.assertEqual(len(quantidades), 1)

        q = quantidades[0]
        real_list = q.find(SI_NS + 'realListXMLList')
        self.assertIsNotNone(real_list)

        value = real_list.find(SI_NS + 'valueXMLList')
        unit = real_list.find(SI_NS + 'unitXMLList')
        self.assertIsNotNone(value)
        self.assertIsNotNone(unit)

        self.assertEqual(unit.text, '\\one')
        self.assertEqual(value.text.split(), valores)

    def test_nueff_ausente_nao_gera_quantidade(self):
        dados = base_dados()
        xml = gerar(dados)
        self.assertEqual(encontrar_quantidade_nueff(xml), [])

    def test_nueff_comprimento_incompativel_gera_erro(self):
        dados = base_dados()
        for r in dados['resultados']:
            if r['mensurando'] == 'acdc':
                r['nueff'] = '10.5'
                break
        with self.assertRaises(ValueError):
            gerar(dados)

    def test_nueff_valor_invalido_gera_erro(self):
        for valor_invalido in ['0', '-1', 'abc']:
            dados = base_dados()
            dados['resultados'] = [r for r in dados['resultados'] if r['mensurando'] == 'acdc'][:2]
            for r in dados['resultados']:
                r['nueff'] = '10.5'
            dados['resultados'][1]['nueff'] = valor_invalido
            with self.assertRaises(ValueError):
                gerar(dados)

    def test_incerteza_expandida_inalterada(self):
        dados = base_dados()
        n = sum(1 for r in dados['resultados'] if r['mensurando'] == 'acdc')
        i = 0
        for r in dados['resultados']:
            if r['mensurando'] == 'acdc':
                r['nueff'] = '12.7'
                i += 1

        xml = gerar(dados)
        tree = etree.fromstring(xml)

        uncertainty = list(tree.iter(SI_NS + 'uncertaintyXMLList'))
        coverage_factor = list(tree.iter(SI_NS + 'coverageFactorXMLList'))
        coverage_probability = list(tree.iter(SI_NS + 'coverageProbabilityXMLList'))

        self.assertTrue(uncertainty)
        self.assertTrue(coverage_factor)
        self.assertTrue(coverage_probability)
        self.assertEqual(coverage_probability[0].text, '0.9545')


if __name__ == '__main__':
    unittest.main()

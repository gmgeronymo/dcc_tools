## Inmetro/Dimci/Diele/Lampe
# Testes automatizados da visualizacao human-readable (XSLT) do DCC.
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
import io
import json
import os
import tempfile
import unittest

# Configura um banco isolado ANTES de importar a app.
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix='dcc_visualizacao_test_'), 'dcc_auth.db')
os.environ.setdefault('DCC_DB_PATH', _TMP_DB)
os.environ.setdefault('DCC_SECRET_KEY', 'secret-test-key')
os.environ.setdefault('DCC_EMAIL_ENABLED', 'false')

from lxml import etree  # noqa: E402

from main import app, dccGen, declaracoes, resolve_dcc_version  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_DIR = os.path.join(BASE_DIR, 'static', 'examples')
XSLT_PATH = os.path.join(EXAMPLES_DIR, 'xslt', 'hr_template.xsl')

EXEMPLO_JSON = os.path.join(EXAMPLES_DIR, 'dcc_json.json')
EXEMPLO_PONTO_UNICO = os.path.join(EXAMPLES_DIR, 'CC_DIMCI_0496_2025.json')
EXEMPLO_LEGADO_XML = os.path.join(EXAMPLES_DIR, 'CC_DIMCI_0515_2025.XML')


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


def gerar_xml(dados):
    dados = preprocessar(dados)
    declaracao = declaracoes(dados)
    versao = resolve_dcc_version(dados)
    return dccGen(versao, dados, declaracao)


def transformar(xml_bytes):
    xml_doc = etree.fromstring(xml_bytes)
    xslt_doc = etree.parse(XSLT_PATH)
    return str(etree.XSLT(xslt_doc)(xml_doc))


class TestCapaVisualizacao(unittest.TestCase):

    def test_capa_usa_estrutura_do_modelo_html(self):
        html = transformar(gerar_xml(carregar(EXEMPLO_JSON)))

        # estrutura da folha de rosto
        self.assertIn('pagina-rosto-container', html)
        self.assertIn('secao-quadro', html)
        self.assertIn('Certificado de Calibração', html)
        self.assertIn('Número do Certificado', html)
        self.assertIn('Informações Administrativas', html)
        self.assertIn('logo_inmetro.png', html)
        # cmc=true no exemplo: logo do CIPM MRA na capa
        self.assertIn('logo_mra.png', html)

    def test_capa_sem_cmc_nao_exibe_logo_mra(self):
        dados = carregar(EXEMPLO_JSON)
        dados['cmc'] = False
        html = transformar(gerar_xml(dados))

        self.assertNotIn('logo_mra.png', html)


class TestMarcacaoCmcVisualizacao(unittest.TestCase):

    def test_lista_mista_exibe_coluna_e_observacao(self):
        dados = carregar(EXEMPLO_JSON)
        dados['cmc'] = True
        resultados = dados['resultados']
        for i, resultado in enumerate(resultados):
            resultado['in_cmc'] = (i < 2)

        html = transformar(gerar_xml(dados))

        self.assertIn('<th>CMC</th>', html)
        self.assertIn('>Sim</td>', html)
        self.assertIn('>Não</td>', html)
        # as duas observações do exemplo vêm antes da observação da CMC
        self.assertIn('Obs. 3: ', html)
        self.assertIn(
            'Os pontos marcados com Não na coluna CMC não estão cobertos pela '
            'Capacidade de Medição e Calibração (CMC) do laboratório no âmbito do CIPM MRA, '
            'embora a rastreabilidade esteja garantida da mesma forma que sustenta a dos demais pontos.',
            html,
        )

    def test_ponto_unico_fora_usa_singular(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['cmc'] = True
        for resultado in dados['resultados']:
            resultado['in_cmc'] = False

        html = transformar(gerar_xml(dados))

        self.assertIn('>Não</td>', html)
        # o exemplo de ponto único não tem observações: a observação da CMC é a Obs. 1
        self.assertIn('Obs. 1: ', html)
        self.assertIn(
            'O ponto marcado com Não na coluna CMC não está coberto pela '
            'Capacidade de Medição e Calibração (CMC) do laboratório no âmbito do CIPM MRA, '
            'embora a rastreabilidade esteja garantida da mesma forma que sustenta a dos demais pontos.',
            html,
        )

    def test_todos_dentro_nao_gera_observacao(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        dados['cmc'] = True
        for resultado in dados['resultados']:
            resultado['in_cmc'] = True

        html = transformar(gerar_xml(dados))

        self.assertIn('>Sim</td>', html)
        self.assertNotIn('marcados com Não na coluna CMC', html)

    def test_sem_marcacao_nao_exibe_coluna_nem_observacao(self):
        dados = carregar(EXEMPLO_JSON)
        dados['cmc'] = False
        html = transformar(gerar_xml(dados))

        self.assertNotIn('<th>CMC</th>', html)
        self.assertNotIn('marcados com Não na coluna CMC', html)

    def test_nueff_infinito_exibe_simbolo(self):
        dados = carregar(EXEMPLO_PONTO_UNICO)
        for resultado in dados['resultados']:
            resultado['nueff'] = 'inf'

        html = transformar(gerar_xml(dados))

        self.assertIn('∞', html)
        self.assertNotIn('<td>inf</td>', html)


class TestCompatibilidadeVisualizacao(unittest.TestCase):

    def test_certificado_legado_3_2_0_continua_transformando(self):
        with open(EXEMPLO_LEGADO_XML, 'rb') as f:
            xml_bytes = f.read()

        html = transformar(xml_bytes)

        self.assertIn('Certificado de Calibração', html)
        self.assertIn('pagina-rosto-container', html)
        self.assertNotIn('<th>CMC</th>', html)


class TestRotaVisualizacao(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_extensao_invalida_retorna_400(self):
        response = self.client.post(
            '/dcc/visualizar_dcc',
            data={'xml_file': (io.BytesIO(b'{}'), 'dcc.json')},
            content_type='multipart/form-data',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()['error'],
            'Somente arquivos XML são aceitos.',
        )


if __name__ == '__main__':
    unittest.main()

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

import unittest

from main import resolve_dcc_version, validate_relative_uncertainty


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


if __name__ == '__main__':
    unittest.main()

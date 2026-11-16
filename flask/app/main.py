## Inmetro/Dimci/Diele/Lampe
# Simple DCC Generator python microservice
# DCC compliant with ptb.de/dcc

# Author: Gean Marcos Geronymo

# This file is part of Inmetro DCC Tools.
#
# Inmetro DCC Tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Your Project is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Inmetro DCC Tools. If not, see <http://www.gnu.org/licenses/>.

# dados do programa
# parametros do programa
__version__ = '2.1'
__date__="12/11/2026"
__appname__="dccGenerator"
__author__="Gean Marcos Geronymo"
__author_email__="gmgeronymo@inmetro.gov.br"

# versao 1.1 (16/10/2025)
# refType nao eh mais adicionado por padrao
# solucao temporaria enquanto ontologia brasileira nao for desenvolvida

# bibliotecas
import json
from lxml import etree
from flask import Flask, jsonify, request, abort, Response, send_file, render_template, redirect, session, url_for, g
import requests
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import re
import tempfile
import shutil
import secrets
import ipaddress
from datetime import timedelta
from urllib.parse import urlparse, urljoin


# autenticacao (cadastro de usuarios / API-KEY)
import auth

# envio de e-mail (recuperacao de senha)
import email_service

# PDF attach
import pikepdf
from pikepdf import Pdf, Name, String, Array
import os
import hashlib
import tempfile

# excel2json
import pandas as pd

import math

# namespaces
nsmap = {'xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'dcc': 'https://ptb.de/dcc', 'si': 'https://ptb.de/si'}
# schema
schemaLocation = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")

DEFAULT_DCC_VERSION = '3.3.0'
SUPPORTED_DCC_VERSIONS = {
    '3.3.0': 'https://www.ptb.de/dcc/v3.3.0/dcc.xsd',
}

# URL base oficial do servico (usada, p.ex., no link de recuperacao de senha).
# Pode ser sobrescrita pela variavel de ambiente APP_BASE_URL.
DEFAULT_APP_BASE_URL = 'https://sig-dimci.inmetro.gov.br'

app = Flask(__name__, static_url_path='/dcc/static')
app.debug = True

# App is behind one proxy that sets the -For and -Host headers.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1)

# chave de assinatura das sessoes da interface web
# em producao definir DCC_SECRET_KEY; caso contrario uma chave efemera eh gerada
_secret_key = os.environ.get('DCC_SECRET_KEY')
if not _secret_key:
    app.logger.warning(
        'DCC_SECRET_KEY nao definida: usando chave efemera. Em producao defina '
        'DCC_SECRET_KEY (ex.: arquivo flask/.env) para que as sessoes da interface '
        'web sejam persistentes e consistentes entre workers.'
    )
app.secret_key = _secret_key or secrets.token_hex(32)

# duracao da sessao da interface web (padrao: 8 horas)
app.permanent_session_lifetime = timedelta(hours=int(os.environ.get('DCC_SESSION_HOURS', '8')))

# cria as tabelas de autenticacao (idempotente)
auth.init_db()

# funcoes auxiliares

def format_two_sig_scientific(number):
    if number == 0:
        return "0.0e0"
    
    # Calculate exponent
    exponent = math.floor(math.log10(abs(number)))
    
    # Calculate mantissa with 2 significant digits
    mantissa = number / (10 ** exponent)
    mantissa = round(mantissa, 1)  # Round to 1 decimal for 2 sig figs
    
    # Adjust if rounding makes mantissa >= 10
    if mantissa >= 10:
        mantissa /= 10
        exponent += 1
    
    return f"{mantissa:.1f}e{exponent}"

# gerar human readable a partir do xml
def transform_xml_to_html(xml_content, xslt_path):
    """Transform XML to HTML using XSLT"""
    try:
        # Use bytes input instead of decoded string
        if isinstance(xml_content, str):
            xml_content = xml_content.encode('utf-8')
        
        # Parse the XML content from bytes
        xml_doc = etree.fromstring(xml_content)
        
        # Parse the XSLT stylesheet
        xslt_doc = etree.parse(xslt_path)
        transformer = etree.XSLT(xslt_doc)
        
        # Transform XML to HTML
        result_html = transformer(xml_doc)
        
        return str(result_html), None
    except etree.XMLSyntaxError as e:
        return None, f"Erro de sintaxe XML: {e}"
    except etree.XSLTParseError as e:
        return None, f"Erro de análise XSLT: {e}"
    except etree.XSLTApplyError as e:
        return None, f"Erro de aplicação XSLT: {e}"
    except Exception as e:
        return None, f"Erro inesperado: {e}"

def allowed_file(filename,allowed_extensions) :
    return '.' in filename and filename.rsplit('.',1)[1].lower() in allowed_extensions

def sha256sum(filename):
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


TRACEABILITY_SHA256_RE = re.compile(r'^[0-9a-fA-F]{64}$')
TRACEABILITY_HASH_PROCEDURE_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
TRACEABILITY_DEFAULT_HASH_PROCEDURE = 'sha256'


def resolve_traceability_hash(rastreabilidade):
    """Resolve os campos procedure/value do certificado de rastreabilidade.

    Quando 'hash_sha256' e informado, o certificado do padrao e um DCC e e
    identificado pelo SHA-256 do seu arquivo XML. O campo opcional
    'hash_procedure' permite registrar a transformacao usada antes do hash
    (ex.: c14n-sha256 ou enveloped-c14n-sha256), conforme o DCC/PTB. Sem ele,
    usa 'sha256', que corresponde ao hash do arquivo inteiro.

    Caso contrario, usa 'analogue'/'analogue', conforme o vocabulario do
    DCC para certificados analogicos.
    """
    hash_sha256 = rastreabilidade.get('hash_sha256')
    if hash_sha256 is None or str(hash_sha256).strip() == '':
        return 'analogue', 'analogue'

    hash_sha256 = str(hash_sha256).strip()
    if not TRACEABILITY_SHA256_RE.match(hash_sha256):
        raise ValueError(
            "Valor inválido para 'tabela_rastreabilidade[].hash_sha256': %r. "
            "Informe o hash SHA-256 em hexadecimal com 64 caracteres."
            % (hash_sha256,)
        )

    procedure = rastreabilidade.get('hash_procedure')
    if procedure is None or str(procedure).strip() == '':
        procedure = TRACEABILITY_DEFAULT_HASH_PROCEDURE
    else:
        procedure = str(procedure).strip()
        if not TRACEABILITY_HASH_PROCEDURE_RE.match(procedure):
            raise ValueError(
                "Valor inválido para 'tabela_rastreabilidade[].hash_procedure': "
                "%r. Use apenas letras, números, ponto, hífen ou sublinhado."
                % (procedure,)
            )

    return procedure, hash_sha256.lower()

## funcoes DCC

## texto das declaracoes do certificado de calibracao
def declaracoes(dados) :
    declaracao = {
        'cmc' : 'Este certificado é consistente com as Capacidades de Medição e Calibração (CMCs) que estão incluídas no apêndice C do Acordo de Reconhecimento Mútuo (MRA) estabelecido pelo Comitê Internacional de Pesos e Medidas (CIPM). Conforme os termos do MRA, todos os institutos participantes reconhecem entre si a validade dos seus certificados de calibração e medição para cada uma das grandezas, faixas e incertezas de medição declaradas no Apêndice C (para maiores detalhes ver http://www.bipm.org).',
        'norma' : 'ABNT NBR ISO/IEC 17025',
        'requisitos' : 'O presente certificado de calibração atende aos requisitos da norma ABNT NBR ISO/IEC 17025 e é válido apenas para o item acima caracterizado, não sendo extensivo a quaisquer outros. Este certificado de calibração somente pode ser reproduzido em sua forma integral. Reproduções parciais devem ser previamente autorizadas pelo Inmetro.',
        'incerteza' : dados['declaracao_incerteza'],
        'metodo_medicao' : dados['metodo_medicao'],
        'rastreabilidade' : dados['declaracao_rastreabilidade']
    }
    
    return declaracao


def resolve_dcc_version(dados):
    """
    Resolve a versao do schema DCC.

    Chaves opcionais:
    - dcc_version
    - schema_version

    Se nao informada, usa DEFAULT_DCC_VERSION. Apenas versoes em
    SUPPORTED_DCC_VERSIONS sao aceitas; versoes antigas ou desconhecidas
    geram ValueError (a API responde 400).
    """
    requested_version = dados.get('dcc_version') or dados.get('schema_version') or DEFAULT_DCC_VERSION
    if requested_version in SUPPORTED_DCC_VERSIONS:
        return requested_version
    if requested_version == '3.2.0':
        raise ValueError(
            "O schema DCC 3.2.0 não é mais suportado para geração. "
            "Use dcc_version='3.3.0'."
        )
    raise ValueError(
        "Versão de schema não suportada: %r. Versão suportada: 3.3.0."
        % (requested_version,)
    )


def is_truthy(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {'true', '1', 'yes', 'sim', 'y'}


# ---------------------------------------------------------------------------
# Marcacao de pontos dentro/fora da CMC (basic_isInCMC)
#
# O schema DCC 3.3.0 nao possui campo nativo de CMC. A marcacao e feita com:
#   1) dcc:statement id=... refType="basic_isInCMC" em administrativeData;
#   2) dcc:measurementMetaData/dcc:metaData refId=... na dcc:quantity resultante;
#   3) dcc:valid (ponto unico) ou dcc:validXMLList (um booleano por ponto).
#
# O statement reaproveita a declaracao de CMC existente (cmc=True), sem criar
# um segundo statement. A entrada JSON usa:
#   - resultados[].in_cmc  (opcional): true/false por ponto;
#   - cmc_padrao           (opcional): valor aplicado aos pontos sem in_cmc;
#   - cmc_declaracao       (opcional): personaliza id, textos e autoridade.
# ---------------------------------------------------------------------------

CMC_REF_TYPE = 'basic_isInCMC'
CMC_ID_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9._-]*$')

# CMC IDs do KCDB (BIPM). O identificador base segue RMO-Area-Pais-ID; o
# sufixo "-X" (digito) e a versao da CMC e nao e usado no XML nem no link.
KCDB_CMC_BASE_URL = 'https://si-digital-framework.org/kcdb-cmc/'
KCDB_CMC_ID_PATTERN = re.compile(r'^[A-Z]{2,10}-[A-Z]{1,5}-[A-Z]{2,4}-[A-Z0-9]{8}$')
KCDB_CMC_VERSION_SUFFIX = re.compile(r'-\d$')

CMC_STATEMENT_DEFAULTS = {
    'id': 'inCMC',
    'nome': 'CIPM-MRA',
    'referencia': 'CIPM-MRA — Apêndice C / KCDB',
    'link': 'https://www.bipm.org/kcdb/',
    'descricao': (
        'Todos os resultados são acompanhados por um elemento dcc:valid '
        '(ou dcc:validXMLList) com refId para este dcc:statement. O valor '
        '"true" indica que (a) o resultado está dentro do escopo coberto '
        'pela CMC e (b) a incerteza declarada é maior ou igual à incerteza '
        'da CMC.'
    ),
    'autoridade': {
        'nome': 'BIPM',
        'cidade': 'Paris',
        'pais': 'FR',
    },
}

CMC_BOOL_TRUE = {'true', '1', 'yes', 'sim', 'y', 's', 't'}
CMC_BOOL_FALSE = {'false', '0', 'no', 'nao', 'não', 'n', 'f'}


def parse_bool(value, campo):
    """Converte um valor booleano (bool, 0/1 ou texto) em bool.

    Aceita true/false, 1/0, yes/no, sim/não. Valores ambíguos ou vazios
    geram ValueError para evitar que um erro de digitacao seja
    silenciosamente interpretado como "fora da CMC".
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        if value == 0:
            return False
        if value == 1:
            return True

    if isinstance(value, str):
        texto = value.strip().lower()
        if texto in CMC_BOOL_TRUE:
            return True
        if texto in CMC_BOOL_FALSE:
            return False

    raise ValueError(
        "Valor inválido para '%s': %r. Use true/false (ou Sim/Não)."
        % (campo, value)
    )


def optional_bool(mapping, key, default):
    """Le um booleano opcional e informa se a chave foi explicitada."""
    if not isinstance(mapping, dict) or key not in mapping:
        return default, False

    value = mapping[key]
    if value is None or (isinstance(value, str) and not value.strip()):
        return default, False

    return parse_bool(value, key), True


def normalize_kcdb_cmc_id(value):
    """Normaliza um CMC ID do KCDB para o identificador base.

    O sufixo "-X" (digito) indica a versao da CMC e e removido, conforme o
    uso no certificado e no link permanente do BIPM. O identificador e
    normalizado para maiusculas.
    """
    original = value
    cmc_id = str(value).strip().upper()
    cmc_id = KCDB_CMC_VERSION_SUFFIX.sub('', cmc_id)

    if not KCDB_CMC_ID_PATTERN.match(cmc_id):
        raise ValueError(
            "CMC ID inválido em 'cmc_declaracao': %r. Use o formato "
            "RMO-Área-País-ID (o sufixo de versão -X é opcional)."
            % (original,)
        )

    return cmc_id


def resolve_cmc_ids(declaracao):
    """Le e normaliza o(s) CMC ID(s) informados em cmc_declaracao.cmc_id.

    Aceita um texto unico ou uma lista de textos; remove duplicidades
    preservando a ordem.
    """
    if not isinstance(declaracao, dict):
        return []

    if 'cmc_ids' in declaracao:
        raise ValueError(
            "Use 'cmc_declaracao.cmc_id' (texto ou lista) em vez de 'cmc_ids'."
        )

    bruto = declaracao.get('cmc_id')

    if bruto is None:
        return []

    if isinstance(bruto, str):
        valores = [bruto]
    elif isinstance(bruto, (list, tuple)):
        valores = list(bruto)
    else:
        raise ValueError(
            "O campo 'cmc_declaracao.cmc_id' deve ser um texto ou uma lista "
            "de textos."
        )

    ids = []
    vistos = set()

    for valor in valores:
        if valor is None or str(valor).strip() == '':
            continue
        if isinstance(valor, (list, tuple, dict)):
            raise ValueError(
                "Cada item de 'cmc_declaracao.cmc_id' deve ser um texto."
            )
        cmc_id = normalize_kcdb_cmc_id(valor)
        if cmc_id not in vistos:
            vistos.add(cmc_id)
            ids.append(cmc_id)

    return ids


def resolve_cmc_config(dados):
    """Valida e resolve a configuracao da marcacao de CMC.

    O statement de CMC e emitido quando cmc=True ou quando o usuario
    informa pelo menos um 'resultados[].in_cmc' ou o campo 'cmc_padrao'.
    Os vinculos por ponto (measurementMetaData) so sao gerados nos dois
    ultimos casos; sem eles, o statement permanece apenas declarativo.
    """
    resultados = dados.get('resultados', []) or []
    explicito = False

    for resultado in resultados:
        if not isinstance(resultado, dict):
            continue
        _, tem_in_cmc = optional_bool(resultado, 'in_cmc', False)
        explicito = explicito or tem_in_cmc

    cmc_padrao, tem_padrao = optional_bool(dados, 'cmc_padrao', False)

    config = {
        'id': CMC_STATEMENT_DEFAULTS['id'],
        'nome': CMC_STATEMENT_DEFAULTS['nome'],
        'referencia': CMC_STATEMENT_DEFAULTS['referencia'],
        'link': CMC_STATEMENT_DEFAULTS['link'],
        'descricao': CMC_STATEMENT_DEFAULTS['descricao'],
        'autoridade': dict(CMC_STATEMENT_DEFAULTS['autoridade']),
        'enabled': explicito or tem_padrao,
        'statement': is_truthy(dados.get('cmc')) or explicito or tem_padrao,
        'default': cmc_padrao,
        'cmc_ids': [],
        'links': [],
    }

    declaracao = dados.get('cmc_declaracao')
    if declaracao is not None and not isinstance(declaracao, dict):
        raise ValueError("O campo 'cmc_declaracao' deve ser um objeto.")

    if isinstance(declaracao, dict):
        for chave in ('id', 'nome', 'referencia', 'link', 'descricao'):
            valor = declaracao.get(chave)
            if valor is not None and str(valor).strip() != '':
                config[chave] = str(valor).strip()

        autoridade = declaracao.get('autoridade')
        if autoridade is not None:
            if not isinstance(autoridade, dict):
                raise ValueError(
                    "O campo 'cmc_declaracao.autoridade' deve ser um objeto."
                )
            for chave in ('nome', 'cidade', 'pais'):
                valor = autoridade.get(chave)
                if valor is not None and str(valor).strip() != '':
                    config['autoridade'][chave] = str(valor).strip()

        cmc_ids = resolve_cmc_ids(declaracao)
        if cmc_ids:
            if not (config['enabled'] or config['statement']):
                raise ValueError(
                    "'cmc_declaracao.cmc_id' exige cmc=True, in_cmc ou "
                    "cmc_padrao."
                )
            config['cmc_ids'] = cmc_ids
            config['links'] = [KCDB_CMC_BASE_URL + cmc_id for cmc_id in cmc_ids]

    if not CMC_ID_PATTERN.match(config['id']):
        raise ValueError(
            "Identificador inválido em 'cmc_declaracao.id': %r. Use letras, "
            "números, ponto, hífen ou sublinhado, começando por letra ou "
            "sublinhado." % (config['id'],)
        )

    return config


def add_cmc_metadata(parent, ref_id, statuses):
    """Adiciona dcc:measurementMetaData com dcc:valid/validXMLList.

    Para um unico ponto usa dcc:valid; para listas usa dcc:validXMLList com
    um booleano por valor, na mesma ordem de si:valueXMLList.
    """
    measurement_metadata = etree.SubElement(
        parent, etree.QName(nsmap['dcc'], 'measurementMetaData'))
    meta_data = etree.SubElement(
        measurement_metadata, etree.QName(nsmap['dcc'], 'metaData'),
        refId=ref_id)

    bools = ['true' if status else 'false' for status in statuses]
    if len(bools) == 1:
        valid = etree.SubElement(meta_data, etree.QName(nsmap['dcc'], 'valid'))
        valid.text = bools[0]
    else:
        valid_list = etree.SubElement(
            meta_data, etree.QName(nsmap['dcc'], 'validXMLList'))
        valid_list.text = ' '.join(bools)


def has_ref_type_definition(dados, namespace):
    """Indica se o payload declarou um namespace de refType."""
    namespace = str(namespace).strip().lower()
    for definicao in dados.get('refTypeDefinitions', []) or []:
        if not isinstance(definicao, dict):
            continue
        if str(definicao.get('namespace', '')).strip().lower() == namespace:
            return True
    return False


def has_basic_ref_type_definition(dados):
    """Indica se o usuario ja declarou o namespace 'basic'."""
    return has_ref_type_definition(dados, 'basic')


def add_basic_ref_type_definition(ref_type_definitions):
    """Declara o namespace 'basic' para o refType basic_isInCMC."""
    ref_type_definition = etree.SubElement(
        ref_type_definitions, etree.QName(nsmap['dcc'], 'refTypeDefinition'))

    campo_name(ref_type_definition, 'Namespace for Cross-Community RefTypes', 'en')

    description = etree.SubElement(
        ref_type_definition, etree.QName(nsmap['dcc'], 'description'))
    campo_texto(
        description,
        'content',
        "The 'basic' namespace contains RefTypes common for multiple communities.",
        'en')

    campo_texto(ref_type_definition, 'namespace', 'basic')
    campo_texto(
        ref_type_definition,
        'link',
        'https://digilab.ptb.de/dkd/refType/vocab/index.php?tema=2')


def add_cmc_statement(statements, dados, config, declaracao):
    """Adapta o statement de CMC para o formato estruturado basic_isInCMC.

    O statement textual emitido quando cmc=True passa a ser o mesmo
    statement usado pela marcacao: ganha id, refType e respAuthority, e
    mantem a declaracao textual do MRA em dcc:declaration.
    """
    statement = etree.SubElement(
        statements,
        etree.QName(nsmap['dcc'], 'statement'),
        id=config['id'],
        refType=CMC_REF_TYPE)

    campo_name(statement, config['nome'])

    description = etree.SubElement(statement, etree.QName(nsmap['dcc'], 'description'))
    campo_texto(description, 'content', config['descricao'])

    campo_texto(statement, 'reference', config['referencia'])

    for cmc_id in config.get('cmc_ids', []):
        campo_texto(statement, 'reference', cmc_id)

    links = config.get('links') or [config['link']]
    for link in links:
        campo_texto(statement, 'link', link)

    # Mantem a declaracao textual do MRA quando o certificado tem CMC.
    # A ordem do XSD exige 'declaration' antes de 'respAuthority'.
    if is_truthy(dados.get('cmc')):
        declaration = etree.SubElement(
            statement, etree.QName(nsmap['dcc'], 'declaration'))
        campo_texto(declaration, 'content', declaracao['cmc'])

    resp_authority = etree.SubElement(
        statement, etree.QName(nsmap['dcc'], 'respAuthority'))
    campo_name(resp_authority, config['autoridade']['nome'])

    location = etree.SubElement(
        resp_authority, etree.QName(nsmap['dcc'], 'location'))
    campo_texto(location, 'city', config['autoridade']['cidade'])
    campo_texto(location, 'countryCode', config['autoridade']['pais'])


# ---------------------------------------------------------------------------
# Valor nominal do item (dcc:itemQuantity com basic_nominalValue)
#
# O DCC 3.3.0 permite declarar quantidades do item em
# dcc:item/dcc:itemQuantities/dcc:itemQuantity. O DKD-E 1-1 usa
# refType="basic_nominalValue" para registrar o valor nominal (valor de
# placa/impresso) de forma estruturada. O campo e opcional.
# ---------------------------------------------------------------------------

NOMINAL_VALUE_REF_TYPE = 'basic_nominalValue'
NOMINAL_VALUE_DEFAULT_NAME = 'Valor nominal'


def resolve_nominal_value(dados):
    """Resolve o valor nominal estruturado do item.

    Formato recomendado:
        "valor_nominal": {
            "valor": "100",
            "unidade": "\\ohm",
            "nome": "Valor nominal",       # opcional
            "descricao": "..."             # opcional
        }

    Por compatibilidade com o gerador legado (aws_lambda), aceita tambem:
        "valor_nominal": "100",
        "valnom_unit": "\\ohm"

    Retorna None quando o campo nao e informado.
    """
    raw = dados.get('valor_nominal')
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None
    if isinstance(raw, (list, tuple, bool)):
        raise ValueError(
            "O campo 'valor_nominal' deve ser um objeto com 'valor' e "
            "'unidade'."
        )

    if isinstance(raw, dict):
        valor = raw.get('valor')
        unidade = raw.get('unidade', raw.get('unit'))
        nome = raw.get('nome')
        descricao = raw.get('descricao')
    else:
        valor = raw
        unidade = dados.get('valnom_unit', dados.get('unidade'))
        nome = None
        descricao = None

    if valor is None or str(valor).strip() == '':
        raise ValueError(
            "O campo 'valor_nominal.valor' é obrigatório quando "
            "'valor_nominal' é informado."
        )
    if unidade is None or str(unidade).strip() == '':
        raise ValueError(
            "O campo 'valor_nominal.unidade' é obrigatório quando "
            "'valor_nominal' é informado."
        )

    nome = str(nome).strip() if nome is not None else ''
    descricao = str(descricao).strip() if descricao is not None else ''

    return {
        'valor': str(valor).strip(),
        'unidade': str(unidade).strip(),
        'nome': nome or NOMINAL_VALUE_DEFAULT_NAME,
        'descricao': descricao or None,
    }


def add_nominal_value(item, config):
    """Adiciona dcc:itemQuantities/dcc:itemQuantity com basic_nominalValue."""
    item_quantities = etree.SubElement(
        item, etree.QName(nsmap['dcc'], 'itemQuantities'))
    item_quantity = etree.SubElement(
        item_quantities,
        etree.QName(nsmap['dcc'], 'itemQuantity'),
        refType=NOMINAL_VALUE_REF_TYPE)

    campo_name(item_quantity, config['nome'])

    if config.get('descricao'):
        description = etree.SubElement(
            item_quantity, etree.QName(nsmap['dcc'], 'description'))
        campo_texto(description, 'content', config['descricao'])

    si_real = etree.SubElement(
        item_quantity, etree.QName(nsmap['si'], 'real'))
    si_value = etree.SubElement(si_real, etree.QName(nsmap['si'], 'value'))
    si_value.text = config['valor']
    si_unit = etree.SubElement(si_real, etree.QName(nsmap['si'], 'unit'))
    si_unit.text = config['unidade']


def validate_relative_uncertainty(dados):
    """Valida a combinacao de flags da incerteza relativa.

    O bloco dcc:relativeUncertainty representa uma incerteza relativa.
    Por isso, so pode ser emitido quando a entrada 'unc' tambem e relativa
    (unc_relativa=true). A combinacao inversa gera erro 400.
    """
    for linha in dados.get('mensurando', []) or []:
        if (is_truthy(linha.get('relative_uncertainty_in_dcc'))
                and not is_truthy(linha.get('unc_relativa'))):
            label = linha.get('label', '?')
            raise ValueError(
                "relative_uncertainty_in_dcc=true exige unc_relativa=true "
                "no mensurando '%s'." % label
            )


def add_expanded_uncertainty(parent, uncertainty, coverage_factor, probability='0.9545'):
    """Adiciona incerteza expandida a um si:real no formato D-SI 2.2.1.

    Estrutura: si:measurementUncertaintyUnivariate/si:expandedMU.
    """
    measurement_uncertainty = etree.SubElement(
        parent, etree.QName(nsmap['si'], 'measurementUncertaintyUnivariate'))
    expanded_mu = etree.SubElement(
        measurement_uncertainty, etree.QName(nsmap['si'], 'expandedMU'))
    value = etree.SubElement(
        expanded_mu, etree.QName(nsmap['si'], 'valueExpandedMU'))
    value.text = str(uncertainty)
    coverage_factor_node = etree.SubElement(
        expanded_mu, etree.QName(nsmap['si'], 'coverageFactor'))
    coverage_factor_node.text = str(coverage_factor)
    coverage_probability_node = etree.SubElement(
        expanded_mu, etree.QName(nsmap['si'], 'coverageProbability'))
    coverage_probability_node.text = str(probability)


def add_expanded_uncertainty_list(parent, uncertainties, coverage_factors, probability='0.9545'):
    """Adiciona incerteza expandida em lista no formato D-SI 2.2.1.

    Estrutura:
    si:measurementUncertaintyUnivariateXMLList/si:expandedMUXMLList.
    """
    measurement_uncertainty = etree.SubElement(
        parent, etree.QName(nsmap['si'], 'measurementUncertaintyUnivariateXMLList'))
    expanded_mu = etree.SubElement(
        measurement_uncertainty, etree.QName(nsmap['si'], 'expandedMUXMLList'))
    value = etree.SubElement(
        expanded_mu, etree.QName(nsmap['si'], 'valueExpandedMUXMLList'))
    value.text = ' '.join(str(item) for item in uncertainties)
    coverage_factor_node = etree.SubElement(
        expanded_mu, etree.QName(nsmap['si'], 'coverageFactorXMLList'))
    coverage_factor_node.text = ' '.join(str(item) for item in coverage_factors)
    coverage_probability_node = etree.SubElement(
        expanded_mu, etree.QName(nsmap['si'], 'coverageProbabilityXMLList'))
    coverage_probability_node.text = str(probability)


def campo_name(parent_node, text, lang="pt"):  # Add lang parameter
    parent_node_name = etree.SubElement(parent_node, etree.QName(nsmap['dcc'], 'name'))
    parent_node_name_content = etree.SubElement(
        parent_node_name, 
        etree.QName(nsmap['dcc'], 'content'), 
        lang=lang  # Use parameter value
    )
    parent_node_name_content.text = text
    return

# gera um campo e preenche
def campo_texto(parent_node, nome_campo, texto_campo, lang="pt") :
    if (nome_campo == 'content'):
        campo = etree.SubElement(parent_node, etree.QName(nsmap['dcc'], nome_campo), lang=lang)
    else:
        campo = etree.SubElement(parent_node, etree.QName(nsmap['dcc'], nome_campo))  
    campo.text = texto_campo

    return


# cria um elemento <dcc:nome_elemento> com conteudo multilingue
# (um <dcc:content lang=...> para cada idioma informado)
def campo_conteudo_multilingue(parent_node, nome_elemento, textos) :
    elemento = etree.SubElement(parent_node, etree.QName(nsmap['dcc'], nome_elemento))
    for lang, texto in textos :
        campo_texto(elemento, 'content', texto, lang=lang)
    return elemento


# graus de liberdade efetivos (nueff): detecta +inf, tanto como numero
# (math.inf) quanto como string ("inf", "+inf", "Infinity", "∞", ...)
def is_positive_infinite(value) :
    if isinstance(value, str) :
        return value.strip().lower() in ('inf', '+inf', 'infinity', '+infinity', '∞', '+∞')

    try :
        v = float(value)
    except (TypeError, ValueError) :
        return False

    return math.isinf(v) and v > 0


# serializa os graus de liberdade efetivos (nueff) para dcc:charsXMLList
# valores finitos viram sua representacao textual; +inf vira "inf"
def serialize_nueff(values) :
    serialized = []

    for value in values :
        if is_positive_infinite(value) :
            serialized.append('inf')
        else :
            serialized.append(str(value))

    return ' '.join(serialized)


# validacao dos graus de liberdade efetivos (nueff)
def validate_nueff(nueff, expected_length) :
    if not isinstance(nueff, (list, tuple)) :
        raise ValueError("O campo 'nueff' deve ser uma lista de valores numéricos.")

    if len(nueff) != expected_length :
        raise ValueError(
            "O número de valores de 'nueff' (%d) deve ser igual ao número de resultados associados (%d)."
            % (len(nueff), expected_length)
        )

    for valor in nueff :
        if valor is None or (isinstance(valor, str) and valor.strip() == '') :
            raise ValueError("O campo 'nueff' contém um valor ausente (null ou vazio).")

        if is_positive_infinite(valor) :
            continue

        try :
            v = float(valor)
        except (TypeError, ValueError) :
            raise ValueError("Valor inválido para 'nueff': %r. Os valores devem ser numéricos." % (valor,))

        if math.isnan(v) :
            raise ValueError("Valor inválido para 'nueff': %r. Não são aceitos NaN." % (valor,))

        if math.isinf(v) :
            raise ValueError("Valor inválido para 'nueff': %r. Não são aceitos -inf." % (valor,))

        if v <= 0 :
            raise ValueError(
                "Valor inválido para 'nueff': %r. Os graus de liberdade efetivos devem ser positivos." % (valor,)
            )

    return True


def dccGen(dcc_version, dados, declaracao) :

    if dcc_version not in SUPPORTED_DCC_VERSIONS:
        raise ValueError(
            "Versão de schema não suportada: %r. Versão suportada: 3.3.0."
            % (dcc_version,)
        )
    schema_url = SUPPORTED_DCC_VERSIONS[dcc_version]

    validate_relative_uncertainty(dados)

    # marcacao de pontos dentro/fora da CMC (opcional)
    cmc_config = resolve_cmc_config(dados)

    # valor nominal estruturado do item (opcional)
    nominal_config = resolve_nominal_value(dados)

    dcc = etree.Element(
        etree.QName(nsmap['dcc'], 'digitalCalibrationCertificate'),
        {schemaLocation: 'https://ptb.de/dcc '+schema_url, 'schemaVersion' : dcc_version},
        nsmap=nsmap)

    # admistrativeData block
    administrativeData = etree.SubElement(dcc, etree.QName(nsmap['dcc'], 'administrativeData'))

    # software information
    dccSoftware = etree.SubElement(administrativeData, etree.QName(nsmap['dcc'], 'dccSoftware'))
    software = etree.SubElement(dccSoftware, etree.QName(nsmap['dcc'], 'software'))

    campo_name(software,__appname__)
    campo_texto(software,'release',__version__)

    # por padrao inclui informacao desse software (dccGenerator)
    # opcional: incluir tambem informacao de software recebida via API
    # chave: software
    # subchaves: name e version
    if 'software' in dados :
        for sfw in dados['software'] :
            software = etree.SubElement(dccSoftware, etree.QName(nsmap['dcc'], 'software'))
            campo_name(software,sfw['name'])
            campo_texto(software,'release',sfw['version'])

    # refTypes
    # campos opcionais porem muito uteis para o processamento automatizado dos DCCs
    #refTypeDefinitions = etree.SubElement(administrativeData, etree.QName(nsmap['dcc'], 'refTypeDefinitions'))
    # definicao do namespace basic - incluida por padrao
    ## 16/10/2025 - removido como padrao - pode ser enviado como opcional
    #refTypeDefinition = etree.SubElement(refTypeDefinitions, etree.QName(nsmap['dcc'], 'refTypeDefinition'))
    #content_basic_en = "Namespace for Cross-Community RefTypes"
    #campo_name(refTypeDefinition,content_basic_en,'en')
    #content_basic_pt = "Espaço de nomes com RefTypes comuns a múltiplas áreas"
    #campo_name(refTypeDefinition,content_basic_pt)

    #description = etree.SubElement(refTypeDefinition, etree.QName(nsmap['dcc'], 'description'))
    #desc_basic_en = "The 'basic' namespace contains RefTypes common for multiple communities."
    #campo_texto(description,'content',desc_basic_en,'en')
    #desc_basic_pt = "O espaço de nomes 'basic' contém RefTypes comuns a múltiplas áreas."
    #campo_texto(description,'content',desc_basic_pt)

    # namespace
    #campo_texto(refTypeDefinition,'namespace','basic')
    # link
    #campo_texto(refTypeDefinition,'link','https://digilab.ptb.de/dkd/refType/vocab/index.php?tema=2')

    # possibilidade de receber mais definicoes de refTypes via API
    # chave: refTypeDefinitions
    # subchaves: name, description, namespace e link
    refTypeDefinitions = None
    if 'refTypeDefinitions' in dados:
        refTypeDefinitions = etree.SubElement(administrativeData, etree.QName(nsmap['dcc'], 'refTypeDefinitions'))
        for refTypeDef in dados['refTypeDefinitions'] :
                refTypeDefinition = etree.SubElement(refTypeDefinitions, etree.QName(nsmap['dcc'], 'refTypeDefinition'))
                campo_name(refTypeDefinition,refTypeDef['name'])

                description = etree.SubElement(refTypeDefinition, etree.QName(nsmap['dcc'], 'description'))
                campo_texto(description,'content',refTypeDef['description'])

                # namespace
                campo_texto(refTypeDefinition,'namespace',refTypeDef['namespace'])
                # link
                campo_texto(refTypeDefinition,'link',refTypeDef['link'])

    # os refTypes basic_isInCMC e basic_nominalValue dependem do namespace
    # 'basic'; declara-o automaticamente quando um deles for emitido
    if (cmc_config['statement'] or nominal_config) and not has_basic_ref_type_definition(dados):
        if refTypeDefinitions is None:
            refTypeDefinitions = etree.SubElement(
                administrativeData, etree.QName(nsmap['dcc'], 'refTypeDefinitions'))
        add_basic_ref_type_definition(refTypeDefinitions)

    # coreData block
    coreData = etree.SubElement(administrativeData, etree.QName(nsmap['dcc'], 'coreData'))
    # country code
    campo_texto(coreData,'countryCodeISO3166_1','BR')
    # language code
    campo_texto(coreData,'usedLangCodeISO639_1','pt')
    # lingua obrigatoria
    campo_texto(coreData,'mandatoryLangCodeISO639_1','pt')

    # certificate number
    campo_texto(coreData,'uniqueIdentifier','DIMCI '+dados['num_certif'])

    # identification block -> usado para incluir o processo Inmetro
    identifications = etree.SubElement(coreData, etree.QName(nsmap['dcc'], 'identifications'))
    identification = etree.SubElement(identifications, etree.QName(nsmap['dcc'], 'identification'))

    campo_texto(identification,'issuer','calibrationLaboratory')
    campo_texto(identification,'value',dados['num_processo'])
    campo_name(identification,'Processo Inmetro')

    # data de calibracao
    campo_texto(coreData,'beginPerformanceDate',dados['data_calibracao'])
    campo_texto(coreData,'endPerformanceDate',dados['data_calibracao'])
    # local de execucao
    campo_texto(coreData,'performanceLocation','laboratory')

    # data de emissao (opcional)
    # no fluxo atual da Dimci a data de emissao eh a data da assinatura eletronica do certificado

    if 'data_emissao' in dados:
        campo_texto(coreData,'issueDate',dados['data_emissao'])
    
    # items block
    items = etree.SubElement(administrativeData, etree.QName(nsmap['dcc'], 'items'))

    # podem ser varios itens
    # estudar possibilidade de transformar em loop 
    item = etree.SubElement(items, etree.QName(nsmap['dcc'], 'item'))
    # descricao do item
    campo_name(item,dados['tipo_item'])
    # fabricante do item
    item_manufacturer = etree.SubElement(item, etree.QName(nsmap['dcc'], 'manufacturer'))
    campo_name(item_manufacturer,dados['fabricante'])
    # modelo
    campo_texto(item,'model',dados['modelo'])
    item_identifications = etree.SubElement(item, etree.QName(nsmap['dcc'], 'identifications'))
    # numero de serie
    #item_ns = etree.SubElement(item_identifications, etree.QName(nsmap['dcc'], 'identification'), refType="basic_serialNumber")
    item_ns = etree.SubElement(item_identifications, etree.QName(nsmap['dcc'], 'identification'))
    
    campo_texto(item_ns,'issuer','manufacturer')
    campo_texto(item_ns,'value',dados['num_serie'])
    campo_name(item_ns,'Número de Série')
    # código de identificação
    item_codid = etree.SubElement(item_identifications, etree.QName(nsmap['dcc'], 'identification'))
    campo_texto(item_codid,'issuer','customer')
    campo_texto(item_codid,'value',dados['cod_identificacao'])
    campo_name(item_codid,'Código de Identificação')

    # valor nominal estruturado do item (opcional, DKD-E 1-1)
    if nominal_config:
        add_nominal_value(item, nominal_config)

    # calibrationLaboratory block
    calibrationLaboratory = etree.SubElement(administrativeData, etree.QName(nsmap['dcc'], 'calibrationLaboratory'))
    calibrationLaboratoryContact = etree.SubElement(calibrationLaboratory, etree.QName(nsmap['dcc'], 'contact'))
    campo_name(calibrationLaboratoryContact, dados['nome_lab']+' ('+dados['sigla_lab']+')')
    campo_texto(calibrationLaboratoryContact,'eMail','samci@inmetro.gov.br')
    campo_texto(calibrationLaboratoryContact,'phone','+55 21 2679 9077/9010')
    calibrationLaboratoryLocation = etree.SubElement(calibrationLaboratoryContact, etree.QName(nsmap['dcc'], 'location'))
    campo_texto(calibrationLaboratoryLocation,'city','Xerém - Duque de Caxias')
    campo_texto(calibrationLaboratoryLocation,'countryCode','BR')
    campo_texto(calibrationLaboratoryLocation,'postCode','25250-020')
    campo_texto(calibrationLaboratoryLocation,'state','RJ')
    campo_texto(calibrationLaboratoryLocation,'street','Av. Nossa Senhora das Graças')
    campo_texto(calibrationLaboratoryLocation,'streetNo','50')

    # respPerson block - assinaturas
    respPersons = etree.SubElement(administrativeData, etree.QName(nsmap['dcc'], 'respPersons'))

    # chefe divisao
    respPerson = etree.SubElement(respPersons, etree.QName(nsmap['dcc'], 'respPerson'))
    person = etree.SubElement(respPerson, etree.QName(nsmap['dcc'], 'person'))
    campo_name(person,dados['chefe_div'])
    campo_texto(respPerson,'role',dados['desc_chefe_div'])
    campo_texto(respPerson,'mainSigner','true')

    # chefe lab
    respPerson = etree.SubElement(respPersons, etree.QName(nsmap['dcc'], 'respPerson'))
    person = etree.SubElement(respPerson, etree.QName(nsmap['dcc'], 'person'))
    campo_name(person,dados['chefe_lab'])
    campo_texto(respPerson,'role',dados['desc_chefe_lab'])

    # tecnico executor
    if (dados['tecnico_executor']) :
        respPerson = etree.SubElement(respPersons, etree.QName(nsmap['dcc'], 'respPerson'))
        person = etree.SubElement(respPerson, etree.QName(nsmap['dcc'], 'person'))
        campo_name(person,dados['tecnico_executor'])
        campo_texto(respPerson,'role',dados['desc_tecnico_executor'])


    # bloco customer (informacoes do cliente)
        
    customer = etree.SubElement(administrativeData, etree.QName(nsmap['dcc'], 'customer'))
    campo_name(customer,dados['cliente']['nome'])
    campo_texto(customer, 'eMail', dados['cliente']['email'])
    customer_location = etree.SubElement(customer, etree.QName(nsmap['dcc'], 'location'))
    campo_texto(customer_location, 'city', dados['cliente']['cidade'])
    campo_texto(customer_location, 'countryCode', dados['cliente']['pais'])
    campo_texto(customer_location, 'postCode', dados['cliente']['cep'])
    campo_texto(customer_location, 'state', dados['cliente']['uf'])
    campo_texto(customer_location, 'street', dados['cliente']['endereco'])
    campo_texto(customer_location, 'streetNo', dados['cliente']['numero'])


    # bloco statements (declaracoes)
    statements = etree.SubElement(administrativeData, etree.QName(nsmap['dcc'], 'statements'))

    # issueDate
    # o schema preve um campo dcc:issueDate (optional), que aceita exclusivamente uma data
    # no modelo de certificado da Dimci existe uma declaracao textual sobre a data de emissao

    # se nao receber data_emissao, incluir esse statement
    if not 'data_emissao' in dados:
        issueDate = etree.SubElement(statements, etree.QName(nsmap['dcc'], 'statement'))
        campo_name(issueDate, 'Data de Emissão')
        description = etree.SubElement(issueDate, etree.QName(nsmap['dcc'], 'description'))
        issueDateText = 'Ver data da assinatura eletrônica presente no certificado'
        campo_texto(description,'content', issueDateText)

    # caracteristicas do item (opcional) - presente no modelo de certificado
    # da Dimci. Se ausente/vazio, o statement nao e emitido; o valor nominal
    # estruturado (quando informado) continua sendo exibido na visualizacao.
    caracteristicas_item_texto = dados.get('caracteristicas_item')
    if (caracteristicas_item_texto is not None
            and str(caracteristicas_item_texto).strip() != ''):
        caracteristicas_item = etree.SubElement(
            statements, etree.QName(nsmap['dcc'], 'statement'))
        campo_name(caracteristicas_item, 'Características do Item')
        description = etree.SubElement(
            caracteristicas_item, etree.QName(nsmap['dcc'], 'description'))
        campo_texto(
            description, 'content', str(caracteristicas_item_texto).strip())

    # declaracao cmc
    # O statement de CMC existente (cmc=true) e adaptado para o formato
    # estruturado basic_isInCMC. A marcacao por ponto adiciona os vinculos
    # measurementMetaData/refId nas quantities de resultado.
    if cmc_config['statement']:
        add_cmc_statement(statements, dados, cmc_config, declaracao)

    # declaracao 17025
    statement = etree.SubElement(statements, etree.QName(nsmap['dcc'], 'statement'))
    campo_texto(statement, 'norm', declaracao['norma'])
    declaration = etree.SubElement(statement, etree.QName(nsmap['dcc'], 'declaration'))
    campo_texto(declaration,'content', declaracao['requisitos'])

    # observacoes - entra como statement?
    count = 1
    if 'observacoes' in dados :
        for obs in dados['observacoes'] :
            statement = etree.SubElement(statements, etree.QName(nsmap['dcc'], 'statement'))
            campo_name(statement, 'Observação '+str(count))
            description = etree.SubElement(statement, etree.QName(nsmap['dcc'], 'description'))
            campo_texto(description, 'content', obs)
            count+=1

    # measurementResults block
    # generalizado para a possibilidade de multiplos blocos de resultados
    measurementResults = etree.SubElement(dcc, etree.QName(nsmap['dcc'], 'measurementResults'))
    measurementResult = etree.SubElement(measurementResults, etree.QName(nsmap['dcc'], 'measurementResult'))
    campo_name(measurementResult,'Resultados e Declaração da Incerteza de Medição')
    # metodos
    usedMethods = etree.SubElement(measurementResult, etree.QName(nsmap['dcc'], 'usedMethods'))

    # metodo de medicao
    for i, metodo_medicao in enumerate(declaracao['metodo_medicao']) :
        #usedMethod = etree.SubElement(usedMethods, etree.QName(nsmap['dcc'], 'usedMethod'), refType="basic_calibrationMethod")
        usedMethod = etree.SubElement(usedMethods, etree.QName(nsmap['dcc'], 'usedMethod'))
        campo_name(usedMethod,'Método de Medição')
        description = etree.SubElement(usedMethod, etree.QName(nsmap['dcc'], 'description'))
      
        campo_texto(description,'content',metodo_medicao)

        # equacao: campo opcional
        if 'metodo_medicao_equation' in dados :
            if i < len(dados['metodo_medicao_equation']) :
                formula = etree.SubElement(description, etree.QName(nsmap['dcc'], 'formula'))
                campo_texto(formula, 'latex', dados['metodo_medicao_equation'][i])

    # incerteza
    #usedMethod = etree.SubElement(usedMethods, etree.QName(nsmap['dcc'], 'usedMethod'), refType="basic_methodMeasurementUncertainty")
    usedMethod = etree.SubElement(usedMethods, etree.QName(nsmap['dcc'], 'usedMethod'))
    campo_name(usedMethod,'Declaração da Incerteza de Medição')
    description = etree.SubElement(usedMethod, etree.QName(nsmap['dcc'], 'description'))
    campo_texto(description,'content',declaracao['incerteza'])

    # measuring equipments - rastreabilidade?
    measuringEquipments = etree.SubElement(measurementResult, etree.QName(nsmap['dcc'], 'measuringEquipments'))
    # declaracao rastreabilidade
    campo_name(measuringEquipments,declaracao['rastreabilidade'])

    # loop tabela rastreabilidade
    if 'tabela_rastreabilidade' in dados :
        for rastreabilidade in dados['tabela_rastreabilidade'] :
            measuringEquipment = etree.SubElement(measuringEquipments, etree.QName(nsmap['dcc'], 'measuringEquipment'))
            campo_name(measuringEquipment,rastreabilidade['name'])
            certificate = etree.SubElement(measuringEquipment, etree.QName(nsmap['dcc'], 'certificate'))
            referral = etree.SubElement(certificate, etree.QName(nsmap['dcc'], 'referral'))
            campo_texto(referral,'content',rastreabilidade['origem'])
            campo_texto(certificate,'referralID',rastreabilidade['certificado'])
            procedure, value = resolve_traceability_hash(rastreabilidade)
            campo_texto(certificate,'procedure', procedure)
            campo_texto(certificate,'value', value)
            identifications = etree.SubElement(measuringEquipment, etree.QName(nsmap['dcc'], 'identifications'))
            identification = etree.SubElement(identifications, etree.QName(nsmap['dcc'], 'identification'))
            campo_texto(identification, 'issuer', 'calibrationLaboratory')
            campo_texto(identification, 'value', rastreabilidade['cod_id'])
            campo_name(identification, 'Código de Identificação')


    # influence conditions - condicoes ambientais
    influenceConditions = etree.SubElement(measurementResult, etree.QName(nsmap['dcc'], 'influenceConditions'))

    # loop para incluir todas as informacoes pertinentes a atividade realizada
    for informacoes_pertinentes in dados['informacoes_pertinentes'] :
        # opcional: refType
        # se o campo for enviado, adicionar
        if 'refType' in informacoes_pertinentes :
            influenceCondition = etree.SubElement(influenceConditions, etree.QName(nsmap['dcc'], 'influenceCondition'), refType=informacoes_pertinentes['refType'])
        else :
            influenceCondition = etree.SubElement(influenceConditions, etree.QName(nsmap['dcc'], 'influenceCondition'))
        campo_name(influenceCondition,informacoes_pertinentes['name'])
        data = etree.SubElement(influenceCondition, etree.QName(nsmap['dcc'], 'data'))

        # interval format: value_min + value_max (opcional - nao quebra API)
        if 'value_min' in informacoes_pertinentes and 'value_max' in informacoes_pertinentes :
            for bound_value_key, bound_refType_key, bound_name_suffix in [
                ('value_min', 'refType_min', 'mínima'),
                ('value_max', 'refType_max', 'máxima')
            ]:
                bound_refType = informacoes_pertinentes.get(bound_refType_key)
                quantity_attribs = {'refType': bound_refType} if bound_refType else {}
                quantity = etree.SubElement(data, etree.QName(nsmap['dcc'], 'quantity'), **quantity_attribs)
                quantity_name_text = 'Temperatura ' + bound_name_suffix if 'Temperatura' in informacoes_pertinentes['name'] else 'Umidade ' + bound_name_suffix
                campo_name(quantity, quantity_name_text)
                si_real = etree.SubElement(quantity, etree.QName(nsmap['si'], 'real'))
                si_value = etree.SubElement(si_real, etree.QName(nsmap['si'], 'value'))
                si_value.text = str(informacoes_pertinentes[bound_value_key])
                if 'unit' in informacoes_pertinentes :
                    si_unit = etree.SubElement(si_real, etree.QName(nsmap['si'], 'unit'))
                    si_unit.text = informacoes_pertinentes['unit']

                if 'unc' in informacoes_pertinentes :
                    coverage_factor = informacoes_pertinentes.get('k') or '2'
                    add_expanded_uncertainty(
                        si_real,
                        informacoes_pertinentes['unc'],
                        coverage_factor,
                        '0.9545',
                    )

        # checar se tem unidade (formato valor unico - existente)
        elif 'unit' in informacoes_pertinentes :
            quantity = etree.SubElement(data, etree.QName(nsmap['dcc'], 'quantity'))
            si_real = etree.SubElement(quantity, etree.QName(nsmap['si'], 'real'))
            si_value = etree.SubElement(si_real, etree.QName(nsmap['si'], 'value'))
            si_value.text = informacoes_pertinentes['value']
            si_unit = etree.SubElement(si_real, etree.QName(nsmap['si'], 'unit'))
            si_unit.text = informacoes_pertinentes['unit']

            if 'unc' in informacoes_pertinentes :
                coverage_factor = informacoes_pertinentes.get('k') or '2'
                add_expanded_uncertainty(
                    si_real,
                    informacoes_pertinentes['unc'],
                    coverage_factor,
                    '0.9545',
                )
        else : # caso contrario, texto
            text = etree.SubElement(data, etree.QName(nsmap['dcc'], 'text'))
            campo_texto(text, 'content', informacoes_pertinentes['text'])
    

    # 22/04/2025
    # mensurando como array
    # possibilidade de mais de uma tabela de resultados

    indexes = {}

    # value, unc e k
    # listas de listas, referenciados ao mensurando
    value = {}
    unc = {}
    unc_input = {}
    k = {}
    # graus de liberdade efetivos (opcional)
    nueff = {}
    # status CMC por ponto (opcional)
    cmc_status = {}
    
    # organizar nomes e unidades dos mensurandos e indices de forma indexada
    mensurando_data = {}
    indices_data = {}

    # mensurando
    if 'mensurando' in dados :
        for i, linha in enumerate(dados['mensurando']) : 
            indexes[linha['label']] = {}
            value[linha['label']] = []
            unc[linha['label']] = []
            unc_input[linha['label']] = []
            k[linha['label']] = []
            nueff[linha['label']] = []
            cmc_status[linha['label']] = []
            # dados
            mensurando_data[linha['label']] = linha
            indices_data[linha['label']] = {}

    # indices auxiliares -> campo 'indexes'
    if 'indices' in dados :            
        #for index in dados['indices'] :
        for i, linha in enumerate(dados['indices']) :
            indexes[linha['mensurando']][linha['label']] = []
            indices_data[linha['mensurando']][linha['label']] = linha


    # loop resultados
    for i, resultados in enumerate(dados['resultados']) :
    # criar vetores com os dados para usar nas si:realListXMLList
        for mensurando in indexes :
            if resultados['mensurando'] == mensurando :
                for index in indexes[mensurando] :
                    if index in resultados:
                        indexes[mensurando][index].append(resultados[index])
    
                # resultados
                value[mensurando].append(resultados['value'])                
                unc_input[mensurando].append(resultados['unc'])

                # se incerteza esta em ppm, converter para valor absoluto
                input_unc_relative = is_truthy(mensurando_data[mensurando].get('unc_relativa'))
                if input_unc_relative :
                    unc[mensurando].append(format_two_sig_scientific(float(resultados['unc']) * 1e-6 * float(resultados['value'])))
                else :
                    unc[mensurando].append(resultados['unc'])
                
                k[mensurando].append(resultados['k'])

                # marcacao CMC do ponto: in_cmc explicito ou cmc_padrao
                in_cmc, _ = optional_bool(
                    resultados, 'in_cmc', cmc_config['default'])
                cmc_status[mensurando].append(in_cmc)

                # graus de liberdade efetivos (opcional)
                if 'nueff' in resultados and resultados['nueff'] is not None :
                    nueff[mensurando].append(resultados['nueff'])

    # results
    results = etree.SubElement(measurementResult, etree.QName(nsmap['dcc'], 'results'))
    # loop resultados
    for mensurando in mensurando_data :

        result = etree.SubElement(results, etree.QName(nsmap['dcc'], 'result'))
        # usar o campo 'mensurando' para dar nome ao grupo results
        campo_name(result, mensurando_data[mensurando]['name'])
        data = etree.SubElement(result, etree.QName(nsmap['dcc'], 'data'))
        # list -> dados em formato de tabela, mesmo se for um ponto unico
        lista = etree.SubElement(data, etree.QName(nsmap['dcc'], 'list'))

        label = None
        for index in indexes[mensurando] :

            # se for label, sem unidade
            if 'unit' not in indices_data[mensurando][index] :
                label = ' '.join(indexes[mensurando][index])
            
            else :
                # se existir refType, incluir
                if 'refType' in indices_data[mensurando][index] :
                    quantity = etree.SubElement(lista, etree.QName(nsmap['dcc'], 'quantity'), refType=indices_data[mensurando][index]['refType'])
                else :
                    quantity = etree.SubElement(lista, etree.QName(nsmap['dcc'], 'quantity'))
                    
                campo_name(quantity,indices_data[mensurando][index]['name'])
                si_realListXMLList = etree.SubElement(quantity, etree.QName(nsmap['si'], 'realListXMLList'))
                si_valueXMLList = etree.SubElement(si_realListXMLList, etree.QName(nsmap['si'], 'valueXMLList'))
                si_valueXMLList.text = ' '.join(indexes[mensurando][index])
                si_unitXMLList = etree.SubElement(si_realListXMLList, etree.QName(nsmap['si'], 'unitXMLList'))
                si_unitXMLList.text = indices_data[mensurando][index]['unit']


        # resultados de medicao
        # refType: opcional
        if 'refType' in mensurando_data[mensurando] :
            quantity = etree.SubElement(lista, etree.QName(nsmap['dcc'], 'quantity'), refType=mensurando_data[mensurando]['refType'])
        else :
            quantity = etree.SubElement(lista, etree.QName(nsmap['dcc'], 'quantity'))
            
        # nome da coluna de resultados 
        campo_name(quantity, mensurando_data[mensurando]['col_name'])
        # sempre manter resultado completo legado em si:realListXMLList
        si_realListXMLList = etree.SubElement(quantity, etree.QName(nsmap['si'], 'realListXMLList'))

        if label :
            si_labelXMLList = etree.SubElement(si_realListXMLList, etree.QName(nsmap['si'], 'labelXMLList'))
            si_labelXMLList.text = label

        si_valueXMLList = etree.SubElement(si_realListXMLList, etree.QName(nsmap['si'], 'valueXMLList'))
        si_valueXMLList.text = ' '.join(value[mensurando])
        si_unitXMLList = etree.SubElement(si_realListXMLList, etree.QName(nsmap['si'], 'unitXMLList'))
        si_unitXMLList.text = mensurando_data[mensurando]['unit']

        # incerteza expandida no bloco SI (D-SI 2.2.1)
        add_expanded_uncertainty_list(
            si_realListXMLList,
            unc[mensurando],
            k[mensurando],
            '0.9545',
        )

        # opcional: bloco dcc:relativeUncertainty completo (resultado + incerteza)
        if is_truthy(mensurando_data[mensurando].get('relative_uncertainty_in_dcc')):
            relative_uncertainty = etree.SubElement(quantity, etree.QName(nsmap['dcc'], 'relativeUncertainty'))
            relative_uncertainty_xml_list = etree.SubElement(relative_uncertainty, etree.QName(nsmap['dcc'], 'relativeUncertaintyXmlList'))

            if label :
                si_relative_labelXMLList = etree.SubElement(relative_uncertainty_xml_list, etree.QName(nsmap['si'], 'labelXMLList'))
                si_relative_labelXMLList.text = label

            # relative uncertainty values
            si_relative_valueXMLList = etree.SubElement(relative_uncertainty_xml_list, etree.QName(nsmap['si'], 'valueXMLList'))
            si_relative_valueXMLList.text = ' '.join(unc_input[mensurando])
            si_relative_unitXMLList = etree.SubElement(relative_uncertainty_xml_list, etree.QName(nsmap['si'], 'unitXMLList'))
            si_relative_unitXMLList.text = mensurando_data[mensurando].get('relative_unc_unit', '\\micro\\one')

        # opcional: marcacao dos pontos dentro/fora da CMC
        # dcc:measurementMetaData deve vir apos relativeUncertainty e antes
        # de usedMethods/usedSoftware/measuringEquipments/influenceConditions
        if cmc_config['enabled'] and cmc_status[mensurando]:
            add_cmc_metadata(quantity, cmc_config['id'], cmc_status[mensurando])

        # opcional: graus de liberdade efetivos (nueff)
        # representados como uma dcc:quantity adicional na mesma dcc:list,
        # usando dcc:charsXMLList (representacao textual, sem unidade)
        if nueff[mensurando] :
            validate_nueff(nueff[mensurando], len(value[mensurando]))

            quantity = etree.SubElement(lista, etree.QName(nsmap['dcc'], 'quantity'))

            campo_name(quantity, 'Graus de liberdade efetivos')

            charsXMLList = etree.SubElement(quantity, etree.QName(nsmap['dcc'], 'charsXMLList'))
            charsXMLList.text = serialize_nueff(nueff[mensurando])
   
    return etree.tostring(dcc, encoding="utf-8", xml_declaration=True, pretty_print=True)


# Excel2JSON
def excel_to_json(excel_path):
    # Read all sheets with specified dtypes
    sheets = pd.read_excel(excel_path, sheet_name=[
        "Metadados Principais",
        "Software",
        #"RefTypeDefinitions",
        "Cliente",
        "Informações Pertinentes",  # Updated sheet name
        "Declarações",
        "Rastreabilidade",
        "Método de Medição",
        "Mensurando",
        "Índices",
        "Resultados",
        "Observações"
    ], dtype={
        'numero': str,
        'value': str,
        'unc': str,
        'k': str,
        'faixa': str,
        'voltage': str,
        'frequency': str,
        'hash_sha256': str,
        'hash_procedure': str
    },
    engine='openpyxl'
)
    
    # Initialize JSON structure
    # tratar campos opcionais
    # tratar datas para usar formato de data do excel
    data = {
        # Main metadata
        "nome_lab": sheets["Metadados Principais"].iloc[0,1],
        "sigla_lab": sheets["Metadados Principais"].iloc[1,1],
        "nome_div": sheets["Metadados Principais"].iloc[2,1],
        "sigla_div": sheets["Metadados Principais"].iloc[3,1],
        "num_certif": sheets["Metadados Principais"].iloc[4,1],
        "num_processo": sheets["Metadados Principais"].iloc[5,1],
        "tipo_item": sheets["Metadados Principais"].iloc[6,1],
        "fabricante": sheets["Metadados Principais"].iloc[7,1],
        "modelo": sheets["Metadados Principais"].iloc[8,1],
        "num_serie": sheets["Metadados Principais"].iloc[9,1],
        "cod_identificacao": sheets["Metadados Principais"].iloc[10,1],
        "caracteristicas_item": (
            str(sheets["Metadados Principais"].iloc[11,1])
            if pd.notnull(sheets["Metadados Principais"].iloc[11,1])
            else None
        ),
        "data_calibracao": sheets["Metadados Principais"].iloc[12,1],
        "data_emissao": str(sheets["Metadados Principais"].iloc[13,1]),
        "cmc": sheets["Metadados Principais"].iloc[14,1] == "Sim",
        "chefe_div": sheets["Metadados Principais"].iloc[15,1],
        "desc_chefe_div": str(sheets["Metadados Principais"].iloc[16,1]),
        "chefe_lab": sheets["Metadados Principais"].iloc[17,1],
        "desc_chefe_lab": str(sheets["Metadados Principais"].iloc[18,1]),
        "tecnico_executor": sheets["Metadados Principais"].iloc[19,1],
        "desc_tecnico_executor": sheets["Metadados Principais"].iloc[20,1],

        #Software information
        "software": [
            {k: str(v) if pd.notnull(v) else None for k, v in row.items()}
            for _, row in sheets["Software"].iterrows()
        ],

        # "refTypeDefinitions": [
        #     {k: str(v) if pd.notnull(v) else None for k, v in row.items()}
        #     for _, row in sheets["RefTypeDefinitions"].iterrows()
        # ],
        
        # Client information
        "cliente": sheets["Cliente"].iloc[0].to_dict(),
        
        # Environmental conditions (updated sheet name)
        "informacoes_pertinentes": [
            {k: str(v) if pd.notnull(v) else None for k, v in row.items()}
            for _, row in sheets["Informações Pertinentes"].iterrows()
        ],

        # Declarations
        "declaracao_rastreabilidade": str(sheets["Declarações"].iloc[0,1]),
        "tabela_rastreabilidade": [
            {k: str(v) for k, v in row.items() if pd.notnull(v)}
            for _, row in sheets["Rastreabilidade"].iterrows()
        ],
        "declaracao_incerteza": str(sheets["Declarações"].iloc[1,1]),

        # metodo de medicao
        "metodo_medicao": [
            str(row['text']) 
            for _, row in sheets["Método de Medição"].iterrows()
        ],
        "metodo_medicao_equation": [
            str(row['equation']) 
            for _, row in sheets["Método de Medição"].iterrows()
        ] if 'equation' in sheets["Método de Medição"].columns else [],


        # informacoes sobre o mensurando
        "mensurando": [
            {
            "label": str(row['label']),
            "name": str(row['name']),
            "col_name": str(row['col_name']),
            "unit": str(row['unit']),
            "unc_relativa": row['unc_relativa'] == "Sim",
            # refType: somente se existir
            **({"refType": str(row['refType'])} if str(row['refType']) != 'nan' else {}),
            # opcional: incluir incerteza relativa no bloco dcc:relativeUncertainty
            **({"relative_uncertainty_in_dcc": str(row['relative_uncertainty_in_dcc']) == "Sim"} if 'relative_uncertainty_in_dcc' in row and str(row['relative_uncertainty_in_dcc']) != 'nan' else {}),
            # opcional: unidade da incerteza relativa (padrão: \micro\one)
            **({"relative_unc_unit": str(row['relative_unc_unit'])} if 'relative_unc_unit' in row and str(row['relative_unc_unit']) != 'nan' else {}),
            }
            for _, row in sheets["Mensurando"].iterrows()
        ], 


        # Measurement indices
        "indices": [
            {
            "mensurando": str(row['mensurando']),
            "label": str(row['label']),
            "name": str(row['name']),
            # refType: somente se existir
            **({"refType": str(row['refType'])} if str(row['refType']) != 'nan' else {}),
            # Conditionally add "unit" if the column exists
            **({"unit": str(row['unit'])} if 'unit' in sheets["Índices"].columns else {})
            }
            for _, row in sheets["Índices"].iterrows()
        ],        

        
        # Results with string preservation
        # células vazias (NaN) são descartadas para manter campos opcionais
        # (como "nueff") ausentes quando não preenchidos
        "resultados": [
            {col: str(row[col]) for col in row.index if pd.notnull(row[col])}
            for _, row in sheets["Resultados"].iterrows()
        ],
        
        # Observations
        "observacoes": [
            str(obs) for obs in 
            sheets["Observações"]["Observações"].dropna().tolist()
        ]
    }

    # Clean empty values from arrays
    for item in data["informacoes_pertinentes"]:
        item.pop('Unnamed: 0', None)
        for k in list(item.keys()):
            if item[k] is None:
                del item[k]

    # clean optional fields
    if data['data_emissao'] == 'nan' :
        del data['data_emissao']

    if data['desc_chefe_div'] == 'nan' :
        del data['desc_chefe_div']

    if data['desc_chefe_lab'] == 'nan' :
        del data['desc_chefe_lab']

    # Save JSON
    #with open(json_path, 'w', encoding='utf-8') as f:
    #	json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return data


def attach_stream(pdf, xml_stream, xml_filename, mime_type) :
    
    # Very important: Set the Subtype directly on the stream
    #xml_stream[Name.Type] = Name.EmbeddedFile
    xml_stream[Name.Subtype] = Name(mime_type)  # Escaped MIME type

    # Make the stream indirect BEFORE putting it into the file spec
    xml_stream = pdf.make_indirect(xml_stream)
    
    # Create a new dictionary for embedded files
    ef_dict = pikepdf.Dictionary()
    ef_dict[Name.F] = xml_stream
    
    # Create a filespec dictionary according to PDF/A-3b requirements
    filespec = pikepdf.Dictionary()
    filespec[Name.Type] = Name.Filespec
    filespec[Name.F] = String(xml_filename)
    filespec[Name.UF] = String(xml_filename)
    filespec[Name.EF] = ef_dict
    filespec[Name.AFRelationship] = Name.Alternative  # Required for PDF/A-3b
    #filespec[Name.Subtype] = String("application/xml")  # Required for PDF/A-3b
    filespec[Name.Subtype] = Name(mime_type)  # Escaped MIME type here too
    # Make the filespec indirect to ensure proper references
    filespec = pdf.make_indirect(filespec)
    
    # First establish the relationship in the document root
    if Name.AF not in pdf.Root:
        pdf.Root[Name.AF] = Array([filespec])
    else:
        pdf.Root[Name.AF].append(filespec)
    
    # Now add to the Names tree for navigation
    if Name.Names not in pdf.Root:
        pdf.Root[Name.Names] = pikepdf.Dictionary()
    
    if Name.EmbeddedFiles not in pdf.Root.Names:
        embedded_files_dict = pikepdf.Dictionary()
        names_array = Array()
        names_array.append(String(xml_filename))
        names_array.append(filespec)
        embedded_files_dict[Name.Names] = names_array
        pdf.Root.Names[Name.EmbeddedFiles] = embedded_files_dict
    else:
        if hasattr(pdf.Root.Names.EmbeddedFiles, 'Names'):
            names_array = pdf.Root.Names.EmbeddedFiles.Names
            names_array.append(String(xml_filename))
            names_array.append(filespec)
        else:
            names_array = Array()
            names_array.append(String(xml_filename))
            names_array.append(filespec)
            pdf.Root.Names.EmbeddedFiles[Name.Names] = names_array

def attach_xml_to_pdfa3b(pdf_path, xml_path, output_path):
    """
    Attach an XML file to a PDF/A-3b document while maintaining compliance
    
    Args:
        pdf_path (str): Path to the input PDF/A-3b file
        xml_path (str): Path to the XML file to attach
        output_path (str): Path for the output PDF with attachment
    """
    # Open the PDF/A-3b document
    pdf = Pdf.open(pdf_path)
    
    # Read the XML file
    with open(xml_path, 'rb') as f:
        xml_content = f.read()
    
    # Get XML filename
    xml_filename = os.path.basename(xml_path)
    
    # Create the file stream for the XML content
    xml_stream = pdf.make_stream(xml_content)

    mime_type = "/application/xml"

    attach_stream(pdf, xml_stream, xml_filename, mime_type)
    
    # adicionar hash
    # filename
    xml_filename = 'SHA256SUM.txt'
    xml_content = (sha256sum(xml_path)+'   '+os.path.basename(xml_path)).encode('utf-8')
    xml_stream = pdf.make_stream(xml_content)
    mime_type = "/text/plain"
    
    attach_stream(pdf, xml_stream, xml_filename, mime_type)

    # Save the modified PDF
    pdf.save(output_path)
    #print(f"XML file attached successfully to {output_path}")


## ROTAS do webapp

def _safe_next(next_url):
    """Aceita apenas redirecionamentos internos (evita open redirect)."""
    if not next_url:
        return None
    if next_url.startswith('/dcc/') and not next_url.startswith('//'):
        return next_url
    return None


@app.route('/dcc/login', methods=['GET', 'POST'])
def login():
    error = None
    next_url = _safe_next(request.args.get('next') or request.form.get('next'))
    auth_required = request.args.get('auth_required') or request.form.get('auth_required')

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user = auth.authenticate(username, password)
        if user is not None:
            auth.start_session(user)
            return redirect(next_url or url_for('landing_page'))
        error = 'Usuário ou senha inválidos.'

    return render_template(
        'login.html',
        error=error,
        next=next_url,
        auth_required=auth_required,
        username=auth.current_username(),
        reset=request.args.get('reset'),
    )


@app.route('/dcc/logout')
def logout():
    session.clear()
    return redirect(url_for('landing_page'))


@app.route('/dcc/perfil')
@auth.require_auth
def perfil():
    user = auth.get_user_by_id(g.user_id)
    if user is None:
        session.clear()
        return redirect(url_for('login'))
    return render_template('perfil.html', user=user)


@app.route('/dcc/perfil/senha', methods=['GET', 'POST'])
@auth.require_auth
def alterar_senha():
    error = None
    success = None

    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new = request.form.get('new_password', '')
        confirm = request.form.get('new_password_confirm', '')

        if new != confirm:
            error = 'A confirmação da nova senha não confere.'
        else:
            try:
                if auth.change_password(g.user_id, current, new):
                    success = 'Senha alterada com sucesso.'
                else:
                    error = 'Senha atual incorreta.'
            except ValueError as e:
                error = str(e)

    return render_template('alterar_senha.html', error=error, success=success)


@app.route('/dcc/perfil/regenerar', methods=['POST'])
@auth.require_auth
def regenerar_api_key():
    auth.regenerate_api_key(g.user_id)
    return redirect(url_for('perfil'))


def _app_base_url():
    return (os.environ.get('APP_BASE_URL') or DEFAULT_APP_BASE_URL).rstrip('/')


def _reset_password_link(token):
    return _app_base_url() + url_for('redefinir_senha', token=token)


def send_password_reset_email(user, link):
    minutes = auth.reset_token_minutes()
    subject = 'DCC Tools - Recuperação de senha'
    body = (
        "Foi solicitada uma recuperação de senha para o usuário '%s'.\n\n"
        "Para definir uma nova senha, acesse o link abaixo (válido por %d minutos):\n"
        "%s\n\n"
        "Se você não fez esta solicitação, ignore esta mensagem.\n"
        % (user['username'], minutes, link)
    )
    return email_service.send_email(user['email'], subject, body)


@app.route('/dcc/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    message = None

    if request.method == 'POST':
        email = request.form.get('email', '')
        user = auth.get_user_by_email(email)

        if user is not None:
            if auth.count_recent_reset_requests(user['id']) < auth.MAX_RESET_REQUESTS_PER_HOUR:
                token = auth.create_password_reset_token(user['id'])
                send_password_reset_email(user, _reset_password_link(token))
            else:
                app.logger.warning(
                    'Limite de solicitações de recuperação excedido para %s', user['username']
                )

        # resposta genérica (evita revelar se o e-mail está cadastrado)
        message = ('Se o endereço estiver cadastrado, você receberá um e-mail com as '
                   'instruções para redefinir sua senha.')

    return render_template('esqueci_senha.html', message=message)


@app.route('/dcc/redefinir-senha', methods=['GET', 'POST'])
def redefinir_senha():
    token = request.values.get('token', '')
    error = None

    if request.method == 'POST':
        new = request.form.get('new_password', '')
        confirm = request.form.get('new_password_confirm', '')

        if new != confirm:
            error = 'A confirmação da nova senha não confere.'
        else:
            try:
                username = auth.consume_password_reset_token(token, new)
                if username:
                    return redirect(url_for('login', reset=1))
                error = 'Link inválido ou expirado. Solicite uma nova recuperação de senha.'
            except ValueError as e:
                error = str(e)

    return render_template('redefinir_senha.html', token=token, error=error)


@app.route('/dcc/register', methods=['GET', 'POST'])
def register():
    created = None
    error = None

    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip() or None
        password = data.get('password') or ''
        try:
            created = auth.create_user(username, password, email)
        except ValueError as e:
            error = str(e)

        if created and request.is_json:
            return jsonify(created), 201
        if error and request.is_json:
            return jsonify({'error': error}), 400

    return render_template('register.html', created=created, error=error)


@app.route('/dcc/')
def landing_page():
    return render_template('landing.html')

@app.route('/dcc/publications')
def publications():
    papers = [
        {
            'title': 'Apresentação DCC - Diele - 06/07/2026',
            'file': 'Apresentacao_DCC_Diele.pdf'
        },
        {
            'title': 'DCC 2026 Conference - YouTube Presentation',
            'external_url': 'https://www.youtube.com/watch?v=tSz8SGsDny4&t=2111s',
            'source_label': 'YouTube'
        },
        {
            'title': 'FORUM-MD (BIPM) 2026 - Presentation',
            'file': 'apresentacao_bipm_2026.pdf'
        },
        {
            'title': 'DCC 2026 Conference - Slides',
            'file': 'P26_Gean-Geronymo_slides.pdf'
        },
        {
            'title': 'DCC 2026 Conference - Abstract',
            'file': 'P26_Gean-Geronymo_abstract.pdf'
        },
        {
            'title': 'Metrologia 2025 Paper',
            'file': 'paper_metrologia2025.pdf'
        },
        {
            'title': 'DCC Tools Abstract',
            'file': 'P04_Gean-Geronymo_abstract.pdf'
        },
        {
            'title': 'DCC Tools Presentation Slides',
            'file': 'P04_Gean-Geronymo_slides.pdf'
        },
        {
            'title': 'DCC Tools Video Presentation',
            'file': 'P04_Gean-Geronymo_DCC-Tools.mp4'
        },
        {
            'title': 'Metrologia 2023 Paper',
            'file': 'paper_metrologia2023.pdf'
        }
    ]

    return render_template('publications.html', papers=papers)

@app.route('/dcc/introducao')
def introducao():
    return render_template('introducao.html')

@app.route('/dcc/api_doc')
def api_doc():
    return render_template('api_documentation.html')

def _llm_doc_path():
    """Caminho do guia Markdown para LLMs (versionado junto com a aplicação)."""
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'docs', 'llm_doc.md'
    )

@app.route('/dcc/llm_doc')
def llm_doc():
    with open(_llm_doc_path(), 'r', encoding='utf-8') as doc_file:
        doc_markdown = doc_file.read()
    return render_template('llm_doc.html', doc_markdown=doc_markdown)

@app.route('/dcc/llm_doc.md')
def llm_doc_md():
    """Entrega o guia em Markdown, pronto para ser anexado a uma LLM."""
    return send_file(
        _llm_doc_path(),
        mimetype='text/markdown',
        as_attachment=False,
        download_name='llm_doc.md',
    )

@app.route('/dcc/form_dcc')
@auth.require_auth
def form_dcc():
    return render_template('form_dcc.html')

@app.route('/dcc/excel_guide')
def excel_guide():
    return render_template('excel_guide.html')

@app.route('/dcc/exemplos')
def exemplos():
    return render_template('exemplos.html')

@app.route('/dcc/faq')
def faq():
    return render_template('faq.html')

@app.route('/dcc/upload_xml')
@auth.require_auth
def upload_xml():
    return render_template('upload_xml.html')

@app.route('/dcc/upload_xml_hr')
def upload_xml_hr():
    return render_template('upload_xml_hr.html')

@app.route('/dcc/validate_xml', methods=['GET', 'POST'])
def validate_xml():
    if request.method == 'POST':
        validation_result = {
            'status': 'error',
            'title': 'Falha na validação',
            'message': '',
            'errors': [],
            'file_name': None,
        }

        if 'xml_file' not in request.files:
            validation_result['message'] = 'Nenhum arquivo foi enviado na requisição.'
            return render_template('validate_xml.html', validation_result=validation_result), 400

        file = request.files['xml_file']
        validation_result['file_name'] = file.filename

        if file.filename == '':
            validation_result['message'] = 'Nenhum arquivo selecionado.'
            return render_template('validate_xml.html', validation_result=validation_result), 400

        tmp_xml_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
                file.save(tmp_file.name)
                tmp_xml_path = tmp_file.name

            is_valid, errors = validate_dcc_xml_upload(tmp_xml_path)

            if is_valid:
                validation_result['status'] = 'success'
                validation_result['title'] = 'XML válido'
                validation_result['message'] = 'O arquivo foi validado com sucesso contra o schema informado no próprio XML.'
                validation_result['errors'] = []
                return render_template('validate_xml.html', validation_result=validation_result), 200

            validation_result['message'] = 'O XML não passou na validação. Verifique os erros abaixo.'
            validation_result['errors'] = errors
            return render_template('validate_xml.html', validation_result=validation_result), 400

        except Exception as e:
            validation_result['message'] = f'Erro interno durante a validação: {str(e)}'
            return render_template('validate_xml.html', validation_result=validation_result), 500
        finally:
            if tmp_xml_path and os.path.exists(tmp_xml_path):
                os.unlink(tmp_xml_path)
                
    ## GET Request - exibe formulario de upload
    return render_template('validate_xml.html')

@app.route('/dcc/upload_json', methods=['GET', 'POST'])
@auth.require_auth
def upload_json():
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'json_file' not in request.files:
            return 'erro'
            
        file = request.files['json_file']
        
        # Check if file was selected
        if file.filename == '':
            return 'No selected file'
            
        # Check if it's a JSON file
        if not file.filename.lower().endswith('.json'):
            return 'Invalid file type. Please upload a JSON file'
            
        try:
            # Parse the JSON file
            json_data = json.load(file.stream)

            # Send to API endpoint
            response = requests.post(
                'http://dccgenerator/dcc/generate',
                json=json_data,
                headers={'Content-Type': 'application/json'}
            )

            # Check for API errors
            if response.status_code != 200:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                return error_msg
                
            # Extract filename from API response headers if available
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')
            else:
                # Generate a default filename
                filename = f"dcc_{json_data.get('num_certif', 'certificate').replace('/', '_')}.xml"
            
            # Return XML file for download
            return Response(
                response.content,
                mimetype='text/xml',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
            
        except json.JSONDecodeError:
            return 'Invalid JSON format'
        except Exception as e:
            return f'Error processing file: {str(e)}'
    
    # GET request - show upload form
    return render_template('upload_json.html')


@app.route('/dcc/upload_xls', methods=['GET', 'POST'])
@auth.require_auth
def upload_xls():
    if request.method == 'POST':

        # Check if a file was uploaded
        if 'xls_file' not in request.files:
            return 'erro'
            
        file = request.files['xls_file']
        
        # Check if file was selected
        if file.filename == '':
            return 'No selected file'
            
        # Check if it's a JSON file
        if not file.filename.lower().endswith('.xlsx'):
            return 'Invalid file type. Please upload a XLSX file'
            
        try:
            # Parse the JSON file
            json_data = excel_to_json(file.stream)

            # Send to API endpoint
            response = requests.post(
                'http://dccgenerator/dcc/generate',
                json=json_data,
                headers={'Content-Type': 'application/json'}
            )

            # Check for API errors
            if response.status_code != 200:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                return error_msg
                
            # Extract filename from API response headers if available
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')
            else:
                # Generate a default filename
                filename = f"dcc_{json_data.get('num_certif', 'certificate').replace('/', '_')}.xml"
            
            # Return XML file for download
            return Response(
                response.content,
                mimetype='text/xml',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
            
        except json.JSONDecodeError:
            return 'Invalid JSON format'
        except Exception as e:
            return f'Error processing file: {str(e)}'
    
    # GET request - show upload form
    return render_template('upload_xls.html')



# embutir XML no PDF
@app.route('/dcc/pdf_attach', methods = ['POST'])
@auth.require_auth
def pdf_attach():
    if request.method == 'POST' :
        if 'pdf_file' not in request.files :
            return {'error': 'No PDF file provided'}, 400
        pdf_file = request.files['pdf_file']

        if 'xml_file' not in request.files :
            return {'error': 'No XML file provided'}, 400
        xml_file = request.files['xml_file']
        
        if pdf_file and allowed_file(pdf_file.filename,{'pdf'}) :
            pdf_filename = secure_filename(pdf_file.filename)
            pdf_tmpdirname = tempfile.mkdtemp()
            pdf_caminho = os.path.join(pdf_tmpdirname, pdf_filename)
            pdf_file.save(pdf_caminho)
        else :
            return {'error': 'Invalid PDF file provided'}, 400

        if xml_file and allowed_file(xml_file.filename,{'xml'}) :
            xml_filename = secure_filename(xml_file.filename)
            xml_tmpdirname = tempfile.mkdtemp()
            xml_caminho = os.path.join(xml_tmpdirname, xml_filename)
            xml_file.save(xml_caminho)
        else :
            return {'error': 'Invalid XML file provided'}, 400

        pdfout_filename = secure_filename(pdf_file.filename+'_out')
        pdfout_tmpdirname = tempfile.mkdtemp()
        pdfout_caminho = os.path.join(pdfout_tmpdirname, pdfout_filename)
        
        attach_xml_to_pdfa3b(pdf_caminho, xml_caminho, pdfout_caminho)

        # retornar o PDF gerado
        return send_file(pdfout_caminho, as_attachment=True, download_name=pdf_filename)


## TODO ##
# usar layout do frontend de envio do PDF e XML para o envio do XLS
# processamento do XLS: atualizar a funcao excel_to_json e seguir a mesma lógica da funcao pdf_attach

## TODO ##
# criar rota para converter XLS em JSON e enviar para API

## TODO ##
# modularidade: as funcoes podem ficar em arquivos separados, mantendo a versao AWS funcional e atualizada

@app.route('/dcc/generate', methods=['POST'])
@auth.require_auth
def generate_dcc():
    # Get JSON data from request body
    try:
        dados = request.get_json()
        if not dados:
            return {'error': 'No JSON provided'}, 400
    except Exception as e:
        return {'error': f'Invalid JSON: {str(e)}'}, 400

    # Process descriptions (same logic as Lambda)
    if 'desc_chefe_div' in dados:
        dados['desc_chefe_div'] = dados['desc_chefe_div'] + ' da ' + dados['nome_div']
    else:
        dados['desc_chefe_div'] = 'Chefe da ' + dados['nome_div']

    if 'desc_chefe_lab' in dados:
        dados['desc_chefe_lab'] = dados['desc_chefe_lab'] + ' do ' + dados['nome_lab']
    else:
        dados['desc_chefe_lab'] = 'Chefe do ' + dados['nome_lab']

    # implementacao mais segura
    base_name = secure_filename(dados['num_certif'].replace('/', '_'))
    filename = f'CC_DIMCI_{base_name}.xml'
        
    #filename = 'CC_DIMCI_' + dados['num_certif'].replace('/', '_') + '.xml'

    ## TODO ##
    # implementar logica para tratamento de erros ao gerar o DCC
    declaracao = declaracoes(dados)  

    try :
        dcc_version = resolve_dcc_version(dados)
        xml_content = dccGen(dcc_version, dados, declaracao)
    except ValueError as e :
        return {'error': str(e)}, 400
    except Exception as e :
        return {'error': f'Erro ao gerar o DCC: {str(e)}'}, 500

    # Create response with XML attachment
    return Response(
        xml_content,
        mimetype='text/xml',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )

# gerar human readable usando xslt
@app.route('/dcc/visualizar_dcc', methods=['POST'])
def visualizar_dcc():
    """Handle file upload and transformation"""
    # Check if a file was uploaded
    if 'xml_file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['xml_file']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check if file is allowed
    if file and allowed_file(file.filename,{'xml'}):
        try:
            # Read XML content
            xml_content = file.read().decode('utf-8')
            
            # Transform XML to HTML
            html_result, error = transform_xml_to_html(xml_content, 'static/examples/xslt/hr_template.xsl')
            
            if error:
                return jsonify({'error': f'Erro ao processar arquivo. {str(error)}'}), 500
            
            return html_result
            
        except Exception as e:
            return jsonify({'error': f'Erro ao processar arquivo. {str(e)}'}), 500
    
    else:
        return jsonify({'error': 'Somente arquivos XML são aceitos.'}), 400


# validacao do XML
class SchemaDownloadError(Exception):
    """Erro ao baixar um schema (host nao confiavel, rede ou tamanho)."""
    pass


# hosts confiaveis para download de schemas na validacao (lista separada por virgula).
# cada entrada casa com o proprio dominio e seus subdominios.
# ptb.de: schemas DCC/SI; w3.org: xmldsig referenciado por schemas DCC antigos.
DEFAULT_ALLOWED_SCHEMA_HOSTS = 'ptb.de,w3.org'
MAX_SCHEMA_BYTES = int(os.environ.get('DCC_MAX_SCHEMA_BYTES', str(5 * 1024 * 1024)))
MAX_SCHEMA_REDIRECTS = 5


def _allowed_schema_hosts():
    raw = os.environ.get('DCC_ALLOWED_SCHEMA_HOSTS', DEFAULT_ALLOWED_SCHEMA_HOSTS)
    return [h.strip().lower() for h in raw.split(',') if h.strip()]


def _host_matches(host, domain):
    return host == domain or host.endswith('.' + domain)


def is_allowed_schema_url(url):
    """Permite apenas http(s) para hosts confiaveis, sem IP privado nem credenciais."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or '').lower()
    except ValueError:
        return False

    if parsed.scheme not in ('http', 'https'):
        return False
    if not host or parsed.username or parsed.password:
        return False
    if host == 'localhost':
        return False

    # bloqueia IP literal privado/reservado/loopback (evita SSRF direto)
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    except ValueError:
        pass

    return any(_host_matches(host, domain) for domain in _allowed_schema_hosts())


def download_file(url, local_path):
    """Baixa um arquivo validando o host contra a allowlist de schemas."""
    current = url
    for _ in range(MAX_SCHEMA_REDIRECTS):
        if not is_allowed_schema_url(current):
            raise SchemaDownloadError(
                "Download bloqueado: host não confiável para schema: %s" % current
            )

        try:
            response = requests.get(current, timeout=30, stream=True, allow_redirects=False)
        except Exception as e:
            raise SchemaDownloadError("Falha ao baixar o schema %s: %s" % (current, e))

        try:
            if response.is_redirect or 300 <= response.status_code < 400:
                location = response.headers.get('Location')
                if not location:
                    raise SchemaDownloadError(
                        "Redirecionamento sem 'Location' ao baixar o schema %s" % current
                    )
                current = urljoin(current, location)
                continue

            try:
                response.raise_for_status()
            except Exception as e:
                raise SchemaDownloadError("Falha ao baixar o schema %s: %s" % (current, e))

            chunks = []
            size = 0
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_SCHEMA_BYTES:
                    raise SchemaDownloadError(
                        "Schema excede o tamanho máximo permitido (%d bytes)." % MAX_SCHEMA_BYTES
                    )
                chunks.append(chunk)

            data = b''.join(chunks)
            text = data.decode(response.encoding or 'utf-8', errors='replace')

            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(text)
            return
        finally:
            response.close()

    raise SchemaDownloadError("Muitos redirecionamentos ao baixar o schema %s" % url)


def validate_dcc_xml_upload(xml_path):
    """
    Validate a DCC XML file from an uploaded file

    Args:
        xml_path (str): Path to the temporary XML file

    Returns:
        tuple: (is_valid, list_of_errors)
    """
    # Create a temporary directory for all XSD files
    temp_dir = tempfile.mkdtemp()
    errors = []

    try:
        # Read the XML file
        with open(xml_path, 'r') as f:
            xml_content = f.read()

        # Extract the schema URL from the XML
        schema_match = re.search(r'xsi:schemaLocation="[^"]*\.xsd"', xml_content)
        if not schema_match:
            raise ValueError("schemaLocation attribute not found or doesn't contain XSD")

        schema_location = schema_match.group(0)
        schema_url = schema_location.split()[-1].replace('"', '').strip()

        # Download the main XSD file
        main_xsd_name = os.path.basename(urlparse(schema_url).path)
        main_xsd_path = os.path.join(temp_dir, main_xsd_name)

        try:
            download_file(schema_url, main_xsd_path)

            # Process dependencies in the main XSD
            process_xsd_dependencies(main_xsd_path, temp_dir)
        except SchemaDownloadError as e:
            # schema em host nao confiavel / indisponivel: falha de validacao clara
            return False, [str(e)]

        # Validate the XML using the main XSD
        is_valid, validation_errors = validate_with_xsd(xml_path, main_xsd_path)
        errors.extend(validation_errors)

        return is_valid, errors

    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

def process_xsd_dependencies(xsd_path, temp_dir, seen=None):
    """Process an XSD file to download its dependencies and update references"""
    if seen is None:
        seen = set()
    if xsd_path in seen:
        return
    seen.add(xsd_path)

    with open(xsd_path, 'r', encoding='utf-8') as f:
        xsd_content = f.read()
    
    # Find all schemaLocation attributes in the XSD
    schema_locations = re.findall(r'schemaLocation="([^"]*)"', xsd_content)
    
    for schema_url in schema_locations:
        # Download the dependency
        dep_xsd_name = os.path.basename(urlparse(schema_url).path)
        dep_xsd_path = os.path.join(temp_dir, dep_xsd_name)
        
        download_file(schema_url, dep_xsd_path)
        
        # Update the main XSD to reference the local file
        xsd_content = xsd_content.replace(schema_url, dep_xsd_name)
        
        # Recursively process dependencies of this dependency
        process_xsd_dependencies(dep_xsd_path, temp_dir, seen)
    
    # Write the updated content back to the main XSD
    with open(xsd_path, 'w', encoding='utf-8') as f:
        f.write(xsd_content)

def validate_with_xsd(xml_path, xsd_path):
    """Validate an XML file against an XSD schema"""
    errors = []
    
    try:
        # Parse the XML and XSD
        xml_doc = etree.parse(xml_path)
        xsd_doc = etree.parse(xsd_path)
        
        # Create a schema validator
        xml_schema = etree.XMLSchema(xsd_doc)
        
        # Validate the XML
        is_valid = xml_schema.validate(xml_doc)
        
        if not is_valid:
            for error in xml_schema.error_log:
                errors.append(f"Line {error.line}: {error.message}")
        
        return is_valid, errors
        
    except etree.XMLSyntaxError as e:
        errors.append(f"XML syntax error: {str(e)}")
        return False, errors
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return False, errors

if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=80)

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
__version__ = '1.0'
__date__="12/06/2025"
__appname__="dccGenerator"
__author__="Gean Marcos Geronymo"
__author_email__="gmgeronymo@inmetro.gov.br"

# bibliotecas
import json
from lxml import etree
from flask import Flask, jsonify, request, abort, Response, send_file, render_template, redirect
import requests
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix


# PDF attach
import pikepdf
from pikepdf import Pdf, Name, String, Array
import os
import hashlib
import tempfile

# excel2json
import pandas as pd

# namespaces
nsmap = {'xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'dcc': 'https://ptb.de/dcc', 'si': 'https://ptb.de/si'}
# schema
schemaLocation = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")

#import os


# biblioteca potenciometrico
#import potenciometrico
# biblioteca capacitores
#import capacitor

app = Flask(__name__, static_url_path='/dcc/static')
app.debug = True

# App is behind one proxy that sets the -For and -Host headers.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)

# funcoes auxiliares

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


def dccGen(dcc_version, dados, declaracao) :

    dcc = etree.Element(
        etree.QName(nsmap['dcc'], 'digitalCalibrationCertificate'),
        {schemaLocation: 'https://ptb.de/dcc https://ptb.de/dcc/v'+dcc_version+'/dcc.xsd', 'schemaVersion' : dcc_version},
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
    refTypeDefinitions = etree.SubElement(administrativeData, etree.QName(nsmap['dcc'], 'refTypeDefinitions'))
    # definicao do namespace basic - incluida por padrao
    refTypeDefinition = etree.SubElement(refTypeDefinitions, etree.QName(nsmap['dcc'], 'refTypeDefinition'))
    #content_basic_en = "Namespace for Cross-Community RefTypes"
    #campo_name(refTypeDefinition,content_basic_en,'en')
    content_basic_pt = "Espaço de nomes com RefTypes comuns a múltiplas áreas"
    campo_name(refTypeDefinition,content_basic_pt)

    description = etree.SubElement(refTypeDefinition, etree.QName(nsmap['dcc'], 'description'))
    #desc_basic_en = "The 'basic' namespace contains RefTypes common for multiple communities."
    #campo_texto(description,'content',desc_basic_en,'en')
    desc_basic_pt = "O espaço de nomes 'basic' contém RefTypes comuns a múltiplas áreas."
    campo_texto(description,'content',desc_basic_pt)

    # namespace
    campo_texto(refTypeDefinition,'namespace','basic')
    # link
    campo_texto(refTypeDefinition,'link','https://digilab.ptb.de/dkd/refType/vocab/index.php?tema=2')

    # possibilidade de receber mais definicoes de refTypes via API
    # chave: refTypeDefinitions
    # subchaves: name, description, namespace e link
    if 'refTypeDefinitions' in dados:
        for refTypeDef in dados['refTypeDefinitions'] :
                refTypeDefinition = etree.SubElement(refTypeDefinitions, etree.QName(nsmap['dcc'], 'refTypeDefinition'))
                campo_name(refTypeDefinition,refTypeDef['name'])

                description = etree.SubElement(refTypeDefinition, etree.QName(nsmap['dcc'], 'description'))
                campo_texto(description,'content',refTypeDef['description'])

                # namespace
                campo_texto(refTypeDefinition,'namespace',refTypeDef['namespace'])
                # link
                campo_texto(refTypeDefinition,'link',refTypeDef['link'])
                
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
    item_ns = etree.SubElement(item_identifications, etree.QName(nsmap['dcc'], 'identification'), refType="basic_serialNumber")
    campo_texto(item_ns,'issuer','manufacturer')
    campo_texto(item_ns,'value',dados['num_serie'])
    campo_name(item_ns,'Número de Série')
    # código de identificação
    item_codid = etree.SubElement(item_identifications, etree.QName(nsmap['dcc'], 'identification'))
    campo_texto(item_codid,'issuer','customer')
    campo_texto(item_codid,'value',dados['cod_identificacao'])
    campo_name(item_codid,'Código de Identificação')

    # calibrationLaboratory block
    calibrationLaboratory = etree.SubElement(administrativeData, etree.QName(nsmap['dcc'], 'calibrationLaboratory'))
    calibrationLaboratoryContact = etree.SubElement(calibrationLaboratory, etree.QName(nsmap['dcc'], 'contact'))
    campo_name(calibrationLaboratoryContact, dados['nome_lab']+'('+dados['sigla_lab']+')')
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

    # caracteristicas do item - presente no modelo de certificado da Dimci
    # receber no campo caracteristicas_item
    caracteristicas_item = etree.SubElement(statements, etree.QName(nsmap['dcc'], 'statement'))
    campo_name(caracteristicas_item, 'Características do Item')
    description = etree.SubElement(caracteristicas_item, etree.QName(nsmap['dcc'], 'description'))
    campo_texto(description,'content', dados['caracteristicas_item'])

    # declaracao cmc
    if (dados['cmc']) :
        statement = etree.SubElement(statements, etree.QName(nsmap['dcc'], 'statement'))
        declaration = etree.SubElement(statement, etree.QName(nsmap['dcc'], 'declaration'))
        campo_texto(declaration, 'content', declaracao['cmc'])

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
        usedMethod = etree.SubElement(usedMethods, etree.QName(nsmap['dcc'], 'usedMethod'), refType="basic_calibrationMethod")
        campo_name(usedMethod,'Método de Medição')
        description = etree.SubElement(usedMethod, etree.QName(nsmap['dcc'], 'description'))
      
        campo_texto(description,'content',metodo_medicao)

        # equacao: campo opcional
        if 'metodo_medicao_equation' in dados :
            if i < len(dados['metodo_medicao_equation']) :
                formula = etree.SubElement(description, etree.QName(nsmap['dcc'], 'formula'))
                campo_texto(formula, 'latex', dados['metodo_medicao_equation'][i])

    # incerteza
    usedMethod = etree.SubElement(usedMethods, etree.QName(nsmap['dcc'], 'usedMethod'), refType="basic_methodMeasurementUncertainty")
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
            campo_texto(certificate,'procedure','analog')
            campo_texto(certificate,'value','analog')
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
        # checar se tem unidade
        if 'unit' in informacoes_pertinentes :
            quantity = etree.SubElement(data, etree.QName(nsmap['dcc'], 'quantity'))
            si_real = etree.SubElement(quantity, etree.QName(nsmap['si'], 'real'))
            si_value = etree.SubElement(si_real, etree.QName(nsmap['si'], 'value'))
            si_value.text = informacoes_pertinentes['value']
            si_unit = etree.SubElement(si_real, etree.QName(nsmap['si'], 'unit'))
            si_unit.text = informacoes_pertinentes['unit']
            si_expandedUnc = etree.SubElement(si_real, etree.QName(nsmap['si'], 'expandedUnc'))
            si_uncertainty = etree.SubElement(si_expandedUnc, etree.QName(nsmap['si'], 'uncertainty'))
            si_uncertainty.text = informacoes_pertinentes['unc']
            si_coveragefactor = etree.SubElement(si_expandedUnc, etree.QName(nsmap['si'], 'coverageFactor'))
            if 'k' in informacoes_pertinentes :
                si_coveragefactor.text = informacoes_pertinentes['k']
            else :
                si_coveragefactor.text = '2'
            
            si_coverageprob = etree.SubElement(si_expandedUnc, etree.QName(nsmap['si'], 'coverageProbability'))
            si_coverageprob.text = '0.9545'
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
    k = {}
    
    # organizar nomes e unidades dos mensurandos e indices de forma indexada
    mensurando_data = {}
    indices_data = {}

    # mensurando
    if 'mensurando' in dados :
        for i, linha in enumerate(dados['mensurando']) : 
            indexes[linha['label']] = {}
            value[linha['label']] = []
            unc[linha['label']] = []
            k[linha['label']] = []
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

                # se incerteza esta em ppm, converter para valor absoluto
                if (mensurando_data[mensurando]['unc_relativa']) :
                    unc[mensurando].append("{:.2E}".format(float(resultados['unc']) * 1e-6 * float(resultados['value'])))
                else :
                    unc[mensurando].append(resultados['unc'])
                
                k[mensurando].append(resultados['k'])

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
        si_realListXMLList = etree.SubElement(quantity, etree.QName(nsmap['si'], 'realListXMLList'))

        if label :
            si_labelXMLList = etree.SubElement(si_realListXMLList, etree.QName(nsmap['si'], 'labelXMLList'))
            si_labelXMLList.text = label
    
        si_valueXMLList = etree.SubElement(si_realListXMLList, etree.QName(nsmap['si'], 'valueXMLList'))
        si_valueXMLList.text = ' '.join(value[mensurando])
        si_unitXMLList = etree.SubElement(si_realListXMLList, etree.QName(nsmap['si'], 'unitXMLList'))
        si_unitXMLList.text = mensurando_data[mensurando]['unit']
        si_expandedUncXMLList = etree.SubElement(si_realListXMLList, etree.QName(nsmap['si'], 'expandedUncXMLList'))
        si_uncertaintyXMLList = etree.SubElement(si_expandedUncXMLList, etree.QName(nsmap['si'], 'uncertaintyXMLList'))
        si_uncertaintyXMLList.text = ' '.join(unc[mensurando])
        si_coverageFactorXMLList = etree.SubElement(si_expandedUncXMLList, etree.QName(nsmap['si'], 'coverageFactorXMLList'))
        si_coverageFactorXMLList.text = ' '.join(k[mensurando])
        si_converageProbabilityXMLList = etree.SubElement(si_expandedUncXMLList, etree.QName(nsmap['si'], 'coverageProbabilityXMLList'))
        # parametro fixo, estudar se vale a pena ser ajustavel
        si_converageProbabilityXMLList.text = '0.9545'
  
    return etree.tostring(dcc, encoding="utf-8", xml_declaration=True, pretty_print=True)


# Excel2JSON
def excel_to_json(excel_path):
    # Read all sheets with specified dtypes
    sheets = pd.read_excel(excel_path, sheet_name=[
        "Metadados Principais",
        "Software",
        "RefTypeDefinitions",
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
        'frequency': str
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
        "caracteristicas_item": sheets["Metadados Principais"].iloc[11,1],
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

        "refTypeDefinitions": [
            {k: str(v) if pd.notnull(v) else None for k, v in row.items()}
            for _, row in sheets["RefTypeDefinitions"].iterrows()
        ],
        
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
            {k: str(v) for k, v in row.items()}
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
        "resultados": [
            {col: str(row[col]) for col in row.index}
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
@app.route('/dcc')
def landing_page():
    return render_template('landing.html')

@app.route('/dcc/api_doc')
def api_doc():
    return render_template('api_documentation.html')


@app.route('/dcc/upload_xml')
def upload_xml():
    return render_template('upload_xml.html')

@app.route('/dcc/upload_json', methods=['GET', 'POST'])
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
    dcc_version = '3.2.0'
    xml_content = dccGen(dcc_version, dados, declaracao)  

    # Create response with XML attachment
    return Response(
        xml_content,
        mimetype='text/xml',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )

        
if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=80)

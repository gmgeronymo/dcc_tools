## Inmetro/Dimci/Diele/Lampe
# Simple DCC Generator Lambda Function
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

import json
from lxml import etree

# parametros do programa
__name__ = 'dccGenerator'
__version__ = '0.9'

# versao 0.9
# 17/04/2024
# incluida possibilidade de multiplos resultados

# namespaces
nsmap = {'xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'dcc': 'https://ptb.de/dcc', 'si': 'https://ptb.de/si'}
# schema
schemaLocation = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")

def lambda_handler(event, context):
    
    # recebe os dados de entrada por json
    dados = json.loads(event["body"])
    dados['desc_chefe_div'] = 'Chefe da '+dados['nome_div']
    dados['desc_chefe_lab'] = 'Chefe do '+dados['nome_lab']
    
    filename = 'CC_DIMCI_'+dados['num_certif'].replace('/','_')+'.xml'
    
    declaracao = declaracoes(dados)
    
    dcc_version = '3.2.0'
    
    dcc = dccGen(dcc_version, dados, declaracao)
    
    
    return {
        'statusCode': 200,
        'headers' : {
            'Content-Type': 'text/xml',
            'Content-Disposition': 'attachment; filename="'+filename+'"'
        }, 
        'body': dcc
    }


## funcoes auxiliares

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

    campo_name(software,__name__)
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
    item_ns = etree.SubElement(item_identifications, etree.QName(nsmap['dcc'], 'identification'))
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
    usedMethod = etree.SubElement(usedMethods, etree.QName(nsmap['dcc'], 'usedMethod'))
    campo_name(usedMethod,'Declaração da Incerteza de Medição')
    description = etree.SubElement(usedMethod, etree.QName(nsmap['dcc'], 'description'))
    campo_texto(description,'content',declaracao['incerteza'])

    # measuring equipments - rastreabilidade?
    measuringEquipments = etree.SubElement(measurementResult, etree.QName(nsmap['dcc'], 'measuringEquipments'))
    # declaracao rastreabilidade
    campo_name(measuringEquipments,declaracao['rastreabilidade'])

    # loop tabela rastreabilidade
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

        for index in indexes[mensurando] :
            label = None
            # se for label, sem unidade
            if 'unit' not in indices_data[mensurando][index] :
                label = ' '.join(indexes[mensurando][index])
            
            else :
                quantity = etree.SubElement(lista, etree.QName(nsmap['dcc'], 'quantity'))
                campo_name(quantity,indices_data[mensurando][index]['name'])
                si_realListXMLList = etree.SubElement(quantity, etree.QName(nsmap['si'], 'realListXMLList'))
                si_valueXMLList = etree.SubElement(si_realListXMLList, etree.QName(nsmap['si'], 'valueXMLList'))
                si_valueXMLList.text = ' '.join(indexes[mensurando][index])
                si_unitXMLList = etree.SubElement(si_realListXMLList, etree.QName(nsmap['si'], 'unitXMLList'))
                si_unitXMLList.text = indices_data[mensurando][index]['unit']


        # resultados de medicao
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

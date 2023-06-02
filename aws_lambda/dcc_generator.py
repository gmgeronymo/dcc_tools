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
__version__ = '0.2'

# namespaces
nsmap = {'xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'dcc': 'https://ptb.de/dcc', 'si': 'https://ptb.de/si'}
# schema
schemaLocation = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")

def lambda_handler(event, context):
    
    # recebe os dados de entrada por json
    # TODO -> opcao de receber os dados por planilha Excel / ODS
    dados = json.loads(event["body"])
    dados['desc_chefe_div'] = 'Chefe da '+dados['nome_div']
    dados['desc_chefe_lab'] = 'Chefe do '+dados['nome_lab']
    
    filename = 'CC_'+dados['sigla_lab']+'_DIMCI '+dados['num_certif'].replace('/','_')+'.xml'
    
    declaracao = declaracoes()
    
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
def declaracoes() :
    declaracao = {
        'cmc' : 'Este certificado é consistente com as Capacidades de Medição e Calibração (CMCs) que estão incluídas no apêndice C do Acordo de Reconhecimento Mútuo (MRA) estabelecido pelo Comitê Internacional de Pesos e Medidas (CIPM). Conforme os termos do MRA, todos os institutos participantes reconhecem entre si a validade dos seus certificados de calibração e medição para cada uma das grandezas, faixas e incertezas de medição declaradas no Apêndice C (para maiores detalhes ver http://www.bipm.org).',
        'norma' : 'ABNT NBR ISO/IEC 17025',
        'requisitos' : 'O presente certificado de calibração atende aos requisitos da norma ABNT NBR ISO/IEC 17025 e é válido apenas para o item acima caracterizado, não sendo extensivo a quaisquer outros. Este certificado de calibração somente pode ser reproduzido em sua forma integral. Reproduções parciais devem ser previamente autorizadas pelo Inmetro.',
        'incerteza' : 'As incertezas expandidas de medição (U) relatadas são declaradas como a incerteza padrão combinada multiplicada pelo fator de abrangência k, que, para uma distribuição t, com um número efetivo de graus de liberdade ν eff , o qual corresponde a uma probabilidade de abrangência de 95,45 %. A incerteza de medição expandida foi relatada de acordo com a publicação Avaliação de Dados de Medição – Guia para a Expressão de Incerteza de medição – GUM 2008.',
        'metodo_medicao' : 'O resultado fornecido refere-se ao valor médio de seis séries de trinta medições pelo método de comparação de corrente na configuração 04 (quatro) terminais. Utilizou-se uma Ponte Automática de Resistência modelo 6010D.',
        'rastreabilidade' : 'Os resultados da calibração são rastreados ao Sistema Internacional de Unidades (SI), por intermédio dos padrões metrológicos nacionais. As medições realizadas estão referenciadas aos padrões relacionados.'
    }
    
    return declaracao

# preenche um campo <dcc:name><dcc:content>
def campo_name(parent_node, text) :
    parent_node_name = etree.SubElement(parent_node, etree.QName(nsmap['dcc'], 'name'))
    parent_node_name_content = etree.SubElement(parent_node_name, etree.QName(nsmap['dcc'], 'content'))
    parent_node_name_content.text = text
    
    return

# gera um campo e preenche
def campo_texto(parent_node, nome_campo, texto_campo) :
    campo = etree.SubElement(parent_node, etree.QName(nsmap['dcc'], nome_campo))
    campo.text = texto_campo

    return


# valor real
def valor_unidade(parent_node,valor,unidade,unc=False,k=False,ppm=False) :
    si_real = etree.SubElement(parent_node, etree.QName(nsmap['si'], 'real'))
    si_value = etree.SubElement(si_real, etree.QName(nsmap['si'], 'value'))
    si_value.text = valor
    si_unit = etree.SubElement(si_real, etree.QName(nsmap['si'], 'unit'))
    si_unit.text = unidade

    if (unc) :
        # converter incerteza relativa (ppm) em absoluta (\ohms)
        if (ppm) :
            unc = "{:.2E}".format(float(unc) * 1e-6 * float(valor))
        
        si_expandedUnc = etree.SubElement(si_real, etree.QName(nsmap['si'], 'expandedUnc'))
        si_uncertainty = etree.SubElement(si_expandedUnc, etree.QName(nsmap['si'], 'uncertainty'))
        si_uncertainty.text = unc
        si_coveragefactor = etree.SubElement(si_expandedUnc, etree.QName(nsmap['si'], 'coverageFactor'))
        if (k) :
            si_coveragefactor.text = k
        else :
            si_coveragefactor.text = '2'

        si_coverageprob = etree.SubElement(si_expandedUnc, etree.QName(nsmap['si'], 'coverageProbability'))
        si_coverageprob.text = '0.9545'

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

    # declaracao caracteristicas do item
    statement = etree.SubElement(statements, etree.QName(nsmap['dcc'], 'statement'))
    declaration = etree.SubElement(statement, etree.QName(nsmap['dcc'], 'declaration'))
    campo_texto(declaration,'content', 'Características do Item')
    statement_data = etree.SubElement(statement, etree.QName(nsmap['dcc'], 'data'))
    statement_data_quantity = etree.SubElement(statement_data, etree.QName(nsmap['dcc'], 'quantity'))
    campo_name(statement_data_quantity, 'Valor Nominal')
    valor_unidade(statement_data_quantity,dados['valor_nominal'],dados['valnom_unit'])

    # measurementResults block
    measurementResults = etree.SubElement(dcc, etree.QName(nsmap['dcc'], 'measurementResults'))
    measurementResult = etree.SubElement(measurementResults, etree.QName(nsmap['dcc'], 'measurementResult'))
    campo_name(measurementResult,'Resultados e Declaração da Incerteza de Medição')
    # metodos
    usedMethods = etree.SubElement(measurementResult, etree.QName(nsmap['dcc'], 'usedMethods'))

    # incerteza
    usedMethod = etree.SubElement(usedMethods, etree.QName(nsmap['dcc'], 'usedMethod'))
    campo_name(usedMethod,'Declaração da Incerteza de Medição')
    description = etree.SubElement(usedMethod, etree.QName(nsmap['dcc'], 'description'))
    campo_texto(description,'content',declaracao['incerteza'])

    # metodo de medicao
    usedMethod = etree.SubElement(usedMethods, etree.QName(nsmap['dcc'], 'usedMethod'))
    campo_name(usedMethod,'Método de Medição')
    description = etree.SubElement(usedMethod, etree.QName(nsmap['dcc'], 'description'))
    campo_texto(description,'content',declaracao['metodo_medicao'])

    # measuring equipments - rastreabilidade?
    measuringEquipments = etree.SubElement(measurementResult, etree.QName(nsmap['dcc'], 'measuringEquipments'))
    # declaracao rastreabilidade
    campo_name(measuringEquipments,declaracao['rastreabilidade'])

    # loop tabela rastreabilidade
    for rastreabilidade in dados['rastreabilidade'] :
        measuringEquipment = etree.SubElement(measuringEquipments, etree.QName(nsmap['dcc'], 'measuringEquipment'))
        campo_name(measuringEquipment,rastreabilidade['name'])
        certificate = etree.SubElement(measuringEquipment, etree.QName(nsmap['dcc'], 'certificate'))
        referral = etree.SubElement(certificate, etree.QName(nsmap['dcc'], 'referral'))
        campo_texto(referral,'content',rastreabilidade['certificado'])
        campo_texto(certificate,'referralID',rastreabilidade['cod_id'])
        campo_texto(certificate,'procedure','analog')
        campo_texto(certificate,'value','analog')

    # influence conditions - condicoes ambientais
    influenceConditions = etree.SubElement(measurementResult, etree.QName(nsmap['dcc'], 'influenceConditions'))

    # loop para incluir todas as condicoes ambientais
    for condicoes_ambientais in dados['condicoes_ambientais'] :
        influenceCondition = etree.SubElement(influenceConditions, etree.QName(nsmap['dcc'], 'influenceCondition'))
        campo_name(influenceCondition,condicoes_ambientais['name'])
        data = etree.SubElement(influenceCondition, etree.QName(nsmap['dcc'], 'data'))
        quantity = etree.SubElement(data, etree.QName(nsmap['dcc'], 'quantity'))
        valor_unidade(quantity,condicoes_ambientais['value'],condicoes_ambientais['unit'],condicoes_ambientais['unc'])

    # results
    results = etree.SubElement(measurementResult, etree.QName(nsmap['dcc'], 'results'))

    # loop resultados
    for i, resultados in enumerate(dados['resultados']) :
        result = etree.SubElement(results, etree.QName(nsmap['dcc'], 'result'))
        campo_name(result,'Resultados')
        data = etree.SubElement(result, etree.QName(nsmap['dcc'], 'data'))
        quantity = etree.SubElement(data, etree.QName(nsmap['dcc'], 'quantity'))
        
        if resultados['unctype'] == 'ppm' :
            valor_unidade(quantity,resultados['value'],resultados['unit'],resultados['unc'],resultados['k'],True)
        else :
            valor_unidade(quantity,resultados['value'],resultados['unit'],resultados['unc'],resultados['k'],False)
        
        # condicoes de influencia (p. ex., corrente)
        if (dados['condicoes_resultados'][i]) :
            influenceConditions = etree.SubElement(quantity, etree.QName(nsmap['dcc'], 'influenceConditions'))
            influenceCondition = etree.SubElement(influenceConditions, etree.QName(nsmap['dcc'], 'influenceCondition'))
            campo_name(influenceCondition,dados['condicoes_resultados'][i]['name'])
            data = etree.SubElement(influenceCondition, etree.QName(nsmap['dcc'], 'data'))
            quantity = etree.SubElement(data, etree.QName(nsmap['dcc'], 'quantity'))
            valor_unidade(quantity,dados['condicoes_resultados'][i]['value'],dados['condicoes_resultados'][i]['unit'])
            
    
    return etree.tostring(dcc, encoding="utf-8", xml_declaration=True, pretty_print=True)
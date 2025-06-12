## ler planilhas de medicao de capacitores
## leitura direta e substituicao
## necessita xlrd -> pip install xlrd
import os
import pandas
import datetime
import json

# converter incerteza absoluta em incerteza relativa (ppm)
def unc_ppm(Cx,Ux):
    return (Ux * 1e6) / Cx

# formatar casas decimais
def format_result_ac(R, k, u_comb):
    urx = u_comb * R * 1e-6
    srx = urx * 1e6 / R
    for n in range(-20, 21):
        # incerteza
        if srx * k > 10 ** n and srx * k < 10 ** (n + 1):
            msrx = round(srx * k * (10 ** (1 - n)))
            esrx = 10 ** (n - 1)
            U = msrx * esrx
        # resultado
        if urx * k > 0.95 * (10 ** n) and urx * k <= 0.95 * (10 ** (n + 1)):
            mrx = round(R * (10 ** (1 - n)))
            erx = 10 ** (n - 1)
            rx = mrx * erx
            ncasas = 1 - n

    # formatar strsings de saida
    # incerteza
    if U >= 100:
        ustr = ">99"
    elif U >= 9.5 and U < 100:
        ustr = "{:.0f}".format(U)
    elif U >= 0.95 and U < 9.5:
        ustr = "{:.1f}".format(U)
    elif U >= 0.095 and U < 0.95:
        ustr = "{:.2f}".format(U)
    elif U >= 0.0095 and U < 0.095:
        ustr = "{:.3f}".format(U)
    elif U >= 0.00095 and U < 0.0095:
        ustr = "{:.4f}".format(U)

    # resistencia
    if rx < 0.995 * 1e3:
        rxstr = "{:,.{}f}".format(rx, ncasas).replace(",", " ")
    elif rx >= 0.995 * 1e3 and (rx / 1e3) < 1e6:
        rxstr = "{:,.{}f}".format(rx / 1e3, ncasas + 3).replace(",", " ")
    elif rx >= 1e6 and (rx / 1e6) < 1e9:
        rxstr = "{:,.{}f}".format(rx, ncasas + 6).replace(",", " ")
    elif rx >= 1e9 and (rx / 1e9) < 1e12:
        rxstr = "{:,.{}f}".format(rx, ncasas + 9).replace(",", " ")
    elif rx >= 1e12 and (rx / 1e12) < 1e15:
        rxstr = "{:,.{}f}".format(rx, ncasas + 12).replace(",", " ")

    return {
        "rxstr": rxstr,
        "ustr": ustr
    }

def read_xls(file) :
    # remover path do nome do arquivo
    path, filename = os.path.split(file)

    # ler a planilha usando pandas
    df = pandas.read_excel(file, sheet_name='Resultados', header=None)

    # determinar se planilha eh metodo direto ou substituicao
    if (df[1][2].find('substituição') > 0) :
        subs = True
    else :
        subs = False

    # na planilha de substituicao -> um certificado por planilha
    # na planilha de leitura direta -> pode ter varios certificados
    
    # inicializar variaveis
    # certificados -> dict com o valor nominal como key
    certificados = {}
    
    # condicoes ambientais
    tx = ''
    utx = ''
    umidx = ''
    uumidx = ''
    
    # prefixo SI
    si_prefix = ''

    # flag para inicio dos pontos
    start = False;

    # dados gerenciais
    tecnico_executor = ''
    processo = ''
    requerente = ''
    
    # gerar array com os dados do registro de medicao
    # identificar dados administrativos

    # no caso de planilha de leitura direta pode ter mais de um item

    for index, row in df.iterrows() :

        if subs :
            # um unico certificado (dict)
            #certificado = {}
            # valor nominal (ignorar case)
            if (str(row[0]).strip().lower() == 'Valor Nominal:'.lower()) :
                certificado = {}
                certificado['valor_nominal'] = str(row[1])

            # fabricante
            if (str(row[0]).strip().lower() == 'Fabricante:'.lower()) :
                certificado['fabricante'] = row[1]

                # substituicao: padrao de referencia eh um capacitor
                padrao_referencia = {}
                padrao_referencia['fabricante'] = ''
                padrao_referencia['modelo'] = str(row[6])
                padrao_referencia['valor_nominal'] = str(row[8])
                padrao_referencia['ns'] = str(row[10])
                padrao_referencia['codigo'] = str(row[12])
                padrao_referencia['certificado'] = str(row[14])

            # modelo
            if (str(row[0]).strip().lower() == 'Modelo:'.lower()) :
                certificado['modelo'] = row[1]
            # codigo
            if (str(row[0]).strip().lower() == 'Código:'.lower()) :
                certificado['codigo'] = row[1]
            # num_serie
            if (str(row[0]).strip().lower() == 'N° de série:'.lower()) :
                certificado['ns'] = row[1]

            # adiciona certificado ao dict certificados
            if (str(row[0]).strip().lower() == 'Frequência (Hz)'.lower()) :
                certificados[certificado['valor_nominal'].replace(' ','')] = {}
                certificados[certificado['valor_nominal'].replace(' ','')]['certificado'] = certificado
                # pontos: lista
                certificados[certificado['valor_nominal'].replace(' ','')]['pontos'] = []
        
        # leitura direta
        else :

            # identificar DUT
            if (str(row[0]).strip().lower() == 'Capacitor padrão'.lower()) :
                # cada certificado eh um dict
                certificado = {}
                certificado['valor_nominal'] = str(row[1])
                certificado['fabricante'] = str(row[2])
                certificado['modelo'] = str(row[3])
                certificado['codigo'] = str(row[4])
                certificado['ns'] = str(row[5])

                # adiciona certificado ao dict certificados
                certificados[certificado['valor_nominal'].replace(' ','')] = {}
                certificados[certificado['valor_nominal'].replace(' ','')]['certificado'] = certificado
                # pontos: lista
                certificados[certificado['valor_nominal'].replace(' ','')]['pontos'] = []

                # padrao de referencia
                # leitura direta -> padrao de referencia eh a ponte AH2700
                if (str(row[6]) != '-') :
                    padrao_referencia = {}
                    padrao_referencia['modelo'] = str(row[6])
                    padrao_referencia['fabricante'] = str(row[8])
                    padrao_referencia['ns'] = str(row[10])
                    padrao_referencia['codigo'] = str(row[12])
                    padrao_referencia['certificado'] = str(row[14])
        
        # dados gerenciais
        if str(row[16]).strip().lower().find('técnico executor') != -1 :
            tecnico_executor = str(row[18])

        if str(row[16]).strip().lower().find('processo') != -1 :
            processo = str(row[18])

        if str(row[16]).strip().lower().find('requerente') != -1 :
            requerente = str(row[18])

        header_desc = ['Valor Nominal'.lower(), 'Frequência (Hz)'.lower()]
        
        if (str(row[0]).strip().lower() in header_desc) :

            start = index
            # unidade
            if (str(row[1]).find('pF') > 0) :
                si_prefix = 'pF'
            if (str(row[1]).find('nF') > 0) :
                si_prefix = 'nF'

        
        if (start) :
            if (index > start) :
                # temperatura
                if (index == start + 1) :
                    tx = str(round(float(row[7]),1))

                if (index == start + 2) :
                    utx = str(round(float(row[7]),1))

                # umidade
                if (index == start + 5) :
                    umidx = str(round(float(row[7]),0))

                if (index == start + 6) :
                    uumidx = str(round(float(row[7]),0))
            
                # resultados
                if ( (str(row[0]).strip() != 'nan') and (str(row[1]).strip() != '-') ) :
                    cx = float(row[1])
                    U = unc_ppm(float(row[1]), float(row[2]))
                    k = float(row[4])
                
                    ponto = {}

                    # substituicao: primeira coluna sempre eh frequencia
                    if subs :
                        ponto['frequencia'] = str(row[0])
                    else :
                        # testar se a primeira coluna eh valor nominal ou frequencia
                        if 'hz' in str(row[0]).lower() :
                            ponto['frequencia'] = str(row[0]).split()[0]

                    # nueff > 100 -> infinito
                    if (float(row[3]) > 100) :
                        ponto['nueff'] = '∞'
                        #ponto['nueff'] = 'inf'
                    else :
                        ponto['nueff'] = str(row[3])
                    
                    formatted = format_result_ac(cx,k,U/k)

                    ponto['cx'] = formatted['rxstr']
                    ponto['U'] = formatted['ustr']
                    ponto['k'] = "{:.2f}".format(k)
                    ponto['si_prefix'] = si_prefix

                    # substituicao ou leitura direta frequencia
                    if 'frequencia' in ponto :
                        # certificado unico - buscar a key
                        key = next(iter(certificados))
                        certificados[key]['pontos'].append(ponto)
                    else :
                        # buscar certificado correspondente
                        # row[0] -> valor nominal
                        certificados[row[0].replace(' ','')]['pontos'].append(ponto)

    # buscar data de medicao
    df_med = pandas.read_excel(file, sheet_name='Medições', header=None)
    data_medicao = []
    for index, row in df_med.iterrows() :
        if (index > 15) :
            if not (pandas.isna(row[17])) :
                data_medicao.append(row[17])

    # ordenar a lista de datas de medicao
    data_medicao.sort(reverse=True)

    for valnom in certificados :
        # incluir dados gerenciais
        certificados[valnom]['certificado']['tecnico_executor'] = tecnico_executor
        certificados[valnom]['certificado']['processo'] = processo
        certificados[valnom]['certificado']['requerente'] = requerente
        certificados[valnom]['certificado']['dtcal'] = data_medicao[0].strftime('%Y-%m-%d')
        # temperatura e umidade
        certificados[valnom]['certificado']['tx'] = tx
        certificados[valnom]['certificado']['utx'] = utx
        certificados[valnom]['certificado']['umidx'] = umidx
        certificados[valnom]['certificado']['uumidx'] = uumidx
        # incluir padrao de referencia
        certificados[valnom]['padrao_referencia'] = padrao_referencia

    return json.dumps(certificados)


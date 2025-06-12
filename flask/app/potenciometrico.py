## Ler planilha gerada pelo sistema de medição do Método potenciométrico
## necessita xlrd -> pip install xlrd
import os
import pandas
import datetime
import json

def read_xls(file) :
    # remover path do nome do arquivo
    path, filename = os.path.split(file)
    # determinar numero de leituras a partir do nome do arquivo
    for i in [5,10,30] :
        if str(i)+'LEITURAS' in filename :
            medicoes = i

    # ler a planilha usando pandas
    df = pandas.read_excel(file, sheet_name='Resultados', header=None)

    # gerar array com os dados do registro de medicao


    registro_medicao = {
        'rs' : df[1][4],
        'valor_rs' : df[7][4],
        'urs' : df[11][4],
        'corrente' : df[13][5],
        'rx' : df[2][11].replace(',','.'),
        'u1' : df[3][11],
        'u2' : df[4][11],
        'u3' : df[5][11],
        'u4' : df[6][11],
        'u5' : df[7][11],
        'u6' : df[8][11],
        'u7' : df[9][11],
        'u8' : df[10][11],
        'uc' : df[11][11],
        'nueff' : df[12][11],
        'k' : df[13][11],
        'U' : float(df[14][11].replace('%','').replace(',','.')) * 1e4
    }

    try :
        data_medicao = datetime.datetime.strptime(df[7][3], "%d/%m/%Y").strftime("%Y-%m-%d")
    except :
        data_medicao = None

    out = {
        'medicoes' : medicoes,
        'nome_registro' : filename,
        'processo' : df[5][3],
        'data_medicao' : data_medicao,
        'operador' : df[11][3],
        'registro_medicao' : registro_medicao
    }

    return json.dumps(out)

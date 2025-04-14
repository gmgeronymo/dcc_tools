import json
import pandas as pd
import tempfile
import requests
from multipart import MultipartParser
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter


def lambda_handler(event, context):
    try:
        # Process multipart/form-data
        content_type = event['headers']['content-type']
        # talvez mudar para utf-8 
        body = bytes(event['body'], 'iso-8859-1') if isinstance(event['body'], str) else event['body']
        
        parser = MultipartParser(body, content_type)
        parts = list(parser.parts())
        
        if not parts:
            return error_response('No file uploaded')
            
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.xlsx') as tmp:
            parts[0].file.seek(0)
            tmp.write(parts[0].file.read())
            tmp.flush()
            
            # Convert to JSON
            converted_data = excel_to_json(tmp.name)
            
            # Send to your API
            api_response = requests.post(
                'https://i3nqpfvs5fkdr72e4dm53ox7dq0tzvxc.lambda-url.sa-east-1.on.aws/',
                json=converted_data,
                headers={'Content-Type': 'application/json'}
            )
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'id': api_response.json().get('id'),
                    'message': 'File processed successfully'
                })
            }
    
    except Exception as e:
        return error_response(str(e))

def excel_to_json(excel_path):
    # Read all sheets with specified dtypes
    sheets = pd.read_excel(excel_path, sheet_name=[
        "Metadados Principais",
        "Cliente",
        "Informações Pertinentes",  # Updated sheet name
        "Rastreabilidade",
        "Resultados",
        "Índices",
        "Declarações",
        "Observações"
    ], dtype={
        'numero': str,
        'value': str,
        'unc': str,
        'k': str,
        'faixa': str,
        'voltage': str,
        'frequency': str
    })
    
    # Initialize JSON structure
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
        "cmc": sheets["Metadados Principais"].iloc[13,1] == "Sim",
        "chefe_div": sheets["Metadados Principais"].iloc[14,1],
        "chefe_lab": sheets["Metadados Principais"].iloc[15,1],
        "tecnico_executor": sheets["Metadados Principais"].iloc[16,1],
        "desc_tecnico_executor": sheets["Metadados Principais"].iloc[17,1],
        
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
        "metodo_medicao": str(sheets["Declarações"].iloc[2,1]),
        "metodo_medicao_equation": str(sheets["Declarações"].iloc[3,1]),
        "mensurando": str(sheets["Declarações"].iloc[4,1]),
        "unit": str(sheets["Declarações"].iloc[5,1]),
        "unc_ppm": sheets["Declarações"].iloc[6,1] == "Sim",

        # Measurement indices
        "indices": {
            "faixa": {
                "name": str(sheets["Índices"].iloc[0,1]),
                "unit": str(sheets["Índices"].iloc[0,2])
            },
            "voltage": {
                "name": str(sheets["Índices"].iloc[1,1]),
                "unit": str(sheets["Índices"].iloc[1,2])
            },
            "frequency": {
                "name": str(sheets["Índices"].iloc[2,1]),
                "unit": str(sheets["Índices"].iloc[2,2])
            }
        },
        
        # Results with string preservation
        "resultados": [
            {
                "faixa": str(row['faixa']),
                "voltage": str(row['voltage']),
                "frequency": str(row['frequency']),
                "value": str(row['value']),
                "unc": str(row['unc']),
                "k": str(row['k'])
            }
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

    # Save JSON
    #with open(json_path, 'w', encoding='utf-8') as f:
    #	json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return data
    # Use your existing excel_to_json function

def error_response(message):
    return {
        'statusCode': 400,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'error': message})
    }

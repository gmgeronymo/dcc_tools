import json
import pandas as pd
import tempfile
import requests
import base64

def lambda_handler(event, context):
    try:
        # Handle binary data
        if event.get('isBase64Encoded', False):
            file_content = base64.b64decode(event['body'])
        else:
            return error_response("Non-binary payload not supported")

        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix='.xlsx') as tmp:
            tmp.write(file_content)
            tmp.flush()
            
            # Convert to JSON
            try:
                converted_data = excel_to_json(tmp.name)
            except Exception as e:
                return error_response(f"Excel conversion failed: {str(e)}")

            try:
                api_response = requests.post(
                    'https://i3nqpfvs5fkdr72e4dm53ox7dq0tzvxc.lambda-url.sa-east-1.on.aws/',
                    json=converted_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                api_response.raise_for_status()
                
                return api_response.content
                    
            except requests.exceptions.RequestException as e:
                return error_response(f"API request failed: {str(e)}")

    except Exception as e:
        return error_response(f"Unexpected error: {str(e)}")

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

def success_response(id):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'id': id, 'status': 'success'})
    }

def error_response(message):
    return {
        'statusCode': 400,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': message})
    }

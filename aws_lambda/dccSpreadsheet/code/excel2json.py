import lambda_function
import json

json_path = "reconstructed.json"

data = lambda_function.excel_to_json("Calibration_Certificate.xlsx")

# Save JSON
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2, default=str)



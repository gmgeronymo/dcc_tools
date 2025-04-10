aws lambda publish-layer-version --layer-name dccSpreadsheet-layer \
    --zip-file fileb://xlsx-layer.zip \
    --compatible-runtimes python3.11 \
    --compatible-architectures "x86_64"

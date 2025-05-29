aws lambda publish-layer-version --layer-name dccPdfAttach-layer \
    --zip-file fileb://pikepdf-layer.zip \
    --compatible-runtimes python3.11 \
    --compatible-architectures "x86_64"

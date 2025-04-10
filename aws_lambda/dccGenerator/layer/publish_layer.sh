aws lambda publish-layer-version --layer-name dccGenerator-layer \
    --zip-file fileb://lxml-layer.zip \
    --compatible-runtimes python3.11 \
    --compatible-architectures "x86_64"

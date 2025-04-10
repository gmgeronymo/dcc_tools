# pass the layers string as parameter to the script
aws lambda update-function-configuration --function-name dccGeneratorNew \
    --cli-binary-format raw-in-base64-out \
    --layers $1

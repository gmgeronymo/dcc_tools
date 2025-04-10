# pass the role string as parameter to the script
aws lambda create-function --function-name dccGeneratorNew \
    --runtime python3.11 \
    --architectures "x86_64" \
    --handler lambda_function.lambda_handler \
    --role $1 \
    --zip-file fileb://deploy.zip

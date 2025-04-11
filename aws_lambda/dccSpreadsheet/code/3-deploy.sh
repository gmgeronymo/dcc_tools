# pass the function name as the first parameter
# pass the role string as 2nd parameter to the script
aws lambda create-function --function-name $1 \
    --runtime python3.11 \
    --architectures "x86_64" \
    --handler lambda_function.lambda_handler \
    --role $2 \
    --zip-file fileb://deploy.zip

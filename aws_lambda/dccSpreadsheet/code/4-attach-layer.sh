# 1st parameter: function name
# pass the layers string as parameter to the script
aws lambda update-function-configuration --function-name $1 \
    --cli-binary-format raw-in-base64-out \
    --layers $2 

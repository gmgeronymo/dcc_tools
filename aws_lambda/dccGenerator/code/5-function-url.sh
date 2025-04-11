# function name: 1st parameter
aws lambda create-function-url-config \
    --function-name $1 \
    --auth-type NONE

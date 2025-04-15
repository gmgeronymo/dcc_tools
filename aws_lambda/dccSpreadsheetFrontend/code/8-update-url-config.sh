aws lambda update-function-url-config \
    --function-name $1 \
    --cli-input-json file://config.json

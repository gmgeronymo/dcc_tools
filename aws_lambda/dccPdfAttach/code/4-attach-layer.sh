# parameters:
# 1st: function name
# 2nd: layers arn string
aws lambda update-function-configuration --function-name $1 \
    --cli-binary-format raw-in-base64-out \
    --layers $2

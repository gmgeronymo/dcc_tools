aws lambda add-permission \
  --function-name $1 \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --statement-id public-url-access \
  --function-url-auth-type NONE

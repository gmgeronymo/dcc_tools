aws lambda add-permission \
  --function-name dccGeneratorNew \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --statement-id public-url-access \
  --function-url-auth-type NONE

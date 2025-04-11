# Create role and attach policy
aws iam create-role \
  --role-name lambda-default-execution-role \
  --assume-role-policy-document file://trust-policy.json \
  --description "Default Lambda execution role"

aws iam attach-role-policy \
  --role-name lambda-default-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

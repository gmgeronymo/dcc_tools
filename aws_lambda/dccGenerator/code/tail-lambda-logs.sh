#!/bin/bash
FUNCTION_NAME="dccGeneratorNew"
LOG_GROUP="/aws/lambda/$FUNCTION_NAME"

# Get the latest log stream
LATEST_STREAM=$(aws logs describe-log-streams \
  --log-group-name $LOG_GROUP \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --query 'logStreams[0].logStreamName' \
  --output text)

# Tail logs from the latest stream
aws logs tail $LOG_GROUP \
  --log-stream-names $LATEST_STREAM \
  --follow

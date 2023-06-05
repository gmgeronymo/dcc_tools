Repository with open source tools for working with Digital Calibration Certificates (DCC).

It is still a work in progress.

The python scripts were developed to work with AWS Lambda, but you can adapt them to run locally.

To use with AWS Lambda you need to create a Lambda layer with the library lxml. You can use the file dcclayer.zip in the aws_lambda directory. Just create an AWS Lambda layer using this file and add it to the lambda functions.

In the curl_scripts directory you can find some bash scripts to interact with the AWS Lambda functions using curl.

In the examples directory you can find an example of a DCC generated using the scripts. There is a human-readable version and a XML withe human-readable pdf attached.


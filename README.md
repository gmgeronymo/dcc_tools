# DCC TOOLS

Repository with open source tools for working with Digital Calibration Certificates (DCC).

## Python Flask (current version)

The current version uses Python Flask framework, and it is available in the flask directory.
A docker-compose.yml file is available. You can build the project using the build.sh script (inside flask directory) and then run the project with

```bash
docker compose up -d
```

By the default the project will run on http://localhost:9099 (you can adjust the port in the docker-compose.yml file).

You can access the system on the url http://localhost:9099/dcc

## AWS Lambda (old version)

The initial version was built using AWS Lambda, and is available in aws_lambda directory. This version is not updated anymore.



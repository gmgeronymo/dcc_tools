#!/bin/sh

if [ $# -eq 0 ]; then
  echo "Usage: $0 <endpoint url> <dcc_file.xml>"
  echo "Example: $0 https://example.com dcc.xml"
  echo "Send the data of file dcc_data.json and receive a DCC in XML format"
  exit 1
fi

curl -X POST -H "Content-Type: application/json" --data "@dcc_data.json" $1 -o $2 



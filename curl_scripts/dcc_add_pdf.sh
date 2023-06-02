#!/bin/sh

if [ $# -eq 0 ]; then
  echo "Usage: $0 <endpoint url> <input zip file> <output xml file>"
  echo "Example: $0 https://example.com dcc.zip dcc.xml"
  echo "The zip file must contain the DCC in XML format and the human readable PDF"
  exit 1
fi

curl -X POST -H "Content-Type: application/zip" --data-binary @$2 "$1" -o "$3"


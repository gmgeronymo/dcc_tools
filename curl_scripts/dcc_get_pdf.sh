#!/bin/sh

if [ $# -eq 0 ]; then
  echo "Usage: $0 <endpoint url> <input xml file> <output pdf file>"
  echo "Example: $0 https://example.com dcc.xml dcc.pdf"
  echo "This scripts extracts the human readable PDF from a DCC in XML format"
  exit 1
fi

curl -X POST -H "Content-Type: application/xml" --data-binary @$2 $1 -o "$3"

#!/bin/sh

# script criado em 23/05/2023

if [ $# -eq 0 ]; then
    >&2 echo "Please provide the DCC xml file to validate."
    exit 1
fi

# apagar arquivos de schema antigos
rm *.xsd 2> /dev/null

# baixar o schema para arquivo local (dcc.xsd)
schema_url=$(grep -o 'xsi:schemaLocation="[^"]*\.xsd' "$1" | sed 's/xsi:schemaLocation="//' | awk '{print $2}')
xsd_file=$(basename "$schema_url")
wget -q -O "$xsd_file" "$schema_url"

# baixar dependencias schema
#schema_locations=($(grep -o 'schemaLocation="[^"]*"' "dcc.xsd" | sed 's/schemaLocation="//;s/"$//'))
schema_locations=$(grep -o 'schemaLocation="[^"]*"' "$xsd_file" | sed 's/schemaLocation="//;s/"$//')

# Check if schemaLocation URLs are found
if [ -n "$schema_locations" ]; then
  # Split the schemaLocation URLs into separate lines
  for url in $schema_locations; do
     xsd_file=$(basename "$url")
     wget -q -O "$xsd_file" "$url"
     # modificar arquivo
     sed "s|$url|$xsd_file|g" dcc.xsd > dcc_mod.xsd
     mv dcc_mod.xsd dcc.xsd
  done

fi

xmllint --schema dcc.xsd "$1" --noout

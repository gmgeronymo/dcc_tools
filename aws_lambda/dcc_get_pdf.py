
## Inmetro/Dimci/Diele/Lampe
## Lambda function to extract base64 encoded pdf from XML DCC

# Author: Gean Marcos Geronymo

# This file is part of Inmetro DCC Tools.
#
# Inmetro DCC Tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Your Project is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Inmetro DCC Tools. If not, see <http://www.gnu.org/licenses/>.

import xml.etree.ElementTree as ET

def lambda_handler(event, context):
    # Get the XML data from the POST request
    xml_data = event['body']
    
    try:
        # Parse the XML data
        root = ET.fromstring(xml_data)

        # Get the base64-encoded PDF data
        base64_data = root.find('.//{https://ptb.de/dcc}dataBase64').text

        # Return the PDF as a base64-encoded string
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/pdf',
                'Content-Disposition': 'attachment; filename="output.pdf"'
            },
            'body': base64_data,
            'isBase64Encoded': True
        }
    except Exception as e:
        # Return an error message if dataBase64 is not found
        response = {
            'statusCode': 400,
            'body': 'Invalid XML format: dataBase64 element not found'
        }

    return response

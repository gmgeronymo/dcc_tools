## Inmetro/Dimci/Diele/Lampe
## Lambda function to add a base64 encoded pdf into a XML DCC

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


import zipfile
import base64
from lxml import etree
from io import BytesIO

def lambda_handler(event, context):
    
    # Retrieve the uploaded zip file
    zip_file_base64 = event['body']

    # Decode the zip file from base64
    zip_file_content = base64.b64decode(zip_file_base64)
    zip_file = BytesIO(zip_file_content)

    # Extract the XML and PDF files from the zip file
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        xml_filename = None
        pdf_filename = None

        for file in zip_ref.namelist():
            if file.endswith('.xml'):
                xml_filename = file
            elif file.endswith('.pdf'):
                pdf_filename = file

        if not xml_filename or not pdf_filename:
            return {
                'statusCode': 400,
                'body': 'Invalid zip file. Must contain XML and PDF files.'
            }

        # Read the XML file
        #xml_file_content = zip_ref.read(xml_filename).decode('utf-8')
        xml_file_content = zip_ref.read(xml_filename)

        # Read the PDF file and convert to base64
        pdf_file_content = zip_ref.read(pdf_filename)
        pdf_base64 = base64.b64encode(pdf_file_content).decode('utf-8')

        xml_data = add_pdf_to_xml(xml_file_content, pdf_base64)
        
        # validar XML
        
        validation_result = validate_xml(xml_data)
        
        if validation_result is True :

            # Return the resulting XML file with the PDF base64 appended
            return {
                'statusCode': 200,
                'headers' : {
                    'Content-Type': 'text/xml',
                    'Content-Disposition': 'attachment; filename="'+xml_filename+'"'
                }, 
                'body': xml_data
            }
        else :
            # Return the resulting XML file with the PDF base64 appended
            return {
                'statusCode': 400,
                'body': "The resulting XML is invalid" 
            }


def add_pdf_to_xml(xml_content, base64_pdf):
    # Parse the XML content
    root = etree.fromstring(xml_content)

    # Create the dcc:document node
    document_node = etree.SubElement(root, '{https://ptb.de/dcc}document')

    # Create the dcc:fileName node
    file_name_node = etree.SubElement(document_node, '{https://ptb.de/dcc}fileName')
    file_name_node.text = 'name_of_pdf_file.pdf'

    # Create the dcc:mimeType node
    mime_type_node = etree.SubElement(document_node, '{https://ptb.de/dcc}mimeType')
    mime_type_node.text = 'application/pdf'

    # Create the dcc:dataBase64 node
    data_base64_node = etree.SubElement(document_node, '{https://ptb.de/dcc}dataBase64')
    data_base64_node.text = base64_pdf

    # Convert the XML tree back to string
    xml_data = etree.tostring(root, encoding='utf-8').decode('utf-8')

    return xml_data

def validate_xml(xml_content):
# It is necessary to first download do xsd files
# implement later
#     # Load the XML schema
#     schema_url = "https://ptb.de/dcc/v3.2.0/dcc.xsd"
#     schema = etree.XMLSchema(etree.parse(schema_url))

#     # Parse the XML content
#     xml_tree = etree.fromstring(xml_content)

#     # Validate the XML against the schema
#     try:
#         schema.assertValid(xml_tree)
#         return True  # XML is valid
#     except etree.DocumentInvalid as e:
#         return str(e)  # XML is invalid with error message
    return True


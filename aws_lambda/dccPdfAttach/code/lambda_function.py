import json
import base64
import tempfile
import os
from typing import Dict, Any
import pikepdf
from pikepdf import Pdf, Name, String, Array

def attach_xml_to_pdfa3b(pdf_path, xml_path, output_path):
    """
    Attach an XML file to a PDF/A-3b document while maintaining compliance
    
    Args:
        pdf_path (str): Path to the input PDF/A-3b file
        xml_path (str): Path to the XML file to attach
        output_path (str): Path for the output PDF with attachment
    """
    # Open the PDF/A-3b document
    pdf = Pdf.open(pdf_path)
    
    # Read the XML file
    with open(xml_path, 'rb') as f:
        xml_content = f.read()
    
    # Get XML filename
    xml_filename = os.path.basename(xml_path)
    
    # Create the file stream for the XML content
    xml_stream = pdf.make_stream(xml_content)
    
    # Very important: Set the Subtype directly on the stream
    #xml_stream[Name.Type] = Name.EmbeddedFile
    xml_stream[Name.Subtype] = Name("/application/xml")  # Escaped MIME type

    # Make the stream indirect BEFORE putting it into the file spec
    xml_stream = pdf.make_indirect(xml_stream)
    
    # Create a new dictionary for embedded files
    ef_dict = pikepdf.Dictionary()
    ef_dict[Name.F] = xml_stream
    
    # Create a filespec dictionary according to PDF/A-3b requirements
    filespec = pikepdf.Dictionary()
    filespec[Name.Type] = Name.Filespec
    filespec[Name.F] = String(xml_filename)
    filespec[Name.UF] = String(xml_filename)
    filespec[Name.EF] = ef_dict
    filespec[Name.AFRelationship] = Name.Alternative  # Required for PDF/A-3b
    #filespec[Name.Subtype] = String("application/xml")  # Required for PDF/A-3b
    filespec[Name.Subtype] = Name("/application/xml")  # Escaped MIME type here too
    # Make the filespec indirect to ensure proper references
    filespec = pdf.make_indirect(filespec)
    
    # First establish the relationship in the document root
    if Name.AF not in pdf.Root:
        pdf.Root[Name.AF] = Array([filespec])
    else:
        pdf.Root[Name.AF].append(filespec)
    
    # Now add to the Names tree for navigation
    if Name.Names not in pdf.Root:
        pdf.Root[Name.Names] = pikepdf.Dictionary()
    
    if Name.EmbeddedFiles not in pdf.Root.Names:
        embedded_files_dict = pikepdf.Dictionary()
        names_array = Array()
        names_array.append(String(xml_filename))
        names_array.append(filespec)
        embedded_files_dict[Name.Names] = names_array
        pdf.Root.Names[Name.EmbeddedFiles] = embedded_files_dict
    else:
        if hasattr(pdf.Root.Names.EmbeddedFiles, 'Names'):
            names_array = pdf.Root.Names.EmbeddedFiles.Names
            names_array.append(String(xml_filename))
            names_array.append(filespec)
        else:
            names_array = Array()
            names_array.append(String(xml_filename))
            names_array.append(filespec)
            pdf.Root.Names.EmbeddedFiles[Name.Names] = names_array
    
    # Save the modified PDF
    pdf.save(output_path)
 

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for attaching XML to PDF A/3-b files
    
    Expected POST body (multipart/form-data or JSON):
    - pdf_file: base64 encoded PDF file
    - xml_file: base64 encoded XML file
    
    Returns:
    - PDF A/3-b file with attached XML as base64 encoded response
    """
    
    try:
        # Parse the request
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(event['body']).decode('utf-8')
        else:
            body = event.get('body', '')
        
        # Handle different content types
        headers = event.get('headers', {})
        content_type = headers.get('content-type', '').lower()
        
        if 'application/json' in content_type:
            # JSON request
            try:
                data = json.loads(body)
                pdf_base64 = data.get('pdf_file')
                xml_base64 = data.get('xml_file')
            except json.JSONDecodeError:
                return create_error_response(400, "Invalid JSON format")
        
        elif 'multipart/form-data' in content_type:
            # For multipart, you'd need to parse the form data
            # This is a simplified version - you might want to use a library like python-multipart
            return create_error_response(400, "Multipart form data parsing not implemented. Use JSON format.")
        
        else:
            return create_error_response(400, "Unsupported content type. Use application/json")
        
        # Validate input
        if not pdf_base64 or not xml_base64:
            return create_error_response(400, "Both pdf_file and xml_file are required")
        
        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Decode and save input files
            pdf_input_path = os.path.join(temp_dir, "input.pdf")
            xml_input_path = os.path.join(temp_dir, "input.xml")
            pdf_output_path = os.path.join(temp_dir, "output.pdf")
            
            try:
                # Decode base64 files
                pdf_data = base64.b64decode(pdf_base64)
                xml_data = base64.b64decode(xml_base64)
                
                # Write files to temp directory
                with open(pdf_input_path, 'wb') as f:
                    f.write(pdf_data)
                
                with open(xml_input_path, 'wb') as f:
                    f.write(xml_data)
                
            except Exception as e:
                return create_error_response(400, f"Invalid base64 encoding: {str(e)}")
            
            # Call your existing function
            try:
                attach_xml_to_pdfa3b(pdf_input_path, xml_input_path, pdf_output_path)
            except Exception as e:
                return create_error_response(500, f"PDF processing error: {str(e)}")
            
            # Read the output file and encode to base64
            try:
                with open(pdf_output_path, 'rb') as f:
                    output_pdf_data = f.read()
                
                output_base64 = base64.b64encode(output_pdf_data).decode('utf-8')
                
            except Exception as e:
                return create_error_response(500, f"Error reading output file: {str(e)}")
        
        # Return successful response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'success': True,
                'pdf_with_xml': output_base64,
                'message': 'XML successfully attached to PDF A/3-b'
            })
        }
        
    except Exception as e:
        return create_error_response(500, f"Internal server error: {str(e)}")

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }

# Optional: Handle preflight CORS requests
def handle_options():
    """Handle CORS preflight requests"""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': ''
    }

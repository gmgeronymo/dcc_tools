import pikepdf
from pikepdf import Pdf, Name, String, Array
import os

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
    print(f"XML file attached successfully to {output_path}")

# Example usage
attach_xml_to_pdfa3b("input.pdf", "data.xml", "output_with_xml.pdf")

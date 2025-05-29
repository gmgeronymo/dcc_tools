#!/usr/bin/env python3

import requests
import base64
import json
import sys
import os

def send_pdf_xml_to_lambda(pdf_path, xml_path, output_path, lambda_url):
    """
    Send PDF and XML files to Lambda function and save the result
    """
    
    # Check if input files exist
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file '{pdf_path}' not found")
        return False
    
    if not os.path.exists(xml_path):
        print(f"Error: XML file '{xml_path}' not found")
        return False
    
    try:
        print("Reading and encoding files...")
        
        # Read and encode PDF file
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
            pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        # Read and encode XML file
        with open(xml_path, 'rb') as f:
            xml_data = f.read()
            xml_base64 = base64.b64encode(xml_data).decode('utf-8')
        
        print(f"PDF size: {len(pdf_data)} bytes")
        print(f"XML size: {len(xml_data)} bytes")
        print(f"Base64 payload size: ~{len(pdf_base64) + len(xml_base64)} characters")
        
        # Check if payload might be too large for Lambda (6MB limit)
        total_size = len(pdf_base64) + len(xml_base64)
        if total_size > 5000000:  # ~5MB in base64 (accounting for JSON overhead)
            print("Warning: Payload might be too large for Lambda (>5MB)")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                return False
        
        # Prepare payload
        payload = {
            'pdf_file': pdf_base64,
            'xml_file': xml_base64
        }
        
        print("Sending request to Lambda...")
        
        # Send request with timeout
        response = requests.post(
            lambda_url,
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=60  # 60 second timeout
        )
        
        print(f"Response status: {response.status_code}")
        
        # Parse response
        try:
            result = response.json()
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON response")
            print(f"Response text: {response.text[:500]}...")
            return False
        
        if result.get('success'):
            print("Success! Decoding and saving result...")
            
            # Decode and save result
            output_data = base64.b64decode(result['pdf_with_xml'])
            
            with open(output_path, 'wb') as f:
                f.write(output_data)
            
            print(f"Output saved to {output_path}")
            print(f"Output file size: {len(output_data)} bytes")
            return True
            
        else:
            print(f"Lambda function error: {result.get('error', 'Unknown error')}")
            return False
            
    except requests.exceptions.Timeout:
        print("Error: Request timed out (Lambda might need more processing time)")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed - {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    # Configuration
    pdf_path = "input.pdf"
    xml_path = "input.xml"
    output_path = "output.pdf"
    lambda_url = "https://ekrldjl63xexbeyeuo454k6oya0kcwcc.lambda-url.sa-east-1.on.aws/"
    
    # Allow command line arguments
    if len(sys.argv) >= 4:
        pdf_path = sys.argv[1]
        xml_path = sys.argv[2]
        output_path = sys.argv[3]
    
    if len(sys.argv) >= 5:
        lambda_url = sys.argv[4]
    
    print(f"PDF file: {pdf_path}")
    print(f"XML file: {xml_path}")
    print(f"Output file: {output_path}")
    print(f"Lambda URL: {lambda_url}")
    print("-" * 50)
    
    success = send_pdf_xml_to_lambda(pdf_path, xml_path, output_path, lambda_url)
    
    if success:
        print("✅ Operation completed successfully!")
        sys.exit(0)
    else:
        print("❌ Operation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()

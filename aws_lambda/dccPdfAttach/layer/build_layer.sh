#!/bin/bash
set -e

echo "=== Building pikepdf Lambda layer using Amazon's recommended approach ==="

# Create a directory for the layer
mkdir -p /tmp/python

# Install lxml with pip
echo "Installing pikepdf..."
pip install pikepdf multipart -t /tmp/python

# Remove unnecessary files to reduce size
echo "Cleaning up..."
find /tmp/python -name "*.pyc" -delete
find /tmp/python -name "__pycache__" -type d -exec rm -rf {} +

# Test the installation
#echo "Testing installation..."
#cd /tmp
#PYTHONPATH=/tmp python -c "from python.pikepdf import Pdf; print('SUCCESS: pikepdf.Pdf imported successfully')" || echo "FAIL: pikepdf.Pdf import failed"

# Create the layer directory structure
echo "Creating layer structure..."
mkdir -p /tmp/layer/python
cp -r /tmp/python/* /tmp/layer/python/

# Test as Lambda would import it
echo "Testing Lambda-style import..."
cd /tmp
PYTHONPATH=/tmp/layer/python python -c "from pikepdf import Pdf; print('SUCCESS: Lambda-style import works')" || echo "FAIL: Lambda-style import failed"

# Create the zip file
echo "Creating zip file..."
cd /tmp/layer
zip -r9 /build/pikepdf-layer.zip .

echo "Layer zip created at /build/pikepdf-layer.zip"
echo "Install this layer and add the following test function to verify:"

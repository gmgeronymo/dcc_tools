#!/bin/bash
set -e

echo "=== Building Lambda layer for pandas, openpyxl, requests, python-multipart ==="

# Create proper directory structure for Lambda layer
mkdir -p /tmp/python

# Configure pip to use proxy if environment variables are set
if [ -n "$HTTP_PROXY" ] || [ -n "$http_proxy" ]; then
    mkdir -p ~/.pip
    echo "[global]" > ~/.pip/pip.conf
    
    if [ -n "$HTTP_PROXY" ]; then
        echo "proxy = $HTTP_PROXY" >> ~/.pip/pip.conf
    elif [ -n "$http_proxy" ]; then
        echo "proxy = $http_proxy" >> ~/.pip/pip.conf
    fi
    
    if [ -n "$HTTPS_PROXY" ]; then
        echo "https_proxy = $HTTPS_PROXY" >> ~/.pip/pip.conf
    elif [ -n "$https_proxy" ]; then
        echo "https_proxy = $https_proxy" >> ~/.pip/pip.conf
    fi
fi

# Install the required packages
echo "Installing packages..."
pip install pandas openpyxl requests python-multipart -t /tmp/python

# Remove unnecessary files to reduce size
echo "Cleaning up to reduce layer size..."
find /tmp/python -name "*.pyc" -delete
find /tmp/python -name "__pycache__" -type d -exec rm -rf {} +
find /tmp/python -name "*.so" | xargs strip 2>/dev/null || true
find /tmp/python -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true

# Check the size - pandas can be large!
echo "Package sizes:"
du -sh /tmp/python/*/ | sort -hr

# Test imports
echo "Testing imports..."
cd /tmp
PYTHONPATH=/tmp/python python -c "import pandas; import openpyxl; import requests; import multipart; print('SUCCESS: All packages imported successfully')" || echo "WARNING: One or more imports failed"

# Create the layer directory structure
echo "Creating layer structure..."
mkdir -p /tmp/layer
mv /tmp/python /tmp/layer/

# Create the zip file
echo "Creating zip file..."
cd /tmp/layer
zip -r9 /build/xlsx-layer.zip .

echo "Layer zip created at /build/xlsx-layer.zip"
echo "Size of the created layer:"
du -h /build/xlsx-layer.zip

# Copy to the mounted volume
if [ -d "/build" ] && [ "$(ls -A /build)" ]; then
    cp /build/xlsx-layer.zip /build/
    echo "Layer zip copied to mounted volume"
fi

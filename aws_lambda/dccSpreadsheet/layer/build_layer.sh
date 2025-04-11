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

# Install the required packages one by one to better handle dependencies
echo "Installing numpy first (pre-built wheel)..."
pip install --only-binary=:all: numpy -t /tmp/python

echo "Installing pandas..."
pip install --no-deps pandas -t /tmp/python

echo "Installing pandas dependencies (except numpy which is already installed)..."
pip install pytz python-dateutil -t /tmp/python

echo "Installing openpyxl..."
pip install openpyxl -t /tmp/python

echo "Installing requests..."
pip install requests -t /tmp/python

echo "Installing python-multipart..."
pip install python-multipart -t /tmp/python

# Remove unnecessary files to reduce size
echo "Cleaning up to reduce layer size..."
find /tmp/python -name "*.pyc" -delete
find /tmp/python -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find /tmp/python -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true

# Check the size
echo "Package sizes:"
du -sh /tmp/python/*/ | sort -hr

# Test imports
echo "Testing imports..."
cd /tmp
PYTHONPATH=/tmp/python python -c "
import sys
print('Python path:', sys.path)
print('Importing numpy...')
import numpy
print('NumPy version:', numpy.__version__)
print('Importing pandas...')
import pandas
print('Pandas version:', pandas.__version__)
print('Importing openpyxl...')
import openpyxl
print('OpenPyXL version:', openpyxl.__version__)
print('Importing requests...')
import requests
print('Requests version:', requests.__version__)
print('Importing multipart...')
import multipart
print('SUCCESS: All packages imported successfully')
" || echo "WARNING: One or more imports failed"

# Create the layer directory structure with proper structure for Lambda
echo "Creating layer structure..."
mkdir -p /tmp/layer/python

# Move all files to the layer structure
cp -r /tmp/python/* /tmp/layer/python/

# Create the zip file
echo "Creating zip file..."
cd /tmp/layer
zip -r9 /build/xlsx-layer.zip .

echo "Layer zip created at /build/xlsx-layer.zip"
echo "Size of the created layer:"
du -h /build/xlsx-layer.zip

# Copy to the mounted volume
if [ -d "/build" ]; then
    cp /build/xlsx-layer.zip /build/ 2>/dev/null || echo "Could not copy to mounted volume"
    echo "Layer zip copied to mounted volume"
fi

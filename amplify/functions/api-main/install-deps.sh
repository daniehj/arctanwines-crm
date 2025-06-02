#!/bin/bash

# Install Python dependencies for Lambda (Linux x86_64)
pip install \
  --platform linux_x86_64 \
  --target . \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --upgrade \
  -r requirements.txt

# Clean up unnecessary files
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.so" -exec strip {} \; 2>/dev/null || true

echo "Dependencies installed successfully for Lambda runtime" 
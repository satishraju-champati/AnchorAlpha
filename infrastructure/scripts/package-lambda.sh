#!/bin/bash

# AnchorAlpha Lambda Deployment Package Script
# This script creates a deployment package for the Lambda function

set -e

# Default values
ENVIRONMENT="prod"
OUTPUT_DIR="dist"
PACKAGE_NAME="anchor-alpha-lambda"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -o|--output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    -n|--package-name)
      PACKAGE_NAME="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  -e, --environment    Environment (dev/staging/prod) [default: prod]"
      echo "  -o, --output-dir     Output directory [default: dist]"
      echo "  -n, --package-name   Package name [default: anchor-alpha-lambda]"
      echo "  -h, --help           Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "📦 Creating Lambda deployment package"
echo "Environment: $ENVIRONMENT"
echo "Output Directory: $OUTPUT_DIR"
echo "Package Name: $PACKAGE_NAME"
echo ""

cd "$PROJECT_ROOT"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Create temporary build directory
BUILD_DIR=$(mktemp -d)
echo "🏗️  Using build directory: $BUILD_DIR"

# Copy source code
echo "📋 Copying source code..."
cp -r src/AnchorAlpha "$BUILD_DIR/"
cp -r cfg "$BUILD_DIR/"

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt -t "$BUILD_DIR/"

# Remove unnecessary files to reduce package size
echo "🧹 Cleaning up unnecessary files..."
find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
find "$BUILD_DIR" -type f -name ".DS_Store" -delete 2>/dev/null || true

# Remove test files and development dependencies
rm -rf "$BUILD_DIR"/*/test* 2>/dev/null || true
rm -rf "$BUILD_DIR"/*/tests* 2>/dev/null || true
rm -rf "$BUILD_DIR"/pytest* 2>/dev/null || true
rm -rf "$BUILD_DIR"/streamlit* 2>/dev/null || true  # Not needed in Lambda

# Create ZIP package
echo "🗜️  Creating ZIP package..."
cd "$BUILD_DIR"
zip -r "$PROJECT_ROOT/$OUTPUT_DIR/$PACKAGE_NAME-$ENVIRONMENT.zip" . -q

# Get package size
PACKAGE_SIZE=$(du -h "$PROJECT_ROOT/$OUTPUT_DIR/$PACKAGE_NAME-$ENVIRONMENT.zip" | cut -f1)

# Clean up
rm -rf "$BUILD_DIR"

echo "✅ Lambda package created successfully!"
echo "📦 Package: $OUTPUT_DIR/$PACKAGE_NAME-$ENVIRONMENT.zip"
echo "📏 Size: $PACKAGE_SIZE"
echo ""
echo "🚀 Next steps:"
echo "1. Upload the package to your Lambda function:"
echo "   aws lambda update-function-code --function-name anchor-alpha-momentum-processor-$ENVIRONMENT --zip-file fileb://$OUTPUT_DIR/$PACKAGE_NAME-$ENVIRONMENT.zip"
echo ""
echo "2. Or use the AWS Console to upload the ZIP file manually"
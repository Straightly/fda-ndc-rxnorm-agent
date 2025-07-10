#!/bin/bash

# FDA NDC to RxNorm Matching Agent Installation Script

set -e

echo "🚀 Installing FDA NDC to RxNorm Matching Agent..."

# Check if Python 3.8+ is installed
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8 or higher is required. Current version: $python_version"
    exit 1
fi

echo "✓ Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/ndc data/rxnorm data/output data/logs

# Copy environment file
if [ ! -f .env ]; then
    echo "⚙️  Creating environment file..."
    cp env.example .env
    echo "✓ Environment file created. Please review .env and adjust settings if needed."
else
    echo "✓ Environment file already exists."
fi

# Test installation
echo "🧪 Testing installation..."
python test_agent.py

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Download FDA NDC data: python main.py download-ndc"
echo "3. Run the complete pipeline: python main.py run-pipeline"
echo "4. Start the API server: python main.py serve-api"
echo "5. View API documentation: http://localhost:8000/docs"
echo ""
echo "For more information, see README.md" 
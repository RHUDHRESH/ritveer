#!/bin/bash
# KARIGAR Setup Script
# One-command setup for the multi-agent artisan platform

set -e

echo "🚀 KARIGAR Multi-Agent Platform Setup"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version found"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null
echo "✓ Virtual environment activated"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Copy environment file
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.template .env
    echo "⚠️  Remember to edit .env with your API keys!"
else
    echo "✓ .env file already exists"
fi

# Create database
echo ""
echo "Initializing database..."
python -c "from src.karigar.schemas.models import init_db; init_db(); print('✓ Database initialized')"

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data/chroma_db logs
echo "✓ Directories created"

echo ""
echo "========================================"
echo "✅ Setup Complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Edit .env file: nano .env"
echo "2. Start the API: python -m uvicorn src.karigar.api.main:app --reload"
echo "3. Visit documentation: http://localhost:8000/docs"
echo ""
echo "📚 Documentation: See README.md for complete guide"
echo "========================================"

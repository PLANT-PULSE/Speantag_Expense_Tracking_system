#!/bin/bash

echo "🍞 Speantag Bakery Expense Tracking System - Installation"
echo "========================================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip."
    exit 1
fi

echo "✅ pip3 found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📦 Installing required packages..."
pip install -r requirements.txt

echo
echo "✅ Installation completed successfully!"
echo
echo "🚀 To start the application:"
echo "   source venv/bin/activate"
echo "   python run.py"
echo
echo "🌐 Then open your browser and go to: http://localhost:5000"
echo 
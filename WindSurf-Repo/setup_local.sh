#!/bin/bash
# BYOS Command Center - Local Testing Setup Script
echo "🎛️  BYOS Command Center - Local Testing Setup"
echo "=============================================="
echo ""

# Check if Python is available
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt || pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

echo "✅ Python dependencies installed"
echo ""

# Install dashboard dependencies
echo "📦 Installing dashboard dependencies..."
cd apps/dashboard
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dashboard dependencies"
    exit 1
fi

cd ../..
echo "✅ Dashboard dependencies installed"
echo ""

echo "🎉 Setup complete!"
echo ""
echo "To start the system:"
echo "1. Backend: python run_local_test.py"
echo "2. Dashboard: cd apps/dashboard && npm start"
echo ""
echo "Or run both with: run_local.bat (Windows)"
echo ""
echo "URLs:"
echo "- Backend API: http://localhost:8765"
echo "- Dashboard: http://localhost:4321"
echo "- API Docs: http://localhost:8765/docs"

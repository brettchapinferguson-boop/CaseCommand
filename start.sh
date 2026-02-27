#!/bin/bash
# CaseCommand — Start Server
# Usage: bash start.sh

set -e

echo "⚡ CaseCommand Server"
echo ""

# Check .env
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "📋 No .env found. Creating from template..."
        cp .env.example .env
        echo ""
        echo "⚠️  EDIT .env AND ADD YOUR API KEY:"
        echo "   nano .env"
        echo "   (replace sk-ant-your-key-here with your real key)"
        echo ""
        echo "   Get a key at: https://console.anthropic.com/settings/keys"
        echo ""
        exit 1
    else
        echo "❌ No .env or .env.example found"
        exit 1
    fi
fi

# Check key is real
if grep -q "your-key-here" .env 2>/dev/null; then
    echo "❌ API key not set. Edit .env:"
    echo "   nano .env"
    exit 1
fi

# Install deps
echo "📦 Checking dependencies..."
pip install -r requirements.txt -q 2>/dev/null || pip install fastapi uvicorn httpx -q 2>/dev/null || pip install fastapi uvicorn httpx --break-system-packages -q

echo ""
echo "🚀 Starting at http://localhost:3000"
echo "   Press Ctrl+C to stop"
echo ""

python server.py

#!/bin/bash
# SEO Audit Tool Setup Script

echo "🚀 Setting up SEO Audit Tool..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright Chromium browser..."
playwright install chromium

echo "✅ Setup complete!"
echo ""
echo "Usage:"
echo "  CLI:   python seo_auditor.py https://example.com"
echo "  Web:   python app.py"
echo ""

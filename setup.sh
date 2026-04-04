#!/bin/bash
# 🎬 AI Studio Elsewhere - Quick Setup Script
# ============================================
# Run this to set up the complete film director's toolkit

set -e  # Exit on error

echo "🎬 AI Studio Elsewhere - Setup Wizard"
echo "======================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check Python version
echo -e "${BLUE}[1/5] Checking Python installation...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $python_version detected"
echo ""

# Step 2: Create project structure
echo -e "${BLUE}[2/5] Creating project directories...${NC}"
mkdir -p data/{scripts,scenes,concepts,videos,storyboards,exports}
mkdir -p agents
mkdir -p tests
mkdir -p .streamlit
echo "✅ Directory structure created"
echo ""

# Step 3: Create .env template
echo -e "${BLUE}[3/5] Creating .env configuration...${NC}"
cat > .env << 'EOF'
# OpenAI Configuration
OPENAI_API_KEY=sk-...

# DashScope / Wanxiang Configuration
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_REGION=intl
DASHSCOPE_IMAGE_MODEL=wanx-v1

# Runway Video Generation
RUNWAY_API_KEY=...

# Optional: Python path for agents
PYTHON_PATH=./agents
EOF
echo "✅ Created .env template (edit with your API keys)"
echo ""

# Step 4: Install dependencies
echo -e "${BLUE}[4/5] Installing Python dependencies...${NC}"

# Check which package manager to use
if command -v pip3 &> /dev/null; then
    PIP=pip3
else
    PIP=pip
fi

echo "Installing core dependencies..."
$PIP install -q streamlit pillow python-dotenv openai requests pydantic

echo "Installing optional dependencies..."
$PIP install -q pdf2image 2>/dev/null || echo "  ⚠️  pdf2image optional"
$PIP install -q easyocr 2>/dev/null || echo "  ⚠️  easyocr optional"
$PIP install -q paddleocr 2>/dev/null || echo "  ⚠️  paddleocr optional"

# Check for system dependencies on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "Detected macOS - checking for system dependencies..."
    if ! command -v poppler-utils &> /dev/null; then
        echo "Installing poppler (required for PDF processing)..."
        if command -v brew &> /dev/null; then
            brew install poppler -q 2>/dev/null && echo "✅ Poppler installed" || echo "⚠️  Poppler installation failed"
        else
            echo "⚠️  Homebrew not found. Install manually: brew install poppler"
        fi
    else
        echo "✅ Poppler already installed"
    fi
fi

echo "✅ Dependencies installed"
echo ""

# Step 5: Create Streamlit config
echo -e "${BLUE}[5/5] Configuring Streamlit...${NC}"
cat > .streamlit/config.toml << 'EOF'
[theme]
primaryColor = "#FF6B35"
backgroundColor = "#0F1419"
secondaryBackgroundColor = "#1A2332"
textColor = "#FFFFFF"
font = "sans serif"

[client]
showErrorDetails = true

[logger]
level = "info"
EOF
echo "✅ Streamlit configured"
echo ""

# Create sample test script
echo -e "${BLUE}Creating sample test file...${NC}"
cat > tests/test_studio.py << 'EOF'
#!/usr/bin/env python3
"""
Quick test to verify AI Studio Elsewhere setup
"""

import sys
from pathlib import Path

# Test 1: Check imports
print("🔍 Testing imports...")
test_results = []

tests = [
    ("streamlit", "Streamlit UI"),
    ("PIL", "Image processing"),
    ("openai", "OpenAI API"),
    ("pdf2image", "PDF processing [OPTIONAL]"),
    ("easyocr", "EasyOCR [OPTIONAL]"),
]

for module, description in tests:
    try:
        __import__(module)
        print(f"  ✅ {description}")
        test_results.append(True)
    except ImportError:
        if "[OPTIONAL]" in description:
            print(f"  ⚠️  {description} (optional)")
            test_results.append(True)
        else:
            print(f"  ❌ {description}")
            test_results.append(False)

# Test 2: Check environment variables
print("\n🔐 Checking environment variables...")
import os
from dotenv import load_dotenv

load_dotenv()

env_vars = [
    ("OPENAI_API_KEY", "OpenAI"),
    ("DASHSCOPE_API_KEY", "DashScope [OPTIONAL]"),
]

for var, desc in env_vars:
    value = os.getenv(var)
    if value and value != "sk-..." and value != "...":
        print(f"  ✅ {desc} configured")
    elif "[OPTIONAL]" in desc:
        print(f"  ⚠️  {desc} not configured")
    else:
        print(f"  ❌ {desc} not set (edit .env file)")

# Test 3: Check directory structure
print("\n📁 Checking directory structure...")
required_dirs = [
    "data/scripts",
    "data/scenes",
    "data/concepts",
    "data/videos",
    "data/exports",
    "agents",
]

for dir_path in required_dirs:
    if Path(dir_path).exists():
        print(f"  ✅ {dir_path}/")
    else:
        print(f"  ❌ {dir_path}/ (create manually)")

# Summary
print("\n" + "="*50)
if all(test_results):
    print("✅ Setup complete! Run: streamlit run ai_studio_elsewhere.py")
else:
    print("⚠️  Some issues detected. Fix above and retry.")
print("="*50)
EOF

chmod +x tests/test_studio.py

echo "✅ Test script created"
echo ""

# Summary
echo "="*60
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "="*60
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your API keys"
echo "  2. Copy your agent files to agents/ directory"
echo "  3. Run: python tests/test_studio.py (verify setup)"
echo "  4. Run: streamlit run ai_studio_elsewhere.py (start app)"
echo ""
echo "Project structure:"
echo "  ai_studio_elsewhere.py    ← Main app"
echo "  .env                      ← Configuration (edit this!)"
echo "  agents/                   ← Your agent files"
echo "  data/"
echo "    ├── scripts/            ← Uploaded scripts & PDFs"
echo "    ├── scenes/             ← Extracted scenes"
echo "    ├── concepts/           ← Concept images"
echo "    ├── videos/             ← Generated videos"
echo "    └── exports/            ← Final deliverables"
echo "  tests/                    ← Test scripts"
echo ""
echo "Documentation:"
echo "  STUDIO_IMPLEMENTATION_GUIDE.md    ← Complete integration guide"
echo "  AGENT_API_REFERENCE.md            ← Agent signatures"
echo ""
echo "Need help? Check the implementation guide 📖"
echo ""

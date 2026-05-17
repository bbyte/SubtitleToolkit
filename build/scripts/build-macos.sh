#!/bin/bash
# macOS build script for SubtitleToolkit
# This script creates a macOS application bundle using PyInstaller

set -e  # Exit on any error

echo "========================================"
echo "SubtitleToolkit macOS Build Script"
echo "========================================"

# Set script directory and project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"
SPEC_FILE="$BUILD_DIR/subtitletoolkit-macos.spec"

echo "Project root: $PROJECT_ROOT"
echo "Build directory: $BUILD_DIR"
echo "Distribution directory: $DIST_DIR"
echo "Spec file: $SPEC_FILE"

# Change to project root
cd "$PROJECT_ROOT"

# Activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    VENV_PATH="$PROJECT_ROOT/venv"
    if [ -f "$VENV_PATH/bin/activate" ]; then
        echo "Activating virtual environment: $VENV_PATH"
        source "$VENV_PATH/bin/activate"
    else
        echo "WARNING: No virtual environment found at $VENV_PATH"
        echo "         Run: python3 -m venv venv && source venv/bin/activate"
    fi
fi

# Determine Python interpreter (prefer venv python)
PYTHON="${VIRTUAL_ENV:+$VIRTUAL_ENV/bin/python3}"
PYTHON="${PYTHON:-python3}"

# Check if Python is available
if ! command -v "$PYTHON" &> /dev/null; then
    echo "ERROR: Python 3 is not available in PATH"
    echo "Please install Python 3.8+ using Homebrew: brew install python3"
    exit 1
fi

echo "Python: $PYTHON"
"$PYTHON" --version

# Check if PyInstaller is available and install if needed
if ! "$PYTHON" -m PyInstaller --version &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    "$PYTHON" -m pip install pyinstaller
fi

# Install project dependencies
echo ""
echo "Installing project dependencies..."
"$PYTHON" -m pip install -r requirements.txt

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf "$DIST_DIR"
rm -rf "build/SubtitleToolkit"

# Run pre-build validation
echo ""
echo "Running pre-build validation..."
"$PYTHON" -c "import sys; sys.path.insert(0, 'app'); import main; print('✓ Main module imports successfully')"

# Build the application
echo ""
echo "Building macOS application bundle..."
echo "Command: $PYTHON -m PyInstaller --clean '$SPEC_FILE'"
"$PYTHON" -m PyInstaller --clean "$SPEC_FILE"

# Verify the build
APP_PATH="$DIST_DIR/SubtitleToolkit.app"
if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: Application bundle not found at $APP_PATH"
    exit 1
fi

echo ""
echo "Build completed successfully!"
echo "Application bundle location: $APP_PATH"

# Get bundle size
BUNDLE_SIZE=$(du -sh "$APP_PATH" | cut -f1)
echo "Bundle size: $BUNDLE_SIZE"

# Check if we should sign the application
if command -v codesign &> /dev/null; then
    echo ""
    read -p "Do you want to sign the application? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Available signing identities:"
        security find-identity -v -p codesigning
        echo ""
        read -p "Enter signing identity (or press Enter to skip): " SIGN_IDENTITY
        
        if [ ! -z "$SIGN_IDENTITY" ]; then
            echo "Signing application bundle..."
            codesign --force --deep --sign "$SIGN_IDENTITY" \
                     --entitlements "$BUILD_DIR/entitlements.plist" \
                     --options runtime \
                     "$APP_PATH"
            
            echo "Verifying signature..."
            codesign --verify --deep --strict "$APP_PATH"
            spctl -a -v "$APP_PATH"
            echo "✓ Application signed and verified successfully"
        fi
    fi
else
    echo ""
    echo "codesign not available - skipping code signing"
    echo "Install Xcode command line tools to enable code signing"
fi

# Run post-build tests
echo ""
echo "Running post-build smoke test..."
if [ -f "$BUILD_DIR/scripts/test-package-macos.sh" ]; then
    bash "$BUILD_DIR/scripts/test-package-macos.sh"
    
    if [ $? -eq 0 ]; then
        echo "✓ Post-build tests passed"
    else
        echo "WARNING: Post-build tests failed"
        echo "The application bundle was created but may have issues"
    fi
else
    echo "Post-build test script not found, skipping tests"
fi

# Create DMG (optional)
echo ""
read -p "Do you want to create a DMG file? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating DMG file..."
    DMG_PATH="$DIST_DIR/SubtitleToolkit-1.0.0.dmg"
    
    # Remove existing DMG
    rm -f "$DMG_PATH"
    
    # Create DMG
    hdiutil create -volname "SubtitleToolkit" \
                   -srcfolder "$APP_PATH" \
                   -ov -format UDZO \
                   "$DMG_PATH"
    
    echo "DMG created: $DMG_PATH"
    DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
    echo "DMG size: $DMG_SIZE"
fi

echo ""
echo "========================================"
echo "macOS build complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Test the application: open '$APP_PATH'"
echo "2. Notarize for distribution (requires Apple Developer ID)"
echo "3. Create installer DMG or distribute as-is"
echo ""
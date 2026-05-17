#!/bin/bash
# macOS-specific package testing script

set -e

echo "========================================"
echo "SubtitleToolkit macOS Package Test"
echo "========================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"

cd "$PROJECT_ROOT"

# Find the application bundle
APP_PATH="$DIST_DIR/SubtitleToolkit.app"
if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: Application bundle not found at $APP_PATH"
    echo "Please run the build script first"
    exit 1
fi

EXECUTABLE_PATH="$APP_PATH/Contents/MacOS/SubtitleToolkit"
if [ ! -f "$EXECUTABLE_PATH" ]; then
    echo "ERROR: Executable not found at $EXECUTABLE_PATH"
    exit 1
fi

echo "Testing application bundle: $APP_PATH"
echo "Testing executable: $EXECUTABLE_PATH"
echo ""

# Run the test framework
python3 "$SCRIPT_DIR/test-package.py" --executable "$EXECUTABLE_PATH" --verbose

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Package tests failed"
    exit 1
fi

echo ""
echo "✅ Package tests passed"
echo ""

# Additional macOS-specific tests
echo "Running macOS-specific tests..."

# Test bundle structure
echo "Checking bundle structure..."
REQUIRED_PATHS=(
    "$APP_PATH/Contents"
    "$APP_PATH/Contents/MacOS"
    "$APP_PATH/Contents/Resources"
    "$APP_PATH/Contents/Info.plist"
)

for path in "${REQUIRED_PATHS[@]}"; do
    if [ -e "$path" ]; then
        echo "✅ Found: $(basename "$path")"
    else
        echo "❌ Missing: $(basename "$path")"
    fi
done

# Test Info.plist
echo ""
echo "Checking Info.plist..."
if plutil -lint "$APP_PATH/Contents/Info.plist" >/dev/null 2>&1; then
    echo "✅ Info.plist is valid"
    
    # Check bundle identifier
    BUNDLE_ID=$(plutil -extract CFBundleIdentifier raw "$APP_PATH/Contents/Info.plist" 2>/dev/null)
    if [ ! -z "$BUNDLE_ID" ]; then
        echo "✅ Bundle identifier: $BUNDLE_ID"
    else
        echo "⚠️  Bundle identifier not found"
    fi
    
    # Check version
    VERSION=$(plutil -extract CFBundleShortVersionString raw "$APP_PATH/Contents/Info.plist" 2>/dev/null)
    if [ ! -z "$VERSION" ]; then
        echo "✅ Bundle version: $VERSION"
    else
        echo "⚠️  Bundle version not found"
    fi
else
    echo "❌ Info.plist is invalid"
fi

# Test code signature (if present)
echo ""
echo "Checking code signature..."
if codesign -v "$APP_PATH" 2>/dev/null; then
    echo "✅ Code signature is valid"
    
    # Get signing identity
    IDENTITY=$(codesign -dv "$APP_PATH" 2>&1 | grep "Authority=" | head -1 | sed 's/Authority=//' | xargs)
    if [ ! -z "$IDENTITY" ]; then
        echo "✅ Signed by: $IDENTITY"
    fi
else
    echo "ℹ️  Application is not signed (this is okay for local testing)"
fi

# Test Gatekeeper compatibility
echo ""
echo "Checking Gatekeeper compatibility..."
if spctl -a -t exec -vv "$APP_PATH" 2>/dev/null; then
    echo "✅ Gatekeeper will allow execution"
else
    echo "⚠️  Gatekeeper may block execution (sign for distribution)"
fi

# Test file associations
echo ""
echo "Checking file associations..."
if /usr/libexec/PlistBuddy -c "Print CFBundleDocumentTypes" "$APP_PATH/Contents/Info.plist" >/dev/null 2>&1; then
    echo "✅ File associations configured"
else
    echo "ℹ️  No file associations configured"
fi

# Test high DPI support
echo ""
echo "Checking high DPI support..."
HIGH_DPI=$(plutil -extract NSHighResolutionCapable raw "$APP_PATH/Contents/Info.plist" 2>/dev/null)
if [ "$HIGH_DPI" = "true" ]; then
    echo "✅ High DPI support enabled"
else
    echo "⚠️  High DPI support not enabled"
fi

# Test minimum macOS version
echo ""
echo "Checking minimum macOS version..."
MIN_VERSION=$(plutil -extract LSMinimumSystemVersion raw "$APP_PATH/Contents/Info.plist" 2>/dev/null)
if [ ! -z "$MIN_VERSION" ]; then
    echo "✅ Minimum macOS version: $MIN_VERSION"
    
    # Compare with current version
    CURRENT_VERSION=$(sw_vers -productVersion)
    if [ "$(printf '%s\n' "$MIN_VERSION" "$CURRENT_VERSION" | sort -V | head -n1)" = "$MIN_VERSION" ]; then
        echo "✅ Compatible with current macOS version: $CURRENT_VERSION"
    else
        echo "❌ Incompatible with current macOS version: $CURRENT_VERSION"
    fi
else
    echo "⚠️  Minimum macOS version not specified"
fi

# Test launch services registration
echo ""
echo "Testing Launch Services registration..."
if /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -dump | grep -q "SubtitleToolkit"; then
    echo "✅ Application is registered with Launch Services"
else
    echo "ℹ️  Application not yet registered with Launch Services (normal for first run)"
fi

echo ""
echo "========================================"
echo "macOS package testing complete"
echo "========================================"
echo ""
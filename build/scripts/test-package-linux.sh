#!/bin/bash
# Linux-specific package testing script

set -e

echo "========================================"
echo "SubtitleToolkit Linux Package Test"  
echo "========================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"

cd "$PROJECT_ROOT"

# Find the executable (directory or AppImage)
EXECUTABLE_PATH=""
APP_DIR="$DIST_DIR/SubtitleToolkit"
APPIMAGE_PATH="$DIST_DIR/SubtitleToolkit-1.0.0-x86_64.AppImage"

if [ -f "$APP_DIR/SubtitleToolkit" ]; then
    EXECUTABLE_PATH="$APP_DIR/SubtitleToolkit"
    PACKAGE_TYPE="directory"
    echo "Testing directory package: $APP_DIR"
elif [ -f "$APPIMAGE_PATH" ]; then
    EXECUTABLE_PATH="$APPIMAGE_PATH" 
    PACKAGE_TYPE="appimage"
    echo "Testing AppImage: $APPIMAGE_PATH"
else
    echo "ERROR: No executable found"
    echo "  Looked for: $APP_DIR/SubtitleToolkit"
    echo "  Looked for: $APPIMAGE_PATH"
    echo "Please run the build script first"
    exit 1
fi

echo "Testing executable: $EXECUTABLE_PATH"
echo "Package type: $PACKAGE_TYPE"
echo ""

# Get Linux distribution info
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "Distribution: $NAME $VERSION"
else
    echo "Distribution: Unknown"
fi
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

# Additional Linux-specific tests
echo "Running Linux-specific tests..."

# Test executable permissions
echo "Checking file permissions..."
if [ -x "$EXECUTABLE_PATH" ]; then
    echo "✅ Executable has correct permissions"
    PERMS=$(stat -c "%a" "$EXECUTABLE_PATH")
    echo "✅ Permission bits: $PERMS"
else
    echo "❌ Executable lacks execute permissions"
fi

# Test dynamic library dependencies
echo ""
echo "Checking dynamic library dependencies..."
if command -v ldd &> /dev/null; then
    echo "Running ldd analysis..."
    if ldd "$EXECUTABLE_PATH" | grep -q "not found"; then
        echo "❌ Missing dynamic library dependencies:"
        ldd "$EXECUTABLE_PATH" | grep "not found"
    else
        echo "✅ All dynamic library dependencies satisfied"
        LIB_COUNT=$(ldd "$EXECUTABLE_PATH" | wc -l)
        echo "✅ Found $LIB_COUNT dynamic library dependencies"
    fi
else
    echo "⚠️  ldd not available, cannot check dependencies"
fi

# Test GLIBC compatibility
echo ""
echo "Checking GLIBC compatibility..."
if command -v objdump &> /dev/null; then
    GLIBC_VERSION=$(objdump -T "$EXECUTABLE_PATH" 2>/dev/null | grep GLIBC | sed 's/.*GLIBC_//' | sort -V | tail -n1 | cut -d' ' -f1)
    if [ ! -z "$GLIBC_VERSION" ]; then
        echo "✅ Requires GLIBC: $GLIBC_VERSION"
        
        # Check system GLIBC version
        if command -v ldd &> /dev/null; then
            SYSTEM_GLIBC=$(ldd --version | head -n1 | grep -o '[0-9]\+\.[0-9]\+')
            if [ ! -z "$SYSTEM_GLIBC" ]; then
                echo "✅ System GLIBC: $SYSTEM_GLIBC"
                if [ "$(printf '%s\n' "$GLIBC_VERSION" "$SYSTEM_GLIBC" | sort -V | head -n1)" = "$GLIBC_VERSION" ]; then
                    echo "✅ GLIBC compatibility: OK"
                else
                    echo "❌ GLIBC compatibility: System version too old"
                fi
            fi
        fi
    fi
else
    echo "⚠️  objdump not available, cannot check GLIBC version"
fi

if [ "$PACKAGE_TYPE" = "directory" ]; then
    # Test directory package structure
    echo ""
    echo "Checking directory package structure..."
    
    if [ -d "$APP_DIR" ]; then
        echo "✅ Application directory exists"
        DIR_SIZE=$(du -sh "$APP_DIR" | cut -f1)
        echo "✅ Directory size: $DIR_SIZE"
        
        # Check for required files
        if [ -f "$APP_DIR/SubtitleToolkit" ]; then
            echo "✅ Main executable found"
        else
            echo "❌ Main executable missing"
        fi
        
        # Check for bundled libraries
        if [ -d "$APP_DIR/_internal" ]; then
            echo "✅ Internal libraries directory found"
            LIB_COUNT=$(find "$APP_DIR/_internal" -name "*.so*" | wc -l)
            echo "✅ Bundled libraries: $LIB_COUNT"
        else
            echo "⚠️  Internal libraries directory not found"
        fi
    fi
    
elif [ "$PACKAGE_TYPE" = "appimage" ]; then
    # Test AppImage specific features
    echo ""
    echo "Checking AppImage features..."
    
    # Check if AppImage has desktop integration
    if "$EXECUTABLE_PATH" --appimage-help &>/dev/null; then
        echo "✅ AppImage runtime available"
        
        # Test AppImage mount
        if "$EXECUTABLE_PATH" --appimage-mount &>/dev/null; then
            echo "✅ AppImage can be mounted"
        else
            echo "⚠️  AppImage mount test failed"
        fi
        
        # Test AppImage extract
        if "$EXECUTABLE_PATH" --appimage-extract-and-run --version &>/dev/null; then
            echo "✅ AppImage extract-and-run works"
        else
            echo "⚠️  AppImage extract-and-run failed"
        fi
    else
        echo "⚠️  AppImage runtime features not available"
    fi
    
    # Check AppImage signature (if available)
    if command -v gpg &> /dev/null; then
        echo ""
        echo "Checking AppImage signature..."
        if "$EXECUTABLE_PATH" --appimage-signature 2>/dev/null | grep -q "BEGIN PGP"; then
            echo "✅ AppImage is signed"
        else
            echo "ℹ️  AppImage is not signed (this is okay)"
        fi
    fi
fi

# Test desktop integration files
echo ""
echo "Checking desktop integration..."
if [ -f "$PROJECT_ROOT/build/linux/subtitletoolkit.desktop" ]; then
    echo "✅ Desktop file available"
    
    # Validate desktop file
    if command -v desktop-file-validate &> /dev/null; then
        if desktop-file-validate "$PROJECT_ROOT/build/linux/subtitletoolkit.desktop" 2>/dev/null; then
            echo "✅ Desktop file is valid"
        else
            echo "⚠️  Desktop file validation failed"
        fi
    else
        echo "ℹ️  desktop-file-validate not available"
    fi
else
    echo "⚠️  Desktop file not found"
fi

# Test XDG compliance
echo ""
echo "Checking XDG compliance..."
if [ ! -z "$XDG_DATA_HOME" ]; then
    echo "✅ XDG_DATA_HOME set: $XDG_DATA_HOME"
else
    echo "ℹ️  XDG_DATA_HOME not set (will use default)"
fi

if [ ! -z "$XDG_CONFIG_HOME" ]; then
    echo "✅ XDG_CONFIG_HOME set: $XDG_CONFIG_HOME"
else
    echo "ℹ️  XDG_CONFIG_HOME not set (will use default)"
fi

# Test GUI environment
echo ""
echo "Checking GUI environment..."
if [ ! -z "$DISPLAY" ]; then
    echo "✅ X11 DISPLAY set: $DISPLAY"
elif [ ! -z "$WAYLAND_DISPLAY" ]; then
    echo "✅ Wayland display set: $WAYLAND_DISPLAY"
else
    echo "⚠️  No GUI environment detected"
fi

# Test Qt platform plugins
echo ""
echo "Checking Qt platform support..."
if [ "$PACKAGE_TYPE" = "directory" ] && [ -d "$APP_DIR/_internal" ]; then
    QT_PLUGINS=$(find "$APP_DIR/_internal" -name "*platforms*" -type d 2>/dev/null | head -1)
    if [ ! -z "$QT_PLUGINS" ]; then
        echo "✅ Qt platform plugins found"
        PLUGIN_COUNT=$(find "$QT_PLUGINS" -name "*.so" | wc -l)
        echo "✅ Platform plugins: $PLUGIN_COUNT"
    else
        echo "⚠️  Qt platform plugins not found"
    fi
fi

echo ""
echo "========================================"
echo "Linux package testing complete"
echo "========================================"
echo ""
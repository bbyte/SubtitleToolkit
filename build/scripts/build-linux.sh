#!/bin/bash
# Linux build script for SubtitleToolkit
# This script creates a Linux standalone executable and optionally an AppImage

set -e  # Exit on any error

echo "========================================"
echo "SubtitleToolkit Linux Build Script"
echo "========================================"

# Set script directory and project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"
SPEC_FILE="$BUILD_DIR/subtitletoolkit-linux.spec"

echo "Project root: $PROJECT_ROOT"
echo "Build directory: $BUILD_DIR"
echo "Distribution directory: $DIST_DIR"
echo "Spec file: $SPEC_FILE"

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$NAME
    VERSION=$VERSION_ID
else
    DISTRO="Unknown"
    VERSION="Unknown"
fi

echo "Linux distribution: $DISTRO $VERSION"

# Change to project root
cd "$PROJECT_ROOT"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not available in PATH"
    echo "Please install Python 3.8+ using your distribution's package manager:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  CentOS/RHEL/Fedora: sudo dnf install python3 python3-pip"
    echo "  Arch: sudo pacman -S python python-pip"
    exit 1
fi

echo "Python version:"
python3 --version

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "ERROR: pip3 is not available"
    echo "Please install pip using your distribution's package manager"
    exit 1
fi

# Check if PyInstaller is available
if ! pip3 show pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip3 install --user pyinstaller
    
    # Add user bin to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        export PATH="$HOME/.local/bin:$PATH"
        echo "Added $HOME/.local/bin to PATH"
    fi
fi

# Install system dependencies
echo ""
echo "Checking system dependencies..."

# Check for required system packages
MISSING_PACKAGES=()

# Qt dependencies
if ! ldconfig -p | grep -q libQt6; then
    if ! ldconfig -p | grep -q libqt6; then
        MISSING_PACKAGES+=("qt6-base-dev" "qt6-svg-dev")
    fi
fi

# Development tools
if ! command -v gcc &> /dev/null; then
    MISSING_PACKAGES+=("build-essential")
fi

if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo "Missing system packages: ${MISSING_PACKAGES[*]}"
    echo "Please install them using your package manager:"
    
    # Provide distribution-specific installation commands
    case "$DISTRO" in
        *Ubuntu*|*Debian*)
            echo "  sudo apt update && sudo apt install ${MISSING_PACKAGES[*]}"
            ;;
        *CentOS*|*Red\ Hat*|*Fedora*)
            echo "  sudo dnf install ${MISSING_PACKAGES[*]}"
            ;;
        *Arch*)
            echo "  sudo pacman -S ${MISSING_PACKAGES[*]}"
            ;;
        *)
            echo "  Use your distribution's package manager to install the above packages"
            ;;
    esac
    
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install project dependencies
echo ""
echo "Installing project dependencies..."
pip3 install --user -r requirements.txt

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf "$DIST_DIR"
rm -rf "build/SubtitleToolkit"

# Run pre-build validation
echo ""
echo "Running pre-build validation..."
python3 -c "import sys; sys.path.insert(0, 'app'); import main; print('✓ Main module imports successfully')"

# Build the application
echo ""
echo "Building Linux executable..."
echo "Command: pyinstaller --clean '$SPEC_FILE'"
pyinstaller --clean "$SPEC_FILE"

# Verify the build
APP_PATH="$DIST_DIR/SubtitleToolkit"
if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: Application directory not found at $APP_PATH"
    exit 1
fi

EXECUTABLE_PATH="$APP_PATH/SubtitleToolkit"
if [ ! -f "$EXECUTABLE_PATH" ]; then
    echo "ERROR: Executable not found at $EXECUTABLE_PATH"
    exit 1
fi

echo ""
echo "Build completed successfully!"
echo "Application directory: $APP_PATH"
echo "Executable: $EXECUTABLE_PATH"

# Get application size
APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
echo "Application size: $APP_SIZE"

# Make executable
chmod +x "$EXECUTABLE_PATH"

# Run post-build tests
echo ""
echo "Running post-build smoke test..."
if [ -f "$BUILD_DIR/scripts/test-package-linux.sh" ]; then
    bash "$BUILD_DIR/scripts/test-package-linux.sh"
    
    if [ $? -eq 0 ]; then
        echo "✓ Post-build tests passed"
    else
        echo "WARNING: Post-build tests failed"
        echo "The executable was created but may have issues"
    fi
else
    echo "Post-build test script not found, skipping tests"
fi

# Create AppImage (optional)
echo ""
read -p "Do you want to create an AppImage? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Setting up AppImage creation..."
    
    # Check if appimagetool is available
    if ! command -v appimagetool &> /dev/null; then
        echo "Downloading appimagetool..."
        APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        curl -L "$APPIMAGETOOL_URL" -o /tmp/appimagetool
        chmod +x /tmp/appimagetool
        APPIMAGETOOL="/tmp/appimagetool"
    else
        APPIMAGETOOL="appimagetool"
    fi
    
    # Create AppDir structure
    APPDIR="$DIST_DIR/SubtitleToolkit.AppDir"
    mkdir -p "$APPDIR/usr/bin"
    mkdir -p "$APPDIR/usr/lib"
    mkdir -p "$APPDIR/usr/share/applications"
    mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
    
    # Copy application
    cp -r "$APP_PATH"/* "$APPDIR/usr/bin/"
    
    # Copy desktop file
    if [ -f "$BUILD_DIR/linux/subtitletoolkit.desktop" ]; then
        cp "$BUILD_DIR/linux/subtitletoolkit.desktop" "$APPDIR/"
        cp "$BUILD_DIR/linux/subtitletoolkit.desktop" "$APPDIR/usr/share/applications/"
    fi
    
    # Copy icon if available
    if [ -f "app/resources/icon.png" ]; then
        cp "app/resources/icon.png" "$APPDIR/subtitletoolkit.png"
        cp "app/resources/icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/subtitletoolkit.png"
    fi
    
    # Create AppRun script
    cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS}"
exec "${HERE}/usr/bin/SubtitleToolkit" "$@"
EOF
    chmod +x "$APPDIR/AppRun"
    
    # Create AppImage
    echo "Creating AppImage..."
    "$APPIMAGETOOL" "$APPDIR" "$DIST_DIR/SubtitleToolkit-1.0.0-x86_64.AppImage"
    
    if [ $? -eq 0 ]; then
        APPIMAGE_PATH="$DIST_DIR/SubtitleToolkit-1.0.0-x86_64.AppImage"
        echo "AppImage created: $APPIMAGE_PATH"
        APPIMAGE_SIZE=$(du -sh "$APPIMAGE_PATH" | cut -f1)
        echo "AppImage size: $APPIMAGE_SIZE"
        
        # Make AppImage executable
        chmod +x "$APPIMAGE_PATH"
    else
        echo "ERROR: AppImage creation failed"
    fi
    
    # Clean up temporary appimagetool
    if [ "$APPIMAGETOOL" = "/tmp/appimagetool" ]; then
        rm -f /tmp/appimagetool
    fi
fi

# Create tarball distribution
echo ""
read -p "Do you want to create a tarball distribution? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating tarball distribution..."
    TARBALL_PATH="$DIST_DIR/SubtitleToolkit-1.0.0-linux.tar.gz"
    
    cd "$DIST_DIR"
    tar -czf "SubtitleToolkit-1.0.0-linux.tar.gz" SubtitleToolkit/
    cd "$PROJECT_ROOT"
    
    echo "Tarball created: $TARBALL_PATH"
    TARBALL_SIZE=$(du -sh "$TARBALL_PATH" | cut -f1)
    echo "Tarball size: $TARBALL_SIZE"
fi

echo ""
echo "========================================"
echo "Linux build complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Test the executable: '$EXECUTABLE_PATH'"
if [ -f "$DIST_DIR/SubtitleToolkit-1.0.0-x86_64.AppImage" ]; then
    echo "2. Test the AppImage: '$DIST_DIR/SubtitleToolkit-1.0.0-x86_64.AppImage'"
fi
echo "3. Distribute the application directory or AppImage"
echo "4. Consider creating distribution-specific packages (deb, rpm, etc.)"
echo ""
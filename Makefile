# SubtitleToolkit Makefile
# Cross-platform build automation

.PHONY: help build test clean package release install-deps

# Default target
help:
	@echo "SubtitleToolkit Build System"
	@echo "============================="
	@echo ""
	@echo "Available targets:"
	@echo "  help         - Show this help message"
	@echo "  install-deps - Install build dependencies"
	@echo "  build        - Build for current platform"  
	@echo "  test         - Test the built package"
	@echo "  clean        - Clean build artifacts"
	@echo "  package      - Create distribution package"
	@echo "  release      - Create complete release (requires version)"
	@echo ""
	@echo "Examples:"
	@echo "  make build"
	@echo "  make release VERSION=1.0.0"
	@echo "  make package"

# Install build dependencies
install-deps:
	@echo "Installing build dependencies..."
	pip install pyinstaller
	pip install -r requirements.txt

# Build for current platform
build:
	@echo "Building SubtitleToolkit for current platform..."
	python build/scripts/build.py

# Test the built package
test:
	@echo "Testing built package..."
	python build/scripts/test-package.py

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf dist/
	rm -rf build/SubtitleToolkit/
	rm -rf *.spec.bak
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Create distribution package
package: build
	@echo "Creating distribution package..."
	@if [ "$(shell uname)" = "Darwin" ]; then \
		python build/installers/create_dmg.py; \
	else \
		echo "Package creation for this platform not automated"; \
	fi

# Create complete release (requires VERSION parameter)
release:
ifndef VERSION
	@echo "Error: VERSION parameter required"
	@echo "Usage: make release VERSION=1.0.0"
	@exit 1
endif
	@echo "Creating release $(VERSION)..."
	python build/scripts/release.py $(VERSION)

# Platform-specific targets (for reference)
build-windows:
	build/scripts/build-windows.bat

build-macos:
	bash build/scripts/build-macos.sh

build-linux:
	bash build/scripts/build-linux.sh
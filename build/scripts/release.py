#!/usr/bin/env python3
"""
Release automation script for SubtitleToolkit

This script automates the entire release process including:
- Version management
- Multi-platform builds
- Testing
- Package creation
- Release artifact preparation
"""

import sys
import os
import subprocess
import tempfile
import shutil
import json
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse


class ReleaseManager:
    """Manages the release process for SubtitleToolkit."""
    
    def __init__(self, version: str, build_all: bool = True):
        self.version = version
        self.build_all = build_all
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent.parent
        self.build_dir = self.project_root / 'build'
        self.dist_dir = self.project_root / 'dist'
        self.release_dir = self.dist_dir / 'release' / version
        
        # Platform detection
        import platform
        self.current_platform = platform.system().lower()
        
        # Supported platforms
        self.platforms = ['windows', 'macos', 'linux'] if build_all else [self.current_platform]
        
        # Release artifacts
        self.artifacts: Dict[str, List[Path]] = {
            'windows': [],
            'macos': [],
            'linux': [],
            'source': []
        }
    
    def validate_version(self) -> bool:
        """Validate version format."""
        import re
        # Support semantic versioning (x.y.z or x.y.z-alpha.1, etc.)
        pattern = r'^\\d+\\.\\d+\\.\\d+(-[a-zA-Z0-9.-]+)?$'
        
        if not re.match(pattern, self.version):
            print(f"❌ Invalid version format: {self.version}")
            print("   Use semantic versioning (e.g., 1.0.0, 1.0.0-beta.1)")
            return False
        
        print(f"✅ Version format valid: {self.version}")
        return True
    
    def check_git_status(self) -> bool:
        """Check if git working directory is clean."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("❌ Git not available or not in a git repository")
                return False
            
            if result.stdout.strip():
                print("❌ Git working directory is not clean:")
                print(result.stdout)
                print("   Commit or stash changes before creating a release")
                return False
            
            print("✅ Git working directory is clean")
            return True
            
        except Exception as e:
            print(f"❌ Error checking git status: {e}")
            return False
    
    def update_version_files(self) -> bool:
        """Update version strings in project files."""
        try:
            version_files = [
                (self.project_root / 'app' / 'main.py', 'setApplicationVersion'),
                (self.build_dir / 'version_info.txt', 'filevers='),
                (self.build_dir / 'subtitletoolkit-windows.spec', 'app_version ='),
                (self.build_dir / 'subtitletoolkit-macos.spec', 'app_version ='),
                (self.build_dir / 'subtitletoolkit-linux.spec', 'app_version ='),
            ]
            
            updated_files = []
            
            for file_path, search_string in version_files:
                if file_path.exists():
                    if self._update_version_in_file(file_path, search_string):
                        updated_files.append(file_path)
            
            if updated_files:
                print(f"✅ Updated version to {self.version} in {len(updated_files)} files")
                return True
            else:
                print("⚠️  No version files updated")
                return True
                
        except Exception as e:
            print(f"❌ Error updating version files: {e}")
            return False
    
    def _update_version_in_file(self, file_path: Path, search_string: str) -> bool:
        """Update version string in a specific file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\\n')
            updated = False
            
            for i, line in enumerate(lines):
                if search_string in line:
                    if 'filevers=' in search_string:
                        # Handle version_info.txt format
                        version_tuple = tuple(map(int, self.version.split('.')[0:3]))
                        lines[i] = f"    filevers={version_tuple + (0,)[:4]},"
                    elif 'setApplicationVersion' in search_string:
                        # Handle main.py format
                        lines[i] = f'        self.setApplicationVersion("{self.version}")'
                    else:
                        # Handle spec file format
                        lines[i] = f'app_version = "{self.version}"'
                    updated = True
                    break
            
            if updated:
                file_path.write_text('\\n'.join(lines), encoding='utf-8')
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error updating {file_path}: {e}")
            return False
    
    def prepare_release_directory(self) -> bool:
        """Prepare the release directory structure."""
        try:
            # Remove existing release directory
            if self.release_dir.exists():
                shutil.rmtree(self.release_dir)
            
            # Create release directory structure
            self.release_dir.mkdir(parents=True, exist_ok=True)
            (self.release_dir / 'windows').mkdir(exist_ok=True)
            (self.release_dir / 'macos').mkdir(exist_ok=True)
            (self.release_dir / 'linux').mkdir(exist_ok=True)
            (self.release_dir / 'source').mkdir(exist_ok=True)
            
            print(f"✅ Prepared release directory: {self.release_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Error preparing release directory: {e}")
            return False
    
    def build_platform(self, platform: str) -> bool:
        """Build for a specific platform."""
        print(f"\\n{'='*60}")
        print(f"Building for {platform.upper()}")
        print(f"{'='*60}")
        
        try:
            # Run platform-specific build
            if platform == 'windows':
                script_path = self.script_dir / 'build-windows.bat'
                if self.current_platform != 'windows':
                    print(f"⚠️  Cannot build Windows package on {self.current_platform}")
                    return False
                result = subprocess.run([str(script_path)], shell=True)
                
            elif platform == 'macos':
                script_path = self.script_dir / 'build-macos.sh'
                if self.current_platform != 'darwin':
                    print(f"⚠️  Cannot build macOS package on {self.current_platform}")
                    return False
                result = subprocess.run(['bash', str(script_path)])
                
            elif platform == 'linux':
                script_path = self.script_dir / 'build-linux.sh'
                if self.current_platform != 'linux':
                    print(f"⚠️  Cannot build Linux package on {self.current_platform}")
                    return False
                result = subprocess.run(['bash', str(script_path)])
            
            else:
                print(f"❌ Unsupported platform: {platform}")
                return False
            
            if result.returncode != 0:
                print(f"❌ Build failed for {platform}")
                return False
            
            print(f"✅ Build completed for {platform}")
            return True
            
        except Exception as e:
            print(f"❌ Error building {platform}: {e}")
            return False
    
    def test_platform(self, platform: str) -> bool:
        """Test the built package for a platform."""
        print(f"Testing {platform} package...")
        
        try:
            test_script = self.script_dir / 'test-package.py'
            result = subprocess.run([
                sys.executable, str(test_script),
                '--json-output', str(self.release_dir / f'{platform}_test_results.json')
            ])
            
            if result.returncode != 0:
                print(f"❌ Tests failed for {platform}")
                return False
            
            print(f"✅ Tests passed for {platform}")
            return True
            
        except Exception as e:
            print(f"❌ Error testing {platform}: {e}")
            return False
    
    def package_artifacts(self, platform: str) -> bool:
        """Package the built artifacts for a platform."""
        try:
            platform_dist = self.dist_dir
            platform_release = self.release_dir / platform
            
            if platform == 'windows':
                # Package Windows executable
                exe_path = platform_dist / 'SubtitleToolkit.exe'
                if exe_path.exists():
                    # Copy executable
                    dst_exe = platform_release / f'SubtitleToolkit-{self.version}-Windows.exe'
                    shutil.copy2(exe_path, dst_exe)
                    self.artifacts['windows'].append(dst_exe)
                    
                    # Create ZIP archive
                    zip_path = platform_release / f'SubtitleToolkit-{self.version}-Windows.zip'
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        zf.write(exe_path, 'SubtitleToolkit.exe')
                        # Add documentation
                        readme_path = self.project_root / 'README.md'
                        if readme_path.exists():
                            zf.write(readme_path, 'README.txt')
                    
                    self.artifacts['windows'].append(zip_path)
                    print(f"✅ Packaged Windows artifacts")
            
            elif platform == 'macos':
                # Package macOS app bundle
                app_path = platform_dist / 'SubtitleToolkit.app'
                if app_path.exists():
                    # Create DMG
                    dmg_creator = self.script_dir.parent / 'installers' / 'create_dmg.py'
                    dmg_path = platform_release / f'SubtitleToolkit-{self.version}.dmg'
                    
                    result = subprocess.run([
                        sys.executable, str(dmg_creator),
                        '--app', str(app_path),
                        '--output', str(dmg_path),
                        '--version', self.version
                    ])
                    
                    if result.returncode == 0 and dmg_path.exists():
                        self.artifacts['macos'].append(dmg_path)
                        print(f"✅ Packaged macOS DMG")
                    
                    # Also create tar.gz for direct distribution
                    tar_path = platform_release / f'SubtitleToolkit-{self.version}-macOS.tar.gz'
                    with tarfile.open(tar_path, 'w:gz') as tf:
                        tf.add(app_path, arcname='SubtitleToolkit.app')
                    
                    self.artifacts['macos'].append(tar_path)
            
            elif platform == 'linux':
                # Package Linux artifacts
                app_dir = platform_dist / 'SubtitleToolkit'
                appimage_path = platform_dist / f'SubtitleToolkit-{self.version}-x86_64.AppImage'
                
                if app_dir.exists():
                    # Create tar.gz
                    tar_path = platform_release / f'SubtitleToolkit-{self.version}-Linux.tar.gz'
                    with tarfile.open(tar_path, 'w:gz') as tf:
                        tf.add(app_dir, arcname='SubtitleToolkit')
                    
                    self.artifacts['linux'].append(tar_path)
                
                if appimage_path.exists():
                    # Copy AppImage
                    dst_appimage = platform_release / f'SubtitleToolkit-{self.version}-x86_64.AppImage'
                    shutil.copy2(appimage_path, dst_appimage)
                    self.artifacts['linux'].append(dst_appimage)
                
                print(f"✅ Packaged Linux artifacts")
            
            return True
            
        except Exception as e:
            print(f"❌ Error packaging {platform} artifacts: {e}")
            return False
    
    def create_source_package(self) -> bool:
        """Create source code package."""
        try:
            source_dir = self.release_dir / 'source'
            
            # Create source archive using git
            git_archive_path = source_dir / f'SubtitleToolkit-{self.version}-source.tar.gz'
            
            result = subprocess.run([
                'git', 'archive',
                '--format=tar.gz',
                f'--output={git_archive_path}',
                '--prefix=f'SubtitleToolkit-{self.version}/',
                'HEAD'
            ], cwd=self.project_root)
            
            if result.returncode == 0 and git_archive_path.exists():
                self.artifacts['source'].append(git_archive_path)
                print(f"✅ Created source package")
                return True
            else:
                print(f"❌ Failed to create source package")
                return False
                
        except Exception as e:
            print(f"❌ Error creating source package: {e}")
            return False
    
    def generate_release_notes(self) -> bool:
        """Generate release notes."""
        try:
            release_notes_path = self.release_dir / 'RELEASE_NOTES.md'
            
            # Get git log since last tag
            try:
                result = subprocess.run([
                    'git', 'describe', '--tags', '--abbrev=0'
                ], cwd=self.project_root, capture_output=True, text=True)
                
                if result.returncode == 0:
                    last_tag = result.stdout.strip()
                    log_result = subprocess.run([
                        'git', 'log', f'{last_tag}..HEAD',
                        '--pretty=format:- %s (%h)', '--no-merges'
                    ], cwd=self.project_root, capture_output=True, text=True)
                    
                    changes = log_result.stdout.strip()
                else:
                    changes = "Initial release"
                    
            except Exception:
                changes = "Release notes not available"
            
            # Generate release notes content
            notes_content = f"""# SubtitleToolkit {self.version}

Released: {datetime.now().strftime('%Y-%m-%d')}

## Changes

{changes if changes else "- Initial release"}

## Downloads

### Windows
"""
            
            # Add download links for each artifact
            for platform, artifacts in self.artifacts.items():
                if artifacts:
                    notes_content += f"\\n### {platform.title()}\\n"
                    for artifact in artifacts:
                        size_mb = artifact.stat().st_size / (1024 * 1024)
                        notes_content += f"- [{artifact.name}](./{platform}/{artifact.name}) ({size_mb:.1f} MB)\\n"
            
            notes_content += f"""
## Installation

### Windows
1. Download the `.exe` file or extract the `.zip` archive
2. Run `SubtitleToolkit.exe`
3. The application will guide you through dependency setup

### macOS
1. Download the `.dmg` file
2. Open the DMG and drag SubtitleToolkit to Applications
3. Install required dependencies (ffmpeg) via Homebrew if needed

### Linux
1. Download the `.AppImage` file or extract the `.tar.gz` archive
2. Make the AppImage executable: `chmod +x SubtitleToolkit-*.AppImage`
3. Install required dependencies via your package manager

## Requirements

- **System Dependencies**: ffmpeg (for subtitle extraction)
- **API Keys**: OpenAI or Anthropic API keys (for translation)
- **Python**: Not required for binary distributions

## Support

- Report issues: [GitHub Issues](https://github.com/subtitletoolkit/subtitletoolkit/issues)
- Documentation: [GitHub Wiki](https://github.com/subtitletoolkit/subtitletoolkit/wiki)
"""
            
            release_notes_path.write_text(notes_content, encoding='utf-8')
            print(f"✅ Generated release notes: {release_notes_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating release notes: {e}")
            return False
    
    def create_checksums(self) -> bool:
        """Create checksum files for all artifacts."""
        try:
            import hashlib
            
            checksums_path = self.release_dir / 'checksums.txt'
            checksums = []
            
            # Calculate checksums for all artifacts
            for platform, artifacts in self.artifacts.items():
                for artifact in artifacts:
                    if artifact.exists():
                        # Calculate SHA256
                        sha256_hash = hashlib.sha256()
                        with open(artifact, 'rb') as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                sha256_hash.update(chunk)
                        
                        checksum = sha256_hash.hexdigest()
                        relative_path = artifact.relative_to(self.release_dir)
                        checksums.append(f"{checksum}  {relative_path}")
            
            # Write checksums file
            checksums_content = "\\n".join(sorted(checksums)) + "\\n"
            checksums_path.write_text(checksums_content, encoding='utf-8')
            
            print(f"✅ Created checksums file with {len(checksums)} entries")
            return True
            
        except Exception as e:
            print(f"❌ Error creating checksums: {e}")
            return False
    
    def create_git_tag(self) -> bool:
        """Create and push git tag for the release."""
        try:
            # Create annotated tag
            tag_message = f"Release version {self.version}"
            result = subprocess.run([
                'git', 'tag', '-a', f'v{self.version}',
                '-m', tag_message
            ], cwd=self.project_root)
            
            if result.returncode != 0:
                print(f"❌ Failed to create git tag")
                return False
            
            print(f"✅ Created git tag: v{self.version}")
            
            # Ask if we should push the tag
            response = input("Push tag to remote? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                result = subprocess.run([
                    'git', 'push', 'origin', f'v{self.version}'
                ], cwd=self.project_root)
                
                if result.returncode == 0:
                    print(f"✅ Pushed tag to remote")
                else:
                    print(f"❌ Failed to push tag to remote")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating git tag: {e}")
            return False
    
    def run_release(self) -> bool:
        """Run the complete release process."""
        print(f"""
{'='*80}
SubtitleToolkit Release Builder
{'='*80}

Version: {self.version}
Platforms: {', '.join(self.platforms)}
Build All: {self.build_all}

{'='*80}
""")
        
        # Validation steps
        if not self.validate_version():
            return False
        
        if not self.check_git_status():
            response = input("Continue anyway? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                return False
        
        # Prepare release
        if not self.prepare_release_directory():
            return False
        
        if not self.update_version_files():
            return False
        
        # Build for each platform
        build_success = True
        for platform in self.platforms:
            if platform == self.current_platform or self.build_all:
                if not self.build_platform(platform):
                    build_success = False
                    continue
                
                if not self.test_platform(platform):
                    print(f"⚠️  Tests failed for {platform}, continuing anyway...")
                
                if not self.package_artifacts(platform):
                    build_success = False
        
        if not build_success:
            print("❌ Some builds failed")
            return False
        
        # Create additional release artifacts
        if not self.create_source_package():
            return False
        
        if not self.generate_release_notes():
            return False
        
        if not self.create_checksums():
            return False
        
        # Git tag
        create_tag = input("Create git tag for this release? (Y/n): ").strip().lower()
        if create_tag not in ['n', 'no']:
            self.create_git_tag()
        
        # Summary
        print(f"\\n{'='*80}")
        print("RELEASE SUMMARY")
        print(f"{'='*80}")
        print(f"Version: {self.version}")
        print(f"Release directory: {self.release_dir}")
        print(f"Total artifacts: {sum(len(artifacts) for artifacts in self.artifacts.values())}")
        
        total_size = 0
        for platform, artifacts in self.artifacts.items():
            if artifacts:
                print(f"\\n{platform.upper()}:")
                for artifact in artifacts:
                    size_mb = artifact.stat().st_size / (1024 * 1024)
                    total_size += size_mb
                    print(f"  {artifact.name} ({size_mb:.1f} MB)")
        
        print(f"\\nTotal release size: {total_size:.1f} MB")
        print(f"\\n✅ Release {self.version} created successfully!")
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Create release packages for SubtitleToolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'version',
        help='Release version (e.g., 1.0.0, 1.2.0-beta.1)'
    )
    
    parser.add_argument(
        '--platform',
        choices=['windows', 'macos', 'linux', 'current'],
        default='current',
        help='Platform to build for (default: current platform only)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Build for all platforms (requires appropriate build environments)'
    )
    
    args = parser.parse_args()
    
    # Determine platforms to build
    build_all = args.all or args.platform == 'all'
    
    try:
        manager = ReleaseManager(args.version, build_all)
        success = manager.run_release()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\\n\\nRelease process interrupted by user.")
        return 130
    except Exception as e:
        print(f"\\n❌ Release process failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
#!/usr/bin/env python3
"""
macOS DMG creator for SubtitleToolkit

This script creates a professional DMG file for macOS distribution
with proper styling and background images.
"""

import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
import time


class DMGCreator:
    """Creates styled DMG files for macOS applications."""
    
    def __init__(self, app_path: Path, output_path: Path):
        self.app_path = app_path
        self.output_path = output_path
        self.project_root = Path(__file__).parent.parent.parent
        self.temp_dmg = None
        self.mount_point = None
    
    def create_dmg(self) -> bool:
        """Create the DMG file."""
        try:
            # Validate inputs
            if not self.app_path.exists():
                print(f"ERROR: Application not found: {self.app_path}")
                return False
            
            # Remove existing DMG
            if self.output_path.exists():
                self.output_path.unlink()
                print(f"Removed existing DMG: {self.output_path}")
            
            # Create temporary DMG
            self.temp_dmg = self.output_path.with_suffix('.tmp.dmg')
            volume_name = "SubtitleToolkit"
            
            print("Creating temporary DMG...")
            if not self._create_temp_dmg(volume_name):
                return False
            
            # Mount the DMG
            print("Mounting DMG for customization...")
            if not self._mount_dmg():
                return False
            
            # Customize the DMG
            print("Customizing DMG appearance...")
            self._customize_dmg()
            
            # Unmount the DMG
            print("Unmounting DMG...")
            self._unmount_dmg()
            
            # Convert to final compressed DMG
            print("Creating final compressed DMG...")
            if not self._create_final_dmg():
                return False
            
            print(f"✅ DMG created successfully: {self.output_path}")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to create DMG: {e}")
            return False
        
        finally:
            # Cleanup
            self._cleanup()
    
    def _create_temp_dmg(self, volume_name: str) -> bool:
        """Create temporary writable DMG."""
        try:
            # Calculate size (app size + 50MB buffer)
            app_size_mb = self._get_directory_size(self.app_path) // (1024 * 1024)
            dmg_size_mb = app_size_mb + 50
            
            cmd = [
                'hdiutil', 'create',
                '-srcfolder', str(self.app_path),
                '-volname', volume_name,
                '-fs', 'HFS+',
                '-fsargs', '-c c=64,a=16,e=16',
                '-format', 'UDRW',
                '-size', f'{dmg_size_mb}m',
                str(self.temp_dmg)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"ERROR: Failed to create temporary DMG: {result.stderr}")
                return False
            
            return True
            
        except Exception as e:
            print(f"ERROR: Exception in _create_temp_dmg: {e}")
            return False
    
    def _mount_dmg(self) -> bool:
        """Mount the temporary DMG."""
        try:
            cmd = ['hdiutil', 'attach', '-readwrite', '-noverify', str(self.temp_dmg)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"ERROR: Failed to mount DMG: {result.stderr}")
                return False
            
            # Extract mount point from output
            for line in result.stdout.split('\\n'):
                if '/Volumes/' in line:
                    self.mount_point = Path(line.split()[-1])
                    break
            
            if not self.mount_point:
                print("ERROR: Could not determine mount point")
                return False
            
            print(f"DMG mounted at: {self.mount_point}")
            return True
            
        except Exception as e:
            print(f"ERROR: Exception in _mount_dmg: {e}")
            return False
    
    def _customize_dmg(self):
        """Customize DMG appearance and layout."""
        try:
            # Create Applications symlink
            applications_link = self.mount_point / "Applications"
            if not applications_link.exists():
                os.symlink("/Applications", applications_link)
                print("Created Applications symlink")
            
            # Copy background image if available
            background_dir = self.mount_point / ".background"
            background_dir.mkdir(exist_ok=True)
            
            background_src = self.project_root / "app" / "resources" / "dmg_background.png"
            if background_src.exists():
                background_dst = background_dir / "background.png"
                shutil.copy2(background_src, background_dst)
                print("Copied background image")
            
            # Create .DS_Store for custom layout
            self._create_ds_store()
            
            # Set custom icon if available
            icon_src = self.project_root / "app" / "resources" / "icon.icns"
            if icon_src.exists():
                self._set_volume_icon(icon_src)
            
        except Exception as e:
            print(f"WARNING: DMG customization failed: {e}")
    
    def _create_ds_store(self):
        """Create .DS_Store file for custom Finder layout."""
        try:
            # Use AppleScript to set up the Finder window
            applescript = f'''
            tell application "Finder"
                tell disk "SubtitleToolkit"
                    open
                    set current view of container window to icon view
                    set toolbar visible of container window to false
                    set statusbar visible of container window to false
                    set the bounds of container window to {{400, 100, 900, 400}}
                    set viewOptions to the icon view options of container window
                    set arrangement of viewOptions to not arranged
                    set icon size of viewOptions to 72
                    set background picture of viewOptions to file ".background:background.png"
                    
                    -- Position items
                    set position of item "SubtitleToolkit.app" of container window to {{150, 200}}
                    set position of item "Applications" of container window to {{350, 200}}
                    
                    close
                    open
                    update without registering applications
                    delay 2
                end tell
            end tell
            '''
            
            # Execute AppleScript
            subprocess.run(['osascript', '-e', applescript], check=False)
            print("Applied custom Finder layout")
            
        except Exception as e:
            print(f"WARNING: Could not apply custom layout: {e}")
    
    def _set_volume_icon(self, icon_path: Path):
        """Set custom volume icon."""
        try:
            volume_icon = self.mount_point / ".VolumeIcon.icns"
            shutil.copy2(icon_path, volume_icon)
            
            # Set the volume icon attribute
            cmd = ['SetFile', '-c', 'icnC', str(volume_icon)]
            subprocess.run(cmd, check=False)
            
            cmd = ['SetFile', '-a', 'C', str(self.mount_point)]
            subprocess.run(cmd, check=False)
            
            print("Set custom volume icon")
            
        except Exception as e:
            print(f"WARNING: Could not set volume icon: {e}")
    
    def _unmount_dmg(self):
        """Unmount the DMG."""
        try:
            if self.mount_point:
                cmd = ['hdiutil', 'detach', str(self.mount_point)]
                subprocess.run(cmd, check=True)
                print("DMG unmounted")
                
        except Exception as e:
            print(f"WARNING: Error unmounting DMG: {e}")
    
    def _create_final_dmg(self) -> bool:
        """Convert to final compressed DMG."""
        try:
            cmd = [
                'hdiutil', 'convert', str(self.temp_dmg),
                '-format', 'UDZO',
                '-imagekey', 'zlib-level=9',
                '-o', str(self.output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"ERROR: Failed to create final DMG: {result.stderr}")
                return False
            
            return True
            
        except Exception as e:
            print(f"ERROR: Exception in _create_final_dmg: {e}")
            return False
    
    def _cleanup(self):
        """Clean up temporary files."""
        try:
            if self.temp_dmg and self.temp_dmg.exists():
                self.temp_dmg.unlink()
                print("Cleaned up temporary DMG")
                
        except Exception as e:
            print(f"WARNING: Cleanup error: {e}")
    
    def _get_directory_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    file_path = Path(dirpath) / filename
                    if file_path.exists():
                        total_size += file_path.stat().st_size
        except Exception as e:
            print(f"WARNING: Error calculating directory size: {e}")
            total_size = 100 * 1024 * 1024  # Default to 100MB
        
        return total_size


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Create macOS DMG for SubtitleToolkit')
    parser.add_argument('--app', type=Path, help='Path to .app bundle')
    parser.add_argument('--output', type=Path, help='Output DMG path')
    parser.add_argument('--version', default='1.0.0', help='Version string')
    
    args = parser.parse_args()
    
    # Default paths if not provided
    if not args.app:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
        args.app = project_root / 'dist' / 'SubtitleToolkit.app'
    
    if not args.output:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
        args.output = project_root / 'dist' / f'SubtitleToolkit-{args.version}.dmg'
    
    print("SubtitleToolkit DMG Creator")
    print(f"App bundle: {args.app}")
    print(f"Output DMG: {args.output}")
    print()
    
    # Create DMG
    creator = DMGCreator(args.app, args.output)
    success = creator.create_dmg()
    
    if success:
        # Show file info
        size = args.output.stat().st_size
        size_mb = size / (1024 * 1024)
        print(f"Final DMG size: {size_mb:.1f} MB")
        
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
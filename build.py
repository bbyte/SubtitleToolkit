#!/usr/bin/env python3
"""
Build script for SubtitleToolkit.

Creates a self-contained distributable package for the current platform.

Usage:
    source venv/bin/activate   # Always activate venv first!
    python build.py            # Build for current platform
    python build.py --clean    # Clean build
    python build.py --skip-scripts   # Skip rebuilding CLI scripts
    python build.py --no-archive     # Skip creating the final archive

Output:
    macOS  → dist/SubtitleToolkit-macos.zip  (contains SubtitleToolkit.app)
    Linux  → dist/SubtitleToolkit-linux.tar.gz
    Windows→ dist/SubtitleToolkit-windows.zip

To install on another machine:
    macOS  : Unzip → drag SubtitleToolkit.app to Applications
    Linux  : Untar → run SubtitleToolkit/SubtitleToolkit
    Windows: Unzip → run SubtitleToolkit/SubtitleToolkit.exe
"""

import sys
import os
import shutil
import platform
import subprocess
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()

# CLI scripts that need to be compiled as separate executables
CLI_SCRIPTS = [
    "extract_mkv_subtitles",
    "srtTranslateWhole",
    "srt_names_sync",
    "srt_fps_convert",
]


def run(cmd, cwd=None, check=True):
    """Run a command, print it, and raise on failure."""
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd or str(PROJECT_ROOT))
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed (exit {result.returncode})")
    return result


def detect_platform() -> str:
    """Return 'macos', 'linux', or 'windows'."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    else:
        raise ValueError(f"Unsupported platform: {system}")


def check_prerequisites():
    """Verify that PyInstaller is installed."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("ERROR: PyInstaller is not installed.")
        print("       Run: pip install pyinstaller")
        sys.exit(1)

    if not (PROJECT_ROOT / "app" / "main.py").exists():
        print("ERROR: app/main.py not found. Run this script from the project root.")
        sys.exit(1)


def compile_translations():
    """Compile .ts source files to .qm binary files (if pyside6-lrelease is available)."""
    ts_dir = PROJECT_ROOT / "app" / "i18n" / "translations"
    ts_files = list(ts_dir.glob("*.ts"))

    if not ts_files:
        print("  No .ts files found — skipping translation compilation.")
        return

    lrelease = shutil.which("pyside6-lrelease") or shutil.which("lrelease")
    if not lrelease:
        print("  pyside6-lrelease not found — skipping translation compilation.")
        print("  Existing .qm files will be used.")
        return

    for ts_file in ts_files:
        qm_file = ts_file.with_suffix(".qm")
        print(f"  Compiling: {ts_file.name} → {qm_file.name}")
        run([lrelease, str(ts_file), "-qm", str(qm_file)], check=False)


def build_cli_scripts(cli_dist_dir: Path):
    """Build each CLI script as a standalone --onefile executable."""
    scripts_src = PROJECT_ROOT / "scripts"
    work_dir = PROJECT_ROOT / "build_temp" / "cli"

    for name in CLI_SCRIPTS:
        script_path = scripts_src / f"{name}.py"
        if not script_path.exists():
            print(f"  WARNING: Script not found, skipping: {script_path}")
            continue

        print(f"\n  Building: {name}")
        run([
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--noconfirm",
            "--distpath", str(cli_dist_dir),
            "--workpath", str(work_dir / name),
            "--specpath", str(work_dir),
            "--name", name,
            str(script_path),
        ])


def build_main_app(platform_name: str, clean: bool):
    """Build the main GUI application using the platform spec file."""
    spec_file = PROJECT_ROOT / "build" / f"subtitletoolkit-{platform_name}.spec"

    if not spec_file.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_file}")

    print(f"\n  Spec: {spec_file.name}")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm"]
    if clean:
        cmd.append("--clean")
    cmd.append(str(spec_file))
    run(cmd)


def install_cli_into_bundle(platform_name: str, dist_dir: Path, cli_dist_dir: Path):
    """Copy compiled CLI executables into the correct location inside the app bundle."""
    ext = ".exe" if platform_name == "windows" else ""

    # Determine target scripts directory inside the bundle
    if platform_name == "macos":
        # PyInstaller BUNDLE puts files at Contents/MacOS/
        bundle_scripts = dist_dir / "SubtitleToolkit.app" / "Contents" / "MacOS" / "scripts"
    else:
        # Directory bundle: dist/SubtitleToolkit/scripts/
        bundle_scripts = dist_dir / "SubtitleToolkit" / "scripts"

    bundle_scripts.mkdir(parents=True, exist_ok=True)

    for name in CLI_SCRIPTS:
        src = cli_dist_dir / f"{name}{ext}"
        if not src.exists():
            print(f"  WARNING: CLI executable not found, skipping: {src.name}")
            continue
        dst = bundle_scripts / f"{name}{ext}"
        print(f"  {src.name} → scripts/")
        shutil.copy2(src, dst)
        if platform_name != "windows":
            dst.chmod(0o755)


def create_archive(platform_name: str, dist_dir: Path) -> Path:
    """Create a distributable archive from the bundle."""
    if platform_name == "macos":
        archive_stem = dist_dir / "SubtitleToolkit-macos"
        source_name = "SubtitleToolkit.app"
        fmt = "zip"
    elif platform_name == "windows":
        archive_stem = dist_dir / "SubtitleToolkit-windows"
        source_name = "SubtitleToolkit"
        fmt = "zip"
    else:
        archive_stem = dist_dir / "SubtitleToolkit-linux"
        source_name = "SubtitleToolkit"
        fmt = "gztar"

    source_path = dist_dir / source_name
    if not source_path.exists():
        raise FileNotFoundError(f"Bundle not found: {source_path}")

    archive_path = shutil.make_archive(
        str(archive_stem),
        fmt,
        root_dir=str(dist_dir),
        base_dir=source_name,
    )
    return Path(archive_path)


def main():
    parser = argparse.ArgumentParser(
        description="Build SubtitleToolkit for distribution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--clean", action="store_true",
                        help="Remove previous build artifacts before building")
    parser.add_argument("--skip-scripts", action="store_true",
                        help="Skip rebuilding the CLI script executables")
    parser.add_argument("--no-archive", action="store_true",
                        help="Skip creating the final distributable archive")
    args = parser.parse_args()

    platform_name = detect_platform()
    dist_dir = PROJECT_ROOT / "dist"
    cli_dist_dir = dist_dir / "_cli_builds"

    print(f"SubtitleToolkit build — platform: {platform_name}")
    print(f"Project root: {PROJECT_ROOT}\n")

    check_prerequisites()

    # Clean if requested
    if args.clean:
        print("=== Cleaning ===")
        for path in [dist_dir, PROJECT_ROOT / "build_temp"]:
            if path.exists():
                shutil.rmtree(path)
                print(f"  Removed: {path}")

    # Compile translations
    print("\n=== Compiling translations ===")
    compile_translations()

    # Build CLI scripts
    if not args.skip_scripts:
        print("\n=== Building CLI scripts ===")
        cli_dist_dir.mkdir(parents=True, exist_ok=True)
        build_cli_scripts(cli_dist_dir)
    else:
        print("\n=== CLI scripts (skipped) ===")

    # Build main app
    print("\n=== Building main application ===")
    build_main_app(platform_name, clean=args.clean)

    # Copy CLI executables into the bundle
    print("\n=== Installing CLI scripts into bundle ===")
    install_cli_into_bundle(platform_name, dist_dir, cli_dist_dir)

    # Create archive
    if not args.no_archive:
        print("\n=== Creating distributable archive ===")
        archive = create_archive(platform_name, dist_dir)
        size_mb = archive.stat().st_size / (1024 * 1024)
        print(f"  Archive: {archive.name}  ({size_mb:.1f} MB)")

    print("\n✓ Build complete!")

    # Print install instructions
    print("\nInstallation instructions:")
    if platform_name == "macos":
        print("  1. Unzip SubtitleToolkit-macos.zip")
        print("  2. Drag SubtitleToolkit.app to /Applications")
        print("  3. On first launch: right-click → Open (to bypass Gatekeeper)")
    elif platform_name == "linux":
        print("  1. Extract SubtitleToolkit-linux.tar.gz")
        print("  2. Run: ./SubtitleToolkit/SubtitleToolkit")
    else:
        print("  1. Unzip SubtitleToolkit-windows.zip")
        print("  2. Run SubtitleToolkit\\SubtitleToolkit.exe")


if __name__ == "__main__":
    main()

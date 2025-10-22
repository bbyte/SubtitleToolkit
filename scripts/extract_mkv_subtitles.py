#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
import time
import re
import threading
from queue import Queue
from datetime import datetime, timezone


# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


# Global flag to control output mode
jsonl_mode = False


def emit_jsonl(event_type, message, progress=None, data=None):
    """Emit a JSONL event to stdout."""
    if not jsonl_mode:
        return
    
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stage": "extract",
        "type": event_type,
        "msg": message
    }
    
    if progress is not None:
        event["progress"] = progress
    
    if data is not None:
        event["data"] = data
    
    print(json.dumps(event), flush=True)


def print_colored(message, end='\n'):
    """Print message only if not in JSONL mode."""
    if not jsonl_mode:
        print(message, end=end, flush=True)


def print_banner():
    """Print fancy ASCII art banner."""
    if jsonl_mode:
        return
        
    banner = f"""{Colors.CYAN}
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║  {Colors.BOLD}███╗   ███╗██╗  ██╗██╗   ██╗    ███████╗██████╗ ████████╗{Colors.ENDC}{Colors.CYAN}   ║
║  {Colors.BOLD}████╗ ████║██║ ██╔╝██║   ██║    ██╔════╝██╔══██╗╚══██╔══╝{Colors.ENDC}{Colors.CYAN}   ║
║  {Colors.BOLD}██╔████╔██║█████╔╝ ██║   ██║    ███████╗██████╔╝   ██║   {Colors.ENDC}{Colors.CYAN}   ║
║  {Colors.BOLD}██║╚██╔╝██║██╔═██╗ ╚██╗ ██╔╝    ╚════██║██╔══██╗   ██║   {Colors.ENDC}{Colors.CYAN}   ║
║  {Colors.BOLD}██║ ╚═╝ ██║██║  ██╗ ╚████╔╝     ███████║██║  ██║   ██║   {Colors.ENDC}{Colors.CYAN}   ║
║  {Colors.BOLD}╚═╝     ╚═╝╚═╝  ╚═╝  ╚═══╝      ╚══════╝╚═╝  ╚═╝   ╚═╝   {Colors.ENDC}{Colors.CYAN}   ║
║                                                               ║
║  {Colors.YELLOW}            Subtitle Extractor for MKV Files{Colors.CYAN}                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.ENDC}
"""
    print(banner)


def print_progress_bar(current, total, prefix='', suffix='', length=50):
    """Print a progress bar."""
    if jsonl_mode:
        return
        
    percent = int(100 * (current / float(total)))
    filled_length = int(length * current // total)
    bar = '█' * filled_length + '░' * (length - filled_length)
    
    # Choose color based on progress
    if percent < 33:
        color = Colors.RED
    elif percent < 66:
        color = Colors.YELLOW
    else:
        color = Colors.GREEN
    
    print(f'\r{prefix} {color}[{bar}]{Colors.ENDC} {percent}% {suffix}', end='', flush=True)
    if current == total:
        print()


def spinning_animation(text, duration=0.5):
    """Show a spinning animation."""
    if jsonl_mode:
        return
        
    chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        print(f'\r{Colors.CYAN}{chars[i % len(chars)]}{Colors.ENDC} {text}', end='', flush=True)
        time.sleep(0.1)
        i += 1
    print('\r' + ' ' * (len(text) + 5), end='\r')  # Clear the line


def get_mkv_files(directory):
    """Get all MKV files in the specified directory."""
    return list(Path(directory).glob("*.mkv"))


def get_subtitle_tracks(mkv_file):
    """Get subtitle track information from MKV file using ffprobe."""
    spinning_animation(f"Analyzing {mkv_file.name}", 0.3)
    
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "s",
        str(mkv_file)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return data.get("streams", [])
    except subprocess.CalledProcessError as e:
        error_msg = f"Error analyzing {mkv_file}: {e}"
        emit_jsonl("error", error_msg, data={"file": str(mkv_file), "error": str(e)})
        print_colored(f"{Colors.RED}✗ {error_msg}{Colors.ENDC}")
        return []
    except json.JSONDecodeError:
        error_msg = f"Error parsing ffprobe output for {mkv_file}"
        emit_jsonl("error", error_msg, data={"file": str(mkv_file)})
        print_colored(f"{Colors.RED}✗ {error_msg}{Colors.ENDC}")
        return []


def find_subtitle_track(tracks, language="eng"):
    """Find subtitle track with specified language."""
    
    # Create language variants for better matching
    language_variants = []
    if language.lower() == "eng" or language.lower() == "en":
        language_variants = ["eng", "en", "english", "en-us", "en-gb"]
    elif language.lower() == "es" or language.lower() == "spa":
        language_variants = ["es", "spa", "spanish", "es-es", "es-mx"]
    elif language.lower() == "fr" or language.lower() == "fra":
        language_variants = ["fr", "fra", "french", "fr-fr"]
    elif language.lower() == "de" or language.lower() == "ger":
        language_variants = ["de", "ger", "german", "de-de"]
    elif language.lower() == "it" or language.lower() == "ita":
        language_variants = ["it", "ita", "italian", "it-it"]
    elif language.lower() == "pt" or language.lower() == "por":
        language_variants = ["pt", "por", "portuguese", "pt-br", "pt-pt"]
    elif language.lower() == "ru" or language.lower() == "rus":
        language_variants = ["ru", "rus", "russian", "ru-ru"]
    elif language.lower() == "ja" or language.lower() == "jpn":
        language_variants = ["ja", "jpn", "japanese", "ja-jp"]
    elif language.lower() == "ko" or language.lower() == "kor":
        language_variants = ["ko", "kor", "korean", "ko-kr"]
    elif language.lower() == "zh" or language.lower() == "chi":
        language_variants = ["zh", "chi", "chinese", "zh-cn", "zh-tw", "cmn", "zho"]
    else:
        # For other languages, try common variations
        language_variants = [language.lower(), language[:2].lower(), language[:3].lower()]
    
    # First pass: exact matches in language tags
    for i, track in enumerate(tracks):
        tags = track.get("tags", {})
        track_language = tags.get("language", "").lower()
        
        if track_language in language_variants:
            info_msg = f"Found subtitle track with language code: {track_language}"
            emit_jsonl("info", info_msg, data={"track_index": track["index"], "language": track_language})
            print_colored(f"  {Colors.GREEN}✓ {info_msg}{Colors.ENDC}")
            return track["index"]
    
    # Second pass: check titles for language info
    for i, track in enumerate(tracks):
        tags = track.get("tags", {})
        title = tags.get("title", "").lower()
        
        for variant in language_variants:
            if variant in title:
                info_msg = f"Found subtitle track with language in title: {title}"
                emit_jsonl("info", info_msg, data={"track_index": track["index"], "title": title})
                print_colored(f"  {Colors.GREEN}✓ {info_msg}{Colors.ENDC}")
                return track["index"]
    
    # Third pass: log all available subtitle tracks for debugging
    debug_msg = "Available subtitle tracks:"
    emit_jsonl("info", debug_msg)
    print_colored(f"  {Colors.CYAN}📋 {debug_msg}{Colors.ENDC}")
    
    for i, track in enumerate(tracks):
        tags = track.get("tags", {})
        track_language = tags.get("language", "N/A")
        track_title = tags.get("title", "N/A")
        track_info = f"  Track {track['index']}: language='{track_language}', title='{track_title}'"
        emit_jsonl("info", track_info, data={"track_index": track["index"], "language": track_language, "title": track_title})
        print_colored(f"    {Colors.DIM}{track_info}{Colors.ENDC}")
    
    # If no language match found and there's only one subtitle track, use it
    if len(tracks) == 1:
        warning_msg = f"No {language} subtitle found, using the only available subtitle track"
        emit_jsonl("warning", warning_msg, data={"language": language, "track_count": len(tracks)})
        print_colored(f"  {Colors.YELLOW}⚠ {warning_msg}{Colors.ENDC}")
        return tracks[0]["index"]
    
    return None


def get_duration(mkv_file):
    """Get duration of MKV file in seconds."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(mkv_file)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except:
        return None


def parse_time(time_str):
    """Parse time string (HH:MM:SS.MS) to seconds."""
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        else:
            return float(time_str)
    except:
        return 0


def extract_subtitle(mkv_file, track_index, output_file, overwrite=False):
    """Extract subtitle track from MKV file with progress."""
    duration = get_duration(mkv_file)

    cmd = [
        "ffmpeg",
        "-i", str(mkv_file),
        "-map", f"0:{track_index}",
        "-c:s", "copy",
        str(output_file),
    ]

    # Only add overwrite flag if explicitly requested
    if overwrite:
        cmd.append("-y")

    cmd.extend([
        "-progress", "pipe:1",  # Output progress to stdout
        "-loglevel", "error"
    ])
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   text=True, bufsize=1, universal_newlines=True)
        
        # Variables for progress tracking
        current_time = 0
        progress_line = f"  {Colors.CYAN}Extracting:{Colors.ENDC} "
        last_percent = -1
        
        for line in process.stdout:
            if line.startswith('out_time='):
                # Extract time from ffmpeg progress
                time_match = re.search(r'out_time=(\d+:\d+:\d+\.\d+)', line)
                if time_match and duration:
                    current_time = parse_time(time_match.group(1))
                    percent = min(int((current_time / duration) * 100), 100)
                    
                    # Emit progress events (throttled to avoid spam)
                    if jsonl_mode and percent != last_percent and percent % 10 == 0:
                        emit_jsonl("progress", f"Extracting subtitle from {mkv_file.name}", 
                                 progress=percent, 
                                 data={"file": str(mkv_file), "output_file": str(output_file)})
                        last_percent = percent
                    
                    # Update progress bar (only in non-JSONL mode)
                    if not jsonl_mode:
                        filled_length = int(30 * percent // 100)
                        bar = '█' * filled_length + '░' * (30 - filled_length)
                        
                        # Choose color based on progress
                        if percent < 33:
                            color = Colors.RED
                        elif percent < 66:
                            color = Colors.YELLOW
                        else:
                            color = Colors.GREEN
                        
                        print(f'\r{progress_line}{color}[{bar}]{Colors.ENDC} {percent}%', end='', flush=True)
        
        # Wait for process to complete
        process.wait()
        
        if process.returncode == 0:
            print_colored(f'\r{progress_line}{Colors.GREEN}[{"█" * 30}]{Colors.ENDC} 100%')
            return True
        else:
            stderr = process.stderr.read()
            error_msg = f"Error extracting subtitle: {stderr}"
            emit_jsonl("error", error_msg, data={"file": str(mkv_file), "error": stderr})
            print_colored(f"\r{Colors.RED}✗ {error_msg}{Colors.ENDC}")
            return False
            
    except Exception as e:
        error_msg = f"Error extracting subtitle: {e}"
        emit_jsonl("error", error_msg, data={"file": str(mkv_file), "error": str(e)})
        print_colored(f"\r{Colors.RED}✗ {error_msg}{Colors.ENDC}")
        return False


def main():
    global jsonl_mode
    
    parser = argparse.ArgumentParser(description="Extract subtitles from MKV files")
    parser.add_argument("path", nargs="?", default=".",
                        help="Directory containing MKV files or path to single MKV file (default: current directory)")
    parser.add_argument("-l", "--language", default="eng",
                        help="Language code for subtitle track (default: eng)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output directory for extracted subtitles (default: same as input)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite existing subtitle files (default: skip existing)")
    parser.add_argument("--jsonl", action="store_true",
                        help="Output structured JSONL events to stdout")
    
    args = parser.parse_args()
    
    # Set global JSONL mode
    jsonl_mode = args.jsonl
    
    # Print banner
    print_banner()
    
    # Validate input path (can be directory or single MKV file)
    input_path = Path(args.path)
    if not input_path.exists():
        error_msg = f"Path '{input_path}' does not exist"
        emit_jsonl("error", error_msg, data={"path": str(input_path)})
        print_colored(f"{Colors.RED}✗ Error: {error_msg}{Colors.ENDC}")
        sys.exit(1)
    
    # Determine if processing single file or directory
    if input_path.is_file():
        # Single file mode
        if not input_path.suffix.lower() == '.mkv':
            error_msg = f"Single file input must be an MKV file, got: {input_path.suffix}"
            emit_jsonl("error", error_msg, data={"path": str(input_path)})
            print_colored(f"{Colors.RED}✗ Error: {error_msg}{Colors.ENDC}")
            sys.exit(1)
        
        print_colored(f"\n{Colors.CYAN}🎯 Processing single file:{Colors.ENDC} {Colors.BOLD}{input_path.name}{Colors.ENDC}")
        mkv_files = [input_path]
        
    elif input_path.is_dir():
        # Directory mode
        print_colored(f"\n{Colors.CYAN}🔍 Scanning directory:{Colors.ENDC} {Colors.BOLD}{input_path}{Colors.ENDC}")
        mkv_files = get_mkv_files(input_path)
        
    else:
        error_msg = f"Path must be either a directory or an MKV file: {input_path}"
        emit_jsonl("error", error_msg, data={"path": str(input_path)})
        print_colored(f"{Colors.RED}✗ Error: {error_msg}{Colors.ENDC}")
        sys.exit(1)
    
    if not mkv_files:
        if input_path.is_dir():
            warning_msg = f"No MKV files found in {input_path}"
        else:
            warning_msg = f"File is not a valid MKV: {input_path}"
        emit_jsonl("warning", warning_msg, data={"path": str(input_path)})
        print_colored(f"{Colors.YELLOW}⚠ {warning_msg}{Colors.ENDC}")
        return
    
    if input_path.is_dir():
        info_msg = f"Found {len(mkv_files)} MKV file(s) in {input_path}"
    else:
        info_msg = f"Processing single MKV file: {input_path.name}"
    
    emit_jsonl("info", info_msg, data={
        "path": str(input_path),
        "file_count": len(mkv_files),
        "language": args.language,
        "mode": "directory" if input_path.is_dir() else "single_file"
    })
    
    print_colored(f"{Colors.GREEN}✓ Found {len(mkv_files)} MKV file(s){Colors.ENDC}")
    print_colored(f"{Colors.CYAN}🌐 Target language:{Colors.ENDC} {Colors.BOLD}{args.language.upper()}{Colors.ENDC}\n")
    
    print_colored(f"{Colors.HEADER}{'='*65}{Colors.ENDC}\n")
    
    successful = 0
    failed = 0
    outputs = []
    skipped_files = []
    
    # Process each MKV file
    for i, mkv_file in enumerate(mkv_files, 1):
        print_colored(f"{Colors.BOLD}[{i}/{len(mkv_files)}] {mkv_file.name}{Colors.ENDC}")
        
        # Emit overall progress
        overall_progress = int((i - 1) * 100 / len(mkv_files))
        emit_jsonl("progress", f"Processing file {i} of {len(mkv_files)}: {mkv_file.name}", 
                  progress=overall_progress, 
                  data={"current_file": i, "total_files": len(mkv_files), "file": str(mkv_file)})
        
        # Get subtitle tracks
        subtitle_tracks = get_subtitle_tracks(mkv_file)
        
        if not subtitle_tracks:
            error_msg = f"No subtitle tracks found in {mkv_file.name}"
            emit_jsonl("warning", error_msg, data={"file": str(mkv_file)})
            print_colored(f"  {Colors.RED}✗ No subtitle tracks found{Colors.ENDC}")
            failed += 1
            skipped_files.append({"file": str(mkv_file), "reason": "No subtitle tracks found"})
            print_progress_bar(i, len(mkv_files), prefix='Overall Progress:', 
                             suffix=f'{successful} success, {failed} failed')
            print_colored("")
            continue
        
        info_msg = f"Found {len(subtitle_tracks)} subtitle track(s) in {mkv_file.name}"
        emit_jsonl("info", info_msg, data={"file": str(mkv_file), "track_count": len(subtitle_tracks)})
        print_colored(f"  {Colors.GREEN}✓ Found {len(subtitle_tracks)} subtitle track(s){Colors.ENDC}")
        
        # Find desired language track
        track_index = find_subtitle_track(subtitle_tracks, args.language)
        
        if track_index is None:
            warning_msg = f"No {args.language} subtitle track found in {mkv_file.name}"
            emit_jsonl("warning", warning_msg, data={"file": str(mkv_file), "language": args.language})
            print_colored(f"  {Colors.RED}✗ No {args.language} subtitle track found{Colors.ENDC}")
            failed += 1
            skipped_files.append({"file": str(mkv_file), "reason": f"No {args.language} subtitle track found"})
            print_progress_bar(i, len(mkv_files), prefix='Overall Progress:', 
                             suffix=f'{successful} success, {failed} failed')
            print_colored("")
            continue
        
        # Create output filename
        if args.output:
            # Use specified output directory
            output_dir = Path(args.output)
            output_file = output_dir / f"{mkv_file.stem}.srt"
        else:
            # Use same directory as input
            output_file = mkv_file.with_suffix(".srt")

        # Check if output file already exists and skip if not overwriting
        if output_file.exists() and not args.overwrite:
            skip_msg = f"Skipping {mkv_file.name} - subtitle file already exists: {output_file.name}"
            emit_jsonl("info", skip_msg, data={"file": str(mkv_file), "output_file": str(output_file), "reason": "already_exists"})
            print_colored(f"  {Colors.YELLOW}⊘ Skipping - {output_file.name} already exists{Colors.ENDC}")
            skipped_files.append({"file": str(mkv_file), "reason": "Output file already exists"})
            print_colored("")
            continue

        # Extract subtitle
        info_msg = f"Extracting track {track_index} from {mkv_file.name} to {output_file.name}"
        emit_jsonl("info", info_msg, data={"file": str(mkv_file), "track_index": track_index, "output_file": str(output_file)})
        print_colored(f"  {Colors.CYAN}📝 Track {track_index} → {output_file.name}{Colors.ENDC}")

        if extract_subtitle(mkv_file, track_index, output_file, overwrite=args.overwrite):
            success_msg = f"Successfully extracted subtitle from {mkv_file.name}"
            emit_jsonl("info", success_msg, data={"file": str(mkv_file), "output_file": str(output_file)})
            print_colored(f"  {Colors.GREEN}✓ Successfully extracted!{Colors.ENDC}")
            successful += 1
            outputs.append({"input_file": str(mkv_file), "output_file": str(output_file)})
        else:
            print_colored(f"  {Colors.RED}✗ Extraction failed!{Colors.ENDC}")
            failed += 1
            skipped_files.append({"file": str(mkv_file), "reason": "Extraction failed"})
        
        print_progress_bar(i, len(mkv_files), prefix='Overall Progress:', 
                         suffix=f'{successful} success, {failed} failed')
        print_colored("")
    
    # Emit final progress and result
    emit_jsonl("progress", "Subtitle extraction complete", progress=100, 
              data={"successful": successful, "failed": failed, "total": len(mkv_files)})
    
    # Emit final result
    result_msg = f"Processed {len(mkv_files)} files: {successful} successful, {failed} failed"
    emit_jsonl("result", result_msg, data={
        "total_files": len(mkv_files),
        "successful": successful,
        "failed": failed,
        "outputs": outputs,
        "skipped_files": skipped_files,
        "language": args.language,
        "path": str(input_path)
    })
    
    # Print summary (only in non-JSONL mode)
    print_colored(f"\n{Colors.HEADER}{'='*65}{Colors.ENDC}")
    print_colored(f"\n{Colors.BOLD}📊 Summary:{Colors.ENDC}")
    print_colored(f"  {Colors.GREEN}✓ Successful:{Colors.ENDC} {successful}")
    print_colored(f"  {Colors.RED}✗ Failed:{Colors.ENDC} {failed}")
    print_colored(f"  {Colors.BLUE}📁 Total processed:{Colors.ENDC} {len(mkv_files)}")
    
    if successful > 0:
        print_colored(f"\n{Colors.GREEN}🎉 Subtitle extraction complete!{Colors.ENDC}")
    else:
        print_colored(f"\n{Colors.YELLOW}⚠ No subtitles were extracted.{Colors.ENDC}")


if __name__ == "__main__":
    main()
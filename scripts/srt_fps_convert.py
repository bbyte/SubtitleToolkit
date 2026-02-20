#!/usr/bin/env python3
"""
srt_fps_convert.py - Convert SRT subtitle timecodes between frame rates.

Scales every timestamp by (target_fps / source_fps) so subtitles created
for one frame rate (e.g. 25 fps PAL) display correctly at another (e.g.
23.976 fps NTSC).

Usage examples
--------------
  # Auto-detect FPS from a video file:
  python3 srt_fps_convert.py -f movie.srt --video movie.mkv --source-fps 25

  # Specify both FPS values explicitly:
  python3 srt_fps_convert.py -d /subs --source-fps 25 --target-fps 23.976

  # Process directory with auto-detection per paired video:
  python3 srt_fps_convert.py -d /shows --source-fps 25 --target-fps 23.976

JSONL output
------------
Every progress/status line is emitted as a JSON object:
  {"ts": "...", "stage": "fps_sync", "type": "info|progress|warning|error|result", "msg": "...", "data": {...}}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# JSONL output helpers
# ---------------------------------------------------------------------------

jsonl_mode: bool = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit_jsonl(
    event_type: str,
    message: str,
    progress: Optional[int] = None,
    data: Optional[dict] = None,
) -> None:
    """Emit a JSONL event to stdout."""
    event: dict = {
        "ts": _now_iso(),
        "stage": "fps_sync",
        "type": event_type,
        "msg": message,
    }
    if progress is not None:
        event["progress"] = progress
    if data is not None:
        event["data"] = data
    print(json.dumps(event, ensure_ascii=False), flush=True)


def log(message: str, level: str = "info", progress: Optional[int] = None, data: Optional[dict] = None) -> None:
    """Log a message — JSONL when in GUI mode, plain text otherwise."""
    if jsonl_mode:
        emit_jsonl(level, message, progress=progress, data=data)
    else:
        prefix = {"info": "  ", "warning": "⚠ ", "error": "✗ ", "progress": "→ "}.get(level, "  ")
        print(f"{prefix}{message}", flush=True)


# ---------------------------------------------------------------------------
# FPS detection via ffprobe
# ---------------------------------------------------------------------------

COMMON_FPS = {
    "23.976": 24000 / 1001,
    "23.98": 24000 / 1001,
    "24": 24.0,
    "25": 25.0,
    "29.97": 30000 / 1001,
    "29.976": 30000 / 1001,
    "30": 30.0,
    "50": 50.0,
    "59.94": 60000 / 1001,
    "60": 60.0,
}


def parse_fps_string(fps_str: str) -> float:
    """Parse an FPS value that may be 'num/den' or a float string."""
    fps_str = fps_str.strip()
    if "/" in fps_str:
        num, den = fps_str.split("/", 1)
        return int(num) / int(den)
    return float(fps_str)


def detect_video_fps(video_path: str, ffprobe_path: Optional[str] = None) -> Optional[float]:
    """
    Use ffprobe to detect the frame rate of a video file.

    Returns the frame rate as a float, or None if detection fails.
    """
    ffprobe = ffprobe_path or "ffprobe"
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        streams = data.get("streams", [])

        # Prefer video streams; check r_frame_rate then avg_frame_rate
        for stream in streams:
            if stream.get("codec_type") != "video":
                continue

            for key in ("r_frame_rate", "avg_frame_rate"):
                fps_raw = stream.get(key, "")
                if fps_raw and fps_raw not in ("0/0", "0"):
                    try:
                        fps = parse_fps_string(fps_raw)
                        if fps > 0:
                            return fps
                    except (ValueError, ZeroDivisionError):
                        continue

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, OSError):
        pass

    return None


def find_paired_video(srt_path: Path, video_extensions: tuple = (".mkv", ".mp4", ".avi", ".mov")) -> Optional[Path]:
    """Look for a video file with the same stem as the SRT file."""
    parent = srt_path.parent
    stem = srt_path.stem
    # Strip language suffix like .en, .bg, .de etc.
    for ext in video_extensions:
        candidate = parent / (stem + ext)
        if candidate.exists():
            return candidate
        # Try stripping a 2-3 char language code suffix (e.g. movie.en.srt → movie.mkv)
        if "." in stem:
            base = stem.rsplit(".", 1)[0]
            candidate = parent / (base + ext)
            if candidate.exists():
                return candidate
    return None


# ---------------------------------------------------------------------------
# SRT parsing and timecode manipulation
# ---------------------------------------------------------------------------

TIMECODE_RE = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def timecode_to_ms(h: int, m: int, s: int, ms: int) -> int:
    return ((h * 3600) + (m * 60) + s) * 1000 + ms


def ms_to_timecode(ms_total: int) -> str:
    ms_total = max(0, int(round(ms_total)))
    ms = ms_total % 1000
    s_total = ms_total // 1000
    s = s_total % 60
    m_total = s_total // 60
    m = m_total % 60
    h = m_total // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def scale_srt_content(content: str, ratio: float) -> tuple[str, int]:
    """
    Scale every SRT timecode in *content* by *ratio*.

    Returns (scaled_content, subtitle_count).
    """
    count = 0

    def replacer(m: re.Match) -> str:
        nonlocal count
        count += 1
        h1, m1, s1, ms1 = int(m[1]), int(m[2]), int(m[3]), int(m[4])
        h2, m2, s2, ms2 = int(m[5]), int(m[6]), int(m[7]), int(m[8])

        start_ms = timecode_to_ms(h1, m1, s1, ms1)
        end_ms = timecode_to_ms(h2, m2, s2, ms2)

        new_start = start_ms * ratio
        new_end = end_ms * ratio

        # Ensure end > start after rounding
        new_start_r = int(round(new_start))
        new_end_r = max(int(round(new_end)), new_start_r + 1)

        return f"{ms_to_timecode(new_start_r)} --> {ms_to_timecode(new_end_r)}"

    scaled = TIMECODE_RE.sub(replacer, content)
    return scaled, count


# ---------------------------------------------------------------------------
# File processing
# ---------------------------------------------------------------------------

def process_srt_file(
    srt_path: Path,
    source_fps: float,
    target_fps: float,
    output_path: Optional[Path],
    overwrite: bool,
    auto_detect_fps: bool,
    ffprobe_path: Optional[str],
) -> dict:
    """
    Convert a single SRT file's timecodes.

    Returns a result dict suitable for the JSONL result event.
    """
    # Optionally auto-detect target FPS from paired video
    effective_target_fps = target_fps
    if auto_detect_fps:
        video = find_paired_video(srt_path)
        if video:
            detected = detect_video_fps(str(video), ffprobe_path)
            if detected and abs(detected - source_fps) > 0.01:
                effective_target_fps = detected
                log(f"Auto-detected target FPS {detected:.4f} from {video.name}", "info")
            elif detected:
                log(
                    f"Source and detected FPS are equal ({detected:.4f}), skipping {srt_path.name}",
                    "info",
                )
                return {
                    "input_file": str(srt_path),
                    "output_file": str(srt_path),
                    "skipped": True,
                    "reason": "source and target FPS are equal",
                }
        else:
            log(f"No paired video found for {srt_path.name}, using supplied target FPS", "warning")

    ratio = effective_target_fps / source_fps

    # Determine output path
    if output_path is None:
        # Overwrite in-place
        dest = srt_path
    elif output_path.is_dir():
        dest = output_path / srt_path.name
    else:
        dest = output_path

    if dest.exists() and not overwrite and dest != srt_path:
        log(f"Skipping {srt_path.name} — output already exists: {dest}", "warning")
        return {
            "input_file": str(srt_path),
            "output_file": str(dest),
            "skipped": True,
            "reason": "output already exists",
        }

    # Read input
    try:
        raw = srt_path.read_bytes()
        # Detect encoding (prefer UTF-8 with BOM stripping)
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                content = raw.decode("cp1252")
            except UnicodeDecodeError:
                content = raw.decode("latin-1")
    except OSError as exc:
        raise RuntimeError(f"Cannot read {srt_path}: {exc}") from exc

    scaled, subtitle_count = scale_srt_content(content, ratio)

    if subtitle_count == 0:
        log(f"No timecodes found in {srt_path.name} — is this a valid SRT file?", "warning")

    # Write output
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(scaled, encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Cannot write {dest}: {exc}") from exc

    log(
        f"Converted {srt_path.name}: {source_fps:.3f} → {effective_target_fps:.3f} fps  ({subtitle_count} subtitles)",
        "info",
    )

    return {
        "input_file": str(srt_path),
        "output_file": str(dest),
        "source_fps": source_fps,
        "target_fps": effective_target_fps,
        "ratio": ratio,
        "subtitle_count": subtitle_count,
        "skipped": False,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def collect_srt_files(root: Path, recursive: bool) -> list[Path]:
    """Gather SRT files from a directory."""
    pattern = "**/*.srt" if recursive else "*.srt"
    return sorted(root.glob(pattern))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert SRT subtitle timecodes between frame rates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Input specification
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-f", "--file", metavar="FILE", help="Single SRT file to convert")
    input_group.add_argument("-d", "--directory", metavar="DIR", help="Directory of SRT files")

    # FPS settings
    parser.add_argument(
        "--source-fps",
        type=float,
        required=True,
        metavar="FPS",
        help="Frame rate the subtitles were authored for (e.g. 25)",
    )
    parser.add_argument(
        "--target-fps",
        type=float,
        default=None,
        metavar="FPS",
        help="Target frame rate (e.g. 23.976). Required unless --video or --auto-detect is used.",
    )
    parser.add_argument(
        "--video",
        metavar="FILE",
        default=None,
        help="Video file to auto-detect target FPS from (uses ffprobe).",
    )
    parser.add_argument(
        "--auto-detect",
        action="store_true",
        help="Auto-detect target FPS by looking for a paired video file next to each SRT.",
    )

    # Output settings
    parser.add_argument(
        "-o", "--output",
        metavar="PATH",
        default=None,
        help="Output file or directory. Defaults to overwriting input file(s).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files.",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not recurse into subdirectories (directory mode only).",
    )

    # Tool paths
    parser.add_argument("--ffprobe", metavar="PATH", default=None, help="Path to ffprobe executable.")

    # GUI mode
    parser.add_argument("--jsonl", action="store_true", help="Emit JSONL events (for GUI integration).")

    args = parser.parse_args()

    global jsonl_mode
    jsonl_mode = args.jsonl

    # Determine target FPS
    target_fps: Optional[float] = args.target_fps
    auto_detect = args.auto_detect

    if args.video:
        # Detect FPS from an explicit video file
        log(f"Detecting FPS from video: {args.video}", "info")
        detected = detect_video_fps(args.video, args.ffprobe)
        if detected is None:
            log(f"Could not detect FPS from {args.video}", "error")
            return 1
        target_fps = detected
        log(f"Detected target FPS: {target_fps:.4f}", "info")
    elif target_fps is None and not auto_detect:
        log("Must specify --target-fps, --video, or --auto-detect", "error")
        return 1

    if target_fps is not None and abs(target_fps - args.source_fps) < 0.001:
        log(f"Source and target FPS are equal ({target_fps:.4f}), nothing to do.", "warning")
        return 0

    # Collect SRT files
    if args.file:
        srt_path = Path(args.file)
        if not srt_path.exists():
            log(f"File not found: {args.file}", "error")
            return 1
        srt_files = [srt_path]
    else:
        dir_path = Path(args.directory)
        if not dir_path.is_dir():
            log(f"Directory not found: {args.directory}", "error")
            return 1
        recursive = not args.no_recursive
        srt_files = collect_srt_files(dir_path, recursive)
        if not srt_files:
            log(f"No SRT files found in {args.directory}", "warning")
            return 0

    total = len(srt_files)
    log(f"Found {total} SRT file(s) to process", "info", progress=0)

    output_path = Path(args.output) if args.output else None

    results = []
    successful = 0
    failed = 0
    skipped = 0

    for idx, srt_path in enumerate(srt_files, 1):
        progress = int((idx - 1) / total * 100)
        log(f"[{idx}/{total}] {srt_path.name}", "progress", progress=progress)

        try:
            result = process_srt_file(
                srt_path=srt_path,
                source_fps=args.source_fps,
                target_fps=target_fps or args.target_fps or 0.0,
                output_path=output_path,
                overwrite=args.overwrite,
                auto_detect_fps=auto_detect,
                ffprobe_path=args.ffprobe,
            )
            results.append(result)
            if result.get("skipped"):
                skipped += 1
            else:
                successful += 1
        except Exception as exc:
            log(f"Failed to process {srt_path.name}: {exc}", "error")
            results.append({
                "input_file": str(srt_path),
                "error": str(exc),
                "skipped": False,
            })
            failed += 1

    # Emit final result
    outputs = [r for r in results if not r.get("skipped") and "output_file" in r]
    summary = {
        "files_processed": total,
        "files_successful": successful,
        "files_failed": failed,
        "files_skipped": skipped,
        "source_fps": args.source_fps,
        "target_fps": target_fps,
        "outputs": [r["output_file"] for r in outputs],
        "results": results,
    }

    log(
        f"FPS conversion complete: {successful} converted, {skipped} skipped, {failed} failed",
        "result",
        progress=100,
        data=summary,
    )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

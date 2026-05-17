#!/usr/bin/env python3
"""
find_subtitles.py — search subtitle sites for movies in a directory.

Usage examples:
  python3 scripts/find_subtitles.py /path/to/movies -l bg
  python3 scripts/find_subtitles.py /path/to/movie.mkv -l en --jsonl
  python3 scripts/find_subtitles.py /path/to/movies --nfo-only

The script reads .nfo files (with AI + ffprobe fallback) to identify
each movie, then queries all configured subtitle providers in parallel.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

# Allow running from project root without installing
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from scripts.lib.subtitle_finder import (
    SubtitleFinder, MovieInfo, SubtitleResult,
    parse_nfo, parse_video_with_ffprobe,
    find_nfo_for_video, find_nfos_in_directory,
)
from scripts.lib.subtitle_finder.language_map import language_name

# ── ANSI colours (disabled in --jsonl mode) ─────────────────────────────────
_USE_COLOR = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

GREEN  = lambda t: _c("32", t)
YELLOW = lambda t: _c("33", t)
CYAN   = lambda t: _c("36", t)
RED    = lambda t: _c("31", t)
BOLD   = lambda t: _c("1",  t)


# ── JSONL output helpers ────────────────────────────────────────────────────

def emit(event: str, data: dict, jsonl: bool) -> None:
    if jsonl:
        print(json.dumps({"event": event, **data}), flush=True)


def info(msg: str, jsonl: bool) -> None:
    if jsonl:
        emit("log", {"level": "info", "message": msg}, jsonl)
    else:
        print(msg)


def warn(msg: str, jsonl: bool) -> None:
    if jsonl:
        emit("log", {"level": "warning", "message": msg}, jsonl)
    else:
        print(YELLOW(f"[WARN] {msg}"))


def error(msg: str, jsonl: bool) -> None:
    if jsonl:
        emit("log", {"level": "error", "message": msg}, jsonl)
    else:
        print(RED(f"[ERROR] {msg}"), file=sys.stderr)


# ── Default provider configs (fallback when no settings file present) ───────

DEFAULT_PROVIDERS = [
    {
        "id": "opensubtitles",
        "name": "OpenSubtitles",
        "type": "api",
        "enabled": True,
        "url": "https://api.opensubtitles.com/api/v1",
        "api_key": os.getenv("OPENSUBTITLES_API_KEY", ""),
        "username": os.getenv("OPENSUBTITLES_USERNAME", ""),
        "password": os.getenv("OPENSUBTITLES_PASSWORD", ""),
    },
    {
        "id": "subdl",
        "name": "SubDL",
        "type": "api",
        "enabled": True,
        "url": "https://api.subdl.com/api/v1",
        "api_key": os.getenv("SUBDL_API_KEY", ""),
    },
    {
        "id": "subsunacs",
        "name": "Subsunacs.net",
        "type": "scraper",
        "enabled": True,
        "url": "https://subsunacs.net/",
    },
    {
        "id": "yavka",
        "name": "Yavka.net",
        "type": "scraper",
        "enabled": True,
        "url": "https://yavka.net/",
    },
    {
        "id": "sabsubs",
        "name": "Subs SAB",
        "type": "scraper",
        "enabled": True,
        "url": "http://subs.sab.bz/",
    },
]


def load_settings_providers(settings_path: Optional[Path]) -> List[dict]:
    """Load provider configs from the app settings file if available."""
    if not settings_path or not settings_path.exists():
        return DEFAULT_PROVIDERS
    try:
        with settings_path.open() as f:
            settings = json.load(f)
        providers = settings.get("subtitle_finder", {}).get("providers", [])
        if providers:
            return providers
    except (json.JSONDecodeError, OSError):
        pass
    return DEFAULT_PROVIDERS


def find_movies(path: Path) -> List[Path]:
    """Return MKV/MP4/AVI files in path (or just path itself if it's a file)."""
    video_exts = {".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv", ".ts", ".m2ts"}
    if path.is_file():
        return [path] if path.suffix.lower() in video_exts else []
    return sorted(
        p for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in video_exts
    )


def resolve_movie_info(
    video: Path,
    ai_config: Optional[dict],
    jsonl: bool,
) -> Optional[MovieInfo]:
    """Get MovieInfo for a video file: NFO first, then ffprobe."""
    nfo = find_nfo_for_video(video)
    if nfo:
        info(f"Parsing NFO: {nfo.name}", jsonl)
        movie = parse_nfo(nfo, ai_config)
        if movie:
            movie.source_file = str(video)
            if not movie.fps:
                # Try to get FPS from video if NFO didn't have it
                probe = parse_video_with_ffprobe(video)
                if probe:
                    movie.fps = probe.fps
            return movie

    # No NFO or parsing failed — use ffprobe
    info(f"No NFO found, using ffprobe on {video.name}", jsonl)
    movie = parse_video_with_ffprobe(video)
    if movie:
        return movie

    # Last resort: filename only
    warn(f"Could not determine movie info for {video.name}", jsonl)
    stem = video.stem
    return MovieInfo(title=stem, source_file=str(video))


def interactive_select(results: List[SubtitleResult], movie: MovieInfo) -> Optional[SubtitleResult]:
    """Present numbered list and let the user pick one."""
    print()
    print(BOLD(f"Found {len(results)} subtitles for: {movie.display_name()}"))
    print()

    for i, r in enumerate(results, 1):
        lang = language_name(r.language)
        fps_str = f"  {r.fps:.3f} fps" if r.fps else ""
        hi_str  = "  [HI]" if r.is_hearing_impaired else ""
        dc_str  = f"  ↓{r.download_count}" if r.download_count else ""
        print(
            f"  {CYAN(str(i).rjust(3))}.  "
            f"{BOLD(lang.ljust(12))} "
            f"[{r.provider}]  "
            f"{r.title[:60]}{fps_str}{hi_str}{dc_str}"
        )

    print()
    while True:
        try:
            raw = input("Select subtitle number (or 0 to skip): ").strip()
            idx = int(raw)
            if idx == 0:
                return None
            if 1 <= idx <= len(results):
                return results[idx - 1]
        except (ValueError, KeyboardInterrupt):
            return None
        print(RED("Invalid choice."))


def download_subtitle(
    finder: SubtitleFinder,
    result: SubtitleResult,
    video: Path,
    jsonl: bool,
) -> bool:
    lang = result.language or "xx"
    dest = video.with_suffix(f".{lang}.srt")
    info(f"Downloading → {dest.name}", jsonl)
    ok = finder.download(result, str(dest))
    if ok:
        if jsonl:
            emit("downloaded", {"path": str(dest), "language": lang}, jsonl)
        else:
            print(GREEN(f"✓ Saved: {dest}"))
    else:
        error(f"Download failed for {result.title}", jsonl)
    return ok


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find and download subtitles for video files."
    )
    parser.add_argument("path", help="Video file or directory to process")
    parser.add_argument("-l", "--language", default="",
                        help="Preferred subtitle language (ISO 639-1, e.g. bg, en)")
    parser.add_argument("--fallback-language", default=None,
                        help="Fallback language if preferred not found (empty=any)")
    parser.add_argument("--limit", type=int, default=10,
                        help="Max results per provider (default: 10)")
    parser.add_argument("--nfo-only", action="store_true",
                        help="Only parse and display NFO/movie info, don't search")
    parser.add_argument("--jsonl", action="store_true",
                        help="Output JSONL events (for GUI integration)")
    parser.add_argument("--auto-download", type=int, default=0, metavar="N",
                        help="Auto-download result #N without interactive prompt")
    parser.add_argument("--settings", default="",
                        help="Path to app settings.json (for provider config)")
    parser.add_argument("--ai-provider", default="openai",
                        help="AI provider for NFO fallback (openai|anthropic)")
    parser.add_argument("--ai-model", default="gpt-4o-mini",
                        help="AI model for NFO fallback")
    parser.add_argument("--ai-key", default="",
                        help="API key for AI NFO fallback")
    args = parser.parse_args()

    global _USE_COLOR
    if args.jsonl:
        _USE_COLOR = False

    target = Path(args.path).expanduser().resolve()
    if not target.exists():
        error(f"Path not found: {target}", args.jsonl)
        return 1

    # Load providers from settings or environment
    settings_path = Path(args.settings) if args.settings else None
    if not settings_path:
        # Try the default app settings location
        default_settings = Path.home() / ".config" / "subtitletoolkit" / "settings.json"
        if default_settings.exists():
            settings_path = default_settings

    provider_configs = load_settings_providers(settings_path)

    ai_config = None
    ai_key = args.ai_key or os.getenv("OPENAI_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
    if ai_key:
        ai_config = {
            "enabled": True,
            "provider": args.ai_provider,
            "model": args.ai_model,
            "api_key": ai_key,
        }

    videos = find_movies(target)
    if not videos:
        error(f"No video files found in: {target}", args.jsonl)
        return 1

    finder = SubtitleFinder(provider_configs)
    overall_ok = True

    for video in videos:
        if args.jsonl:
            emit("video_start", {"path": str(video)}, args.jsonl)
        else:
            print()
            print(BOLD(f"━━  {video.name}  ━━"))

        movie = resolve_movie_info(video, ai_config, args.jsonl)
        if not movie:
            overall_ok = False
            continue

        info(f"Movie: {movie.display_name()}", args.jsonl)
        if movie.fps:
            info(f"FPS:   {movie.fps}", args.jsonl)
        if movie.imdb_id:
            info(f"IMDB:  tt{movie.imdb_id}", args.jsonl)

        if args.nfo_only:
            if args.jsonl:
                emit("movie_info", {
                    "title": movie.title,
                    "original_title": movie.original_title,
                    "year": movie.year,
                    "imdb_id": movie.imdb_id,
                    "fps": movie.fps,
                    "original_language": movie.original_language,
                }, args.jsonl)
            continue

        # Search
        lang = args.language or ""
        info(f"Searching for subtitles ({language_name(lang) if lang else 'any language'})…", args.jsonl)

        def _progress(msg: str) -> None:
            info(f"  {msg}", args.jsonl)

        results = finder.search(
            movie,
            language=lang,
            fallback_language=args.fallback_language,
            progress_cb=_progress,
            max_per_provider=args.limit,
        )

        if not results:
            warn(f"No subtitles found for: {movie.display_name()}", args.jsonl)
            overall_ok = False
            continue

        if args.jsonl:
            emit("results", {
                "movie": movie.display_name(),
                "count": len(results),
                "items": [
                    {
                        "index": i + 1,
                        "title": r.title,
                        "language": r.language,
                        "provider": r.provider,
                        "provider_id": r.provider_id,
                        "download_url": r.download_url,
                        "fps": r.fps,
                        "download_count": r.download_count,
                        "rating": r.rating,
                        "is_hearing_impaired": r.is_hearing_impaired,
                        "release_name": r.release_name,
                        "format": r.format,
                    }
                    for i, r in enumerate(results)
                ],
            }, args.jsonl)

            # In JSONL mode with --auto-download, download without interaction
            if args.auto_download and 1 <= args.auto_download <= len(results):
                ok = download_subtitle(finder, results[args.auto_download - 1], video, args.jsonl)
                overall_ok = overall_ok and ok
        else:
            # Interactive CLI mode
            if args.auto_download and 1 <= args.auto_download <= len(results):
                chosen = results[args.auto_download - 1]
            else:
                chosen = interactive_select(results, movie)

            if chosen:
                ok = download_subtitle(finder, chosen, video, args.jsonl)
                overall_ok = overall_ok and ok
            else:
                info("Skipped.", args.jsonl)

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())

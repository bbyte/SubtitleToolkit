"""
MKV Language Detection Utility

This module provides functionality to detect available subtitle languages in MKV files
using ffprobe. It can analyze single files or entire directories containing MKV files.
"""

import subprocess
import json
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Union
from dataclasses import dataclass


@dataclass
class SubtitleTrack:
    """Represents a subtitle track found in an MKV file."""
    index: int
    language_code: str
    language_name: str
    title: Optional[str] = None
    codec: Optional[str] = None
    forced: bool = False
    default: bool = False


@dataclass 
class MKVAnalysisResult:
    """Result of analyzing an MKV file for subtitle tracks."""
    file_path: Path
    subtitle_tracks: List[SubtitleTrack]
    has_subtitles: bool
    error: Optional[str] = None


@dataclass
class LanguageDetectionResult:
    """Result of language detection across multiple files."""
    available_languages: List[Tuple[str, str]]  # [(code, display_name), ...]
    file_results: List[MKVAnalysisResult]
    total_files: int
    files_with_subtitles: int
    errors: List[str]


class MKVLanguageDetector:
    """
    Utility class for detecting available subtitle languages in MKV files.
    
    Uses ffprobe to analyze MKV files and extract subtitle track information,
    providing language codes and display names for UI integration.
    """
    
    # Language code to display name mapping
    LANGUAGE_NAMES = {
        'eng': 'English',
        'en': 'English', 
        'spa': 'Spanish',
        'es': 'Spanish',
        'fra': 'French',
        'fr': 'French',
        'deu': 'German',
        'de': 'German',
        'ger': 'German',
        'ita': 'Italian',
        'it': 'Italian',
        'por': 'Portuguese',
        'pt': 'Portuguese',
        'rus': 'Russian',
        'ru': 'Russian',
        'jpn': 'Japanese',
        'ja': 'Japanese',
        'kor': 'Korean',
        'ko': 'Korean',
        'chi': 'Chinese',
        'zh': 'Chinese',
        'zho': 'Chinese',
        'cmn': 'Chinese (Mandarin)',
        'ara': 'Arabic',
        'ar': 'Arabic',
        'hin': 'Hindi',
        'hi': 'Hindi',
        'ben': 'Bengali',
        'bn': 'Bengali',
        'urd': 'Urdu',
        'ur': 'Urdu',
        'tha': 'Thai',
        'th': 'Thai',
        'vie': 'Vietnamese',
        'vi': 'Vietnamese',
        'pol': 'Polish',
        'pl': 'Polish',
        'nld': 'Dutch',
        'nl': 'Dutch',
        'swe': 'Swedish',
        'sv': 'Swedish',
        'dan': 'Danish',
        'da': 'Danish',
        'nor': 'Norwegian',
        'no': 'Norwegian',
        'fin': 'Finnish',
        'fi': 'Finnish',
        'ell': 'Greek',
        'el': 'Greek',
        'heb': 'Hebrew',
        'he': 'Hebrew',
        'tur': 'Turkish',
        'tr': 'Turkish',
        'cze': 'Czech',
        'cs': 'Czech',
        'hun': 'Hungarian',
        'hu': 'Hungarian',
        'ron': 'Romanian',
        'ro': 'Romanian',
        'bul': 'Bulgarian',
        'bg': 'Bulgarian',
        'hrv': 'Croatian',
        'hr': 'Croatian',
        'srp': 'Serbian',
        'sr': 'Serbian',
        'slv': 'Slovenian',
        'sl': 'Slovenian',
        'slk': 'Slovak',
        'sk': 'Slovak',
        'ukr': 'Ukrainian',
        'uk': 'Ukrainian',
        'lit': 'Lithuanian',
        'lt': 'Lithuanian',
        'lav': 'Latvian',
        'lv': 'Latvian',
        'est': 'Estonian',
        'et': 'Estonian',
    }
    
    @staticmethod
    def get_language_display_name(language_code: str) -> str:
        """
        Get display name for a language code.
        
        Args:
            language_code: ISO language code (e.g., 'eng', 'es', 'fr')
            
        Returns:
            Human-readable language name, or the code itself if not found
        """
        if not language_code:
            return "Unknown"
            
        code_lower = language_code.lower()
        return MKVLanguageDetector.LANGUAGE_NAMES.get(code_lower, language_code.upper())
    
    @staticmethod
    def analyze_mkv_file(mkv_file: Path) -> MKVAnalysisResult:
        """
        Analyze a single MKV file to extract subtitle track information.
        
        Args:
            mkv_file: Path to the MKV file to analyze
            
        Returns:
            MKVAnalysisResult with subtitle tracks and metadata
        """
        if not mkv_file.exists():
            return MKVAnalysisResult(
                file_path=mkv_file,
                subtitle_tracks=[],
                has_subtitles=False,
                error=f"File does not exist: {mkv_file}"
            )
        
        if not mkv_file.is_file():
            return MKVAnalysisResult(
                file_path=mkv_file,
                subtitle_tracks=[],
                has_subtitles=False,
                error=f"Path is not a file: {mkv_file}"
            )
        
        # Use ffprobe to get subtitle stream information
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "s",  # Select only subtitle streams
            str(mkv_file)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            subtitle_tracks = []
            streams = data.get("streams", [])
            
            for stream in streams:
                # Extract subtitle track information
                index = stream.get("index", -1)
                tags = stream.get("tags", {})
                disposition = stream.get("disposition", {})
                
                # Get language code from tags
                language_code = tags.get("language", "")
                if not language_code:
                    # Try alternative tag names
                    language_code = tags.get("LANGUAGE", "")
                
                # Get title/description 
                title = tags.get("title") or tags.get("TITLE")
                
                # Get codec information
                codec = stream.get("codec_name", "")
                
                # Check if track is forced or default
                forced = disposition.get("forced", 0) == 1
                default = disposition.get("default", 0) == 1
                
                # Create subtitle track object
                track = SubtitleTrack(
                    index=index,
                    language_code=language_code,
                    language_name=MKVLanguageDetector.get_language_display_name(language_code),
                    title=title,
                    codec=codec,
                    forced=forced,
                    default=default
                )
                
                subtitle_tracks.append(track)
            
            return MKVAnalysisResult(
                file_path=mkv_file,
                subtitle_tracks=subtitle_tracks,
                has_subtitles=len(subtitle_tracks) > 0,
                error=None
            )
            
        except subprocess.CalledProcessError as e:
            error_msg = f"ffprobe failed for {mkv_file.name}: {e}"
            if e.stderr:
                error_msg += f" - {e.stderr}"
            
            return MKVAnalysisResult(
                file_path=mkv_file,
                subtitle_tracks=[],
                has_subtitles=False,
                error=error_msg
            )
            
        except json.JSONDecodeError as e:
            return MKVAnalysisResult(
                file_path=mkv_file,
                subtitle_tracks=[],
                has_subtitles=False,
                error=f"Failed to parse ffprobe output for {mkv_file.name}: {e}"
            )
            
        except Exception as e:
            return MKVAnalysisResult(
                file_path=mkv_file,
                subtitle_tracks=[],
                has_subtitles=False,
                error=f"Unexpected error analyzing {mkv_file.name}: {e}"
            )
    
    @staticmethod
    def find_mkv_files(directory: Path) -> List[Path]:
        """
        Find all MKV files in a directory.
        
        Args:
            directory: Directory to search for MKV files
            
        Returns:
            List of Path objects for MKV files found
        """
        if not directory.exists() or not directory.is_dir():
            return []
        
        mkv_files = []
        try:
            # Search for MKV files (case-insensitive)
            for pattern in ["*.mkv", "*.MKV"]:
                mkv_files.extend(directory.glob(pattern))
                
            # Sort by name for consistent ordering
            mkv_files.sort(key=lambda p: p.name.lower())
            
        except Exception:
            # If globbing fails, return empty list
            pass
            
        return mkv_files
    
    @staticmethod
    def detect_languages_in_path(path: Union[str, Path]) -> LanguageDetectionResult:
        """
        Detect all available subtitle languages in MKV files at the given path.
        
        Args:
            path: Either a directory containing MKV files or a single MKV file
            
        Returns:
            LanguageDetectionResult with all detected languages and file analysis
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            return LanguageDetectionResult(
                available_languages=[],
                file_results=[],
                total_files=0,
                files_with_subtitles=0,
                errors=[f"Path does not exist: {path}"]
            )
        
        # Determine if it's a single file or directory
        if path_obj.is_file():
            # Single file mode
            if path_obj.suffix.lower() != '.mkv':
                return LanguageDetectionResult(
                    available_languages=[],
                    file_results=[],
                    total_files=0,
                    files_with_subtitles=0,
                    errors=[f"File is not an MKV file: {path_obj.suffix}"]
                )
            
            mkv_files = [path_obj]
            
        elif path_obj.is_dir():
            # Directory mode
            mkv_files = MKVLanguageDetector.find_mkv_files(path_obj)
            
            if not mkv_files:
                return LanguageDetectionResult(
                    available_languages=[],
                    file_results=[],
                    total_files=0,
                    files_with_subtitles=0,
                    errors=[f"No MKV files found in directory: {path}"]
                )
        else:
            return LanguageDetectionResult(
                available_languages=[],
                file_results=[],
                total_files=0,
                files_with_subtitles=0,
                errors=[f"Path is neither a file nor directory: {path}"]
            )
        
        # Analyze each MKV file
        file_results = []
        all_language_codes = set()
        errors = []
        files_with_subtitles = 0
        
        for mkv_file in mkv_files:
            result = MKVLanguageDetector.analyze_mkv_file(mkv_file)
            file_results.append(result)
            
            if result.error:
                errors.append(result.error)
            
            if result.has_subtitles:
                files_with_subtitles += 1
                
                # Collect all unique language codes
                for track in result.subtitle_tracks:
                    if track.language_code:
                        all_language_codes.add(track.language_code.lower())
        
        # Convert language codes to display format
        available_languages = []
        for code in sorted(all_language_codes):
            display_name = MKVLanguageDetector.get_language_display_name(code)
            available_languages.append((code, display_name))
        
        return LanguageDetectionResult(
            available_languages=available_languages,
            file_results=file_results,
            total_files=len(mkv_files),
            files_with_subtitles=files_with_subtitles,
            errors=errors
        )
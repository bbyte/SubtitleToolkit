#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import re
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime, timezone

import openai
import anthropic
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

class LLMProvider(Enum):
    OPENAI = "openai"
    CLAUDE = "claude"

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

@dataclass
class MediaFile:
    path: Path
    name: str
    extension: str

@dataclass
class MatchResult:
    mkv_file: MediaFile
    srt_file: MediaFile
    confidence: float
    reason: str

class SRTNamesSync:
    def __init__(self, directory: str, provider: LLMProvider, model: str = None, jsonl_mode: bool = False, language_filter: str = None, auto_backup_existing: bool = False):
        self.directory = Path(directory)
        self.provider = provider
        self.model = model or self._get_default_model()
        self.language_filter = language_filter  # e.g., 'bg' to only match .bg.srt files
        self.auto_backup_existing = auto_backup_existing  # Auto-rename existing files to .original.srt
        self.mkv_files: List[MediaFile] = []
        self.srt_files: List[MediaFile] = []
        self.jsonl_mode = jsonl_mode

        # Initialize LLM clients
        self._init_llm_clients()
        
    def _get_default_model(self) -> str:
        if self.provider == LLMProvider.OPENAI:
            return "gpt-4o-mini"
        elif self.provider == LLMProvider.CLAUDE:
            return "claude-3-haiku-20240307"
    
    def _emit_jsonl(self, event_type: str, msg: str, progress: Optional[int] = None, data: Optional[Dict] = None):
        """Emit a JSONL event to stdout"""
        if not self.jsonl_mode:
            return
            
        event = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "stage": "sync",
            "type": event_type,
            "msg": msg
        }
        
        if progress is not None:
            event["progress"] = progress
            
        if data is not None:
            event["data"] = data
            
        print(json.dumps(event, ensure_ascii=False))
    
    def _print_or_emit(self, message: str, event_type: str = "info", progress: Optional[int] = None, data: Optional[Dict] = None):
        """Print message normally or emit JSONL event based on mode"""
        if self.jsonl_mode:
            # Strip ANSI codes from message for JSONL
            clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', message)
            self._emit_jsonl(event_type, clean_msg, progress, data)
        else:
            print(message)
    
    def _init_llm_clients(self):
        try:
            if self.provider == LLMProvider.OPENAI:
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY environment variable not set")
                self.openai_client = openai.OpenAI(api_key=api_key)
            
            elif self.provider == LLMProvider.CLAUDE:
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY environment variable not set")
                self.claude_client = anthropic.Anthropic(api_key=api_key)
                
        except Exception as e:
            error_msg = f"{Colors.FAIL}Error initializing LLM client: {e}{Colors.ENDC}"
            self._print_or_emit(error_msg, "error")
            sys.exit(1)
    
    def discover_files(self) -> Tuple[List[MediaFile], List[MediaFile]]:
        """Recursively discover .mkv and .srt files in the directory"""
        self._print_or_emit(
            f"{Colors.HEADER}🔍 Discovering media files in: {self.directory}{Colors.ENDC}",
            "info",
            data={"directory": str(self.directory)}
        )
        
        mkv_files = []
        srt_files = []
        
        for file_path in self.directory.rglob('*'):
            if file_path.is_file():
                if file_path.suffix.lower() == '.mkv':
                    mkv_files.append(MediaFile(file_path, file_path.stem, file_path.suffix))
                elif file_path.suffix.lower() == '.srt':
                    # Apply language filter if specified
                    if self.language_filter:
                        # Check if filename matches the language filter pattern
                        # e.g., for language_filter='bg', match files like 'movie.bg.srt'
                        if file_path.stem.endswith(f'.{self.language_filter}'):
                            srt_files.append(MediaFile(file_path, file_path.stem, file_path.suffix))
                    else:
                        # No filter, include all SRT files
                        srt_files.append(MediaFile(file_path, file_path.stem, file_path.suffix))
        
        self._print_or_emit(
            f"{Colors.OKGREEN}Found {len(mkv_files)} MKV files and {len(srt_files)} SRT files{Colors.ENDC}",
            "info",
            data={"mkv_count": len(mkv_files), "srt_count": len(srt_files)}
        )
        
        self.mkv_files = mkv_files
        self.srt_files = srt_files
        
        return mkv_files, srt_files
    
    def _create_matching_prompt(self, mkv_file: MediaFile, srt_files: List[MediaFile]) -> str:
        """Create a prompt for the LLM to match MKV and SRT files"""
        
        srt_list = "\n".join([f"- {srt.name}" for srt in srt_files])
        
        prompt = f"""You are helping to match video files (.mkv) with their corresponding subtitle files (.srt).

MKV file to match: "{mkv_file.name}"

Available SRT files:
{srt_list}

Please analyze the MKV filename and determine which SRT file is the best match. Consider:
- Show/movie titles (including abbreviations)
- Season and episode numbers (various formats like S01E01, s1e1, 1x01, etc.)
- Release years
- Common abbreviations and naming patterns

Respond with a JSON object containing:
{{
    "best_match": "exact_srt_filename_without_extension",
    "confidence": 0.95,
    "reason": "Brief explanation of why this is the best match"
}}

If no good match is found, set "best_match" to null and confidence to 0.0."""

        return prompt
    
    def _query_llm(self, prompt: str) -> Dict:
        """Query the selected LLM provider"""
        try:
            if self.provider == LLMProvider.OPENAI:
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=500
                )
                content = response.choices[0].message.content
            
            elif self.provider == LLMProvider.CLAUDE:
                response = self.claude_client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
            
            # Parse JSON response
            try:
                # Extract JSON from response - handle various formats
                # 1. Try markdown code blocks first
                if "```json" in content:
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1)
                elif "```" in content:
                    json_match = re.search(r'```\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1)
                else:
                    # 2. Try to extract JSON object from beginning of response
                    # Claude often returns JSON followed by explanation
                    json_match = re.search(r'^\s*(\{[^}]*\})', content, re.DOTALL | re.MULTILINE)
                    if json_match:
                        # Found opening brace, now find the matching closing brace
                        brace_count = 0
                        start_idx = content.find('{')
                        if start_idx != -1:
                            for i, char in enumerate(content[start_idx:], start=start_idx):
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        # Found matching closing brace
                                        content = content[start_idx:i+1]
                                        break

                return json.loads(content.strip())
            except json.JSONDecodeError as e:
                self._print_or_emit(
                    f"{Colors.WARNING}Failed to parse JSON response: {content[:200]}...{Colors.ENDC}",
                    "warning"
                )
                return {"best_match": None, "confidence": 0.0, "reason": "Failed to parse response"}
        
        except Exception as e:
            self._print_or_emit(
                f"{Colors.FAIL}Error querying LLM: {e}{Colors.ENDC}",
                "error"
            )
            return {"best_match": None, "confidence": 0.0, "reason": f"Error: {e}"}
    
    def find_matches(self) -> List[MatchResult]:
        """Find matches between MKV and SRT files using LLM"""
        self._print_or_emit(
            f"{Colors.HEADER}🤖 Analyzing file matches with {self.provider.value} ({self.model}){Colors.ENDC}",
            "info",
            data={"provider": self.provider.value, "model": self.model}
        )
        
        matches = []
        total_files = len(self.mkv_files)
        
        # Use tqdm only in non-JSONL mode
        mkv_iterator = self.mkv_files if self.jsonl_mode else tqdm(
            self.mkv_files, 
            desc="Processing MKV files", 
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
        )
        
        for i, mkv_file in enumerate(mkv_iterator, 1):
            if self.jsonl_mode:
                progress = int((i / total_files) * 100)
                self._emit_jsonl(
                    "progress", 
                    f"Processing MKV file {i}/{total_files}: {mkv_file.name}",
                    progress,
                    {"current_file": mkv_file.name}
                )
            
            prompt = self._create_matching_prompt(mkv_file, self.srt_files)
            result = self._query_llm(prompt)
            
            if result["best_match"] and result["confidence"] > 0.3:
                # Find the matching SRT file
                matching_srt = None
                for srt_file in self.srt_files:
                    if srt_file.name == result["best_match"]:
                        matching_srt = srt_file
                        break
                
                if matching_srt:
                    match_result = MatchResult(
                        mkv_file=mkv_file,
                        srt_file=matching_srt,
                        confidence=result["confidence"],
                        reason=result["reason"]
                    )
                    matches.append(match_result)
                    
                    if result["confidence"] < 0.7:
                        self._print_or_emit(
                            f"{Colors.WARNING}Low confidence match ({result['confidence']:.2%}): {mkv_file.name} -> {matching_srt.name}{Colors.ENDC}",
                            "warning",
                            data={
                                "mkv_file": mkv_file.name,
                                "srt_file": matching_srt.name,
                                "confidence": result["confidence"]
                            }
                        )
            else:
                # No match found or low confidence
                if result["confidence"] > 0.0:
                    self._print_or_emit(
                        f"{Colors.WARNING}Skipping {mkv_file.name}: confidence too low ({result['confidence']:.2%}){Colors.ENDC}",
                        "warning",
                        data={"mkv_file": mkv_file.name, "confidence": result["confidence"]}
                    )
            
            # Small delay to respect API rate limits
            time.sleep(0.1)
        
        return matches
    
    def display_matches(self, matches: List[MatchResult]):
        """Display the found matches with fancy formatting"""
        if not self.jsonl_mode:
            print(f"\n{Colors.HEADER}📋 MATCHING RESULTS{Colors.ENDC}")
            print("=" * 80)
        
        if not matches:
            self._print_or_emit(
                f"{Colors.WARNING}No matches found!{Colors.ENDC}",
                "warning"
            )
            return
        
        # Emit info about total matches found
        self._print_or_emit(
            f"Found {len(matches)} matches",
            "info",
            data={"total_matches": len(matches)}
        )
        
        for i, match in enumerate(matches, 1):
            confidence_color = Colors.OKGREEN if match.confidence > 0.8 else Colors.WARNING if match.confidence > 0.5 else Colors.FAIL
            
            if not self.jsonl_mode:
                print(f"\n{Colors.BOLD}Match #{i}:{Colors.ENDC}")
                print(f"  {Colors.OKBLUE}MKV:{Colors.ENDC} {match.mkv_file.name}")
                print(f"  {Colors.OKCYAN}SRT:{Colors.ENDC} {match.srt_file.name}")
                print(f"  {Colors.BOLD}Confidence:{Colors.ENDC} {confidence_color}{match.confidence:.2%}{Colors.ENDC}")
                print(f"  {Colors.BOLD}Reason:{Colors.ENDC} {match.reason}")
            else:
                self._emit_jsonl(
                    "info",
                    f"Match {i}: {match.mkv_file.name} -> {match.srt_file.name} (confidence: {match.confidence:.2%})",
                    data={
                        "match_number": i,
                        "mkv_file": match.mkv_file.name,
                        "srt_file": match.srt_file.name,
                        "confidence": match.confidence,
                        "reason": match.reason
                    }
                )
    
    def rename_files(self, matches: List[MatchResult], dry_run: bool = True):
        """Rename SRT files to match MKV files"""
        action = "Would rename" if dry_run else "Renaming"
        self._print_or_emit(
            f"\n{Colors.HEADER}🔄 {action} SRT files{Colors.ENDC}",
            "info",
            data={"dry_run": dry_run}
        )
        
        renamed_count = 0
        renames = []
        
        for match in matches:
            old_path = match.srt_file.path
            new_name = match.mkv_file.name + ".srt"
            new_path = old_path.parent / new_name
            
            if old_path.name == new_name:
                self._print_or_emit(
                    f"  {Colors.OKCYAN}SKIP:{Colors.ENDC} {old_path.name} (already correctly named)",
                    "info",
                    data={"action": "skip", "reason": "already correctly named", "file": old_path.name}
                )
                continue
            
            if new_path.exists():
                # Handle existing file based on auto_backup_existing flag
                if self.auto_backup_existing:
                    # Rename existing file to .original.srt
                    backup_path = new_path.parent / f"{new_path.stem}.original{new_path.suffix}"

                    # If .original.srt also exists, find a unique name
                    counter = 1
                    while backup_path.exists():
                        backup_path = new_path.parent / f"{new_path.stem}.original{counter}{new_path.suffix}"
                        counter += 1

                    backup_action = "Would backup" if dry_run else "Backing up"
                    self._print_or_emit(
                        f"  {Colors.OKCYAN}{backup_action}:{Colors.ENDC} {new_path.name} -> {backup_path.name}",
                        "info",
                        data={"action": "backup", "from": new_path.name, "to": backup_path.name}
                    )

                    if not dry_run:
                        try:
                            new_path.rename(backup_path)
                        except Exception as e:
                            error_msg = f"    {Colors.FAIL}ERROR backing up:{Colors.ENDC} {e}"
                            self._print_or_emit(error_msg, "error", data={"file": new_path.name, "error": str(e)})
                            continue  # Skip this rename if backup failed
                else:
                    # Skip if not auto-backing up
                    self._print_or_emit(
                        f"  {Colors.WARNING}SKIP:{Colors.ENDC} {new_name} (target file already exists)",
                        "warning",
                        data={"action": "skip", "reason": "target exists", "target": new_name}
                    )
                    continue
            
            rename_info = {
                "from": old_path.name,
                "to": new_name,
                "confidence": match.confidence,
                "reason": match.reason
            }
            renames.append(rename_info)
            
            if not self.jsonl_mode:
                print(f"  {Colors.OKGREEN}{'WOULD RENAME' if dry_run else 'RENAME'}:{Colors.ENDC}")
                print(f"    {Colors.FAIL}From:{Colors.ENDC} {old_path.name}")
                print(f"    {Colors.OKGREEN}To:{Colors.ENDC}   {new_name}")
            else:
                self._emit_jsonl(
                    "info",
                    f"{'Would rename' if dry_run else 'Renaming'}: {old_path.name} -> {new_name}",
                    data={"action": "rename", **rename_info}
                )
            
            if not dry_run:
                try:
                    old_path.rename(new_path)
                    renamed_count += 1
                except Exception as e:
                    error_msg = f"    {Colors.FAIL}ERROR:{Colors.ENDC} {e}"
                    self._print_or_emit(error_msg, "error", data={"file": old_path.name, "error": str(e)})
            else:
                renamed_count += 1
        
        # Emit final result
        if self.jsonl_mode:
            self._emit_jsonl(
                "result",
                f"{'Would rename' if dry_run else 'Renamed'} {renamed_count} files",
                data={
                    "renames": renames,
                    "dry_run": dry_run,
                    "total_renames": renamed_count
                }
            )
        
        if dry_run:
            self._print_or_emit(
                f"\n{Colors.WARNING}DRY RUN: {renamed_count} files would be renamed{Colors.ENDC}",
                "warning",
                data={"would_rename_count": renamed_count}
            )
            if not self.jsonl_mode:
                print(f"{Colors.BOLD}Use --execute to actually rename files{Colors.ENDC}")
        else:
            self._print_or_emit(
                f"\n{Colors.OKGREEN}Successfully renamed {renamed_count} files{Colors.ENDC}",
                "info",
                data={"renamed_count": renamed_count}
            )

def main():
    parser = argparse.ArgumentParser(
        description="🎬 SRT Names Sync - Match and rename subtitle files using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python srt_names_sync.py                          # Current directory, OpenAI
  python srt_names_sync.py /path/to/videos          # Specific directory
  python srt_names_sync.py --provider claude        # Use Claude instead
  python srt_names_sync.py --execute                # Actually rename files
  python srt_names_sync.py --model gpt-4o           # Use specific model
  python srt_names_sync.py --jsonl                  # Output structured JSONL events
        """
    )
    
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to search for files (default: current directory)"
    )
    
    parser.add_argument(
        "--provider",
        choices=["openai", "claude"],
        default="openai",
        help="LLM provider to use (default: openai)"
    )
    
    parser.add_argument(
        "--model",
        help="Specific model to use (default: gpt-4o-mini for OpenAI, claude-3-haiku-20240307 for Claude)"
    )
    
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually rename files (default: dry run)"
    )
    
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.3,
        help="Minimum confidence threshold for matches (default: 0.3)"
    )

    parser.add_argument(
        "--language-filter",
        type=str,
        default=None,
        help="Filter subtitles by language code (e.g., 'bg' for .bg.srt files, 'en' for .en.srt). Leave empty to match all .srt files."
    )

    parser.add_argument(
        "--auto-backup-existing",
        action="store_true",
        help="Automatically rename existing files to .original.srt instead of skipping them"
    )

    parser.add_argument(
        "--jsonl",
        action="store_true",
        help="Output structured JSONL events instead of colored console output"
    )
    
    args = parser.parse_args()
    
    # Print banner (only in non-JSONL mode)
    if not args.jsonl:
        print(f"{Colors.HEADER}")
        print("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
        print("┃                  🎬 SRT Names Sync                       ┃")
        print("┃              AI-Powered Subtitle Matching               ┃") 
        print("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
        print(f"{Colors.ENDC}")
    
    # Validate directory
    if not Path(args.directory).exists():
        error_msg = f"{Colors.FAIL}Error: Directory '{args.directory}' does not exist{Colors.ENDC}"
        if args.jsonl:
            # Emit error event for JSONL mode
            event = {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stage": "sync",
                "type": "error",
                "msg": f"Directory '{args.directory}' does not exist",
                "data": {"directory": args.directory}
            }
            print(json.dumps(event))
        else:
            print(error_msg)
        sys.exit(1)
    
    # Initialize app
    provider = LLMProvider(args.provider)
    app = SRTNamesSync(args.directory, provider, args.model, args.jsonl, args.language_filter, args.auto_backup_existing)
    
    # Emit start event for JSONL mode
    if args.jsonl:
        app._emit_jsonl(
            "info", 
            f"Starting SRT Names Sync with {provider.value} provider",
            data={
                "provider": provider.value,
                "model": app.model,
                "directory": args.directory,
                "dry_run": not args.execute
            }
        )
    
    # Discover files
    mkv_files, srt_files = app.discover_files()
    
    if not mkv_files:
        app._print_or_emit(
            f"{Colors.WARNING}No MKV files found in the directory{Colors.ENDC}",
            "warning"
        )
        sys.exit(0)
    
    if not srt_files:
        app._print_or_emit(
            f"{Colors.WARNING}No SRT files found in the directory{Colors.ENDC}",
            "warning"
        )
        sys.exit(0)
    
    # Find matches
    matches = app.find_matches()
    
    # Display results
    app.display_matches(matches)
    
    # Rename files
    if matches:
        app.rename_files(matches, dry_run=not args.execute)
    
    app._print_or_emit(
        f"\n{Colors.OKGREEN}✨ Done!{Colors.ENDC}",
        "info"
    )

if __name__ == "__main__":
    main()
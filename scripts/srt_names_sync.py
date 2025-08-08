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
    def __init__(self, directory: str, provider: LLMProvider, model: str = None):
        self.directory = Path(directory)
        self.provider = provider
        self.model = model or self._get_default_model()
        self.mkv_files: List[MediaFile] = []
        self.srt_files: List[MediaFile] = []
        
        # Initialize LLM clients
        self._init_llm_clients()
        
    def _get_default_model(self) -> str:
        if self.provider == LLMProvider.OPENAI:
            return "gpt-4o-mini"
        elif self.provider == LLMProvider.CLAUDE:
            return "claude-3-haiku-20240307"
    
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
            print(f"{Colors.FAIL}Error initializing LLM client: {e}{Colors.ENDC}")
            sys.exit(1)
    
    def discover_files(self) -> Tuple[List[MediaFile], List[MediaFile]]:
        """Recursively discover .mkv and .srt files in the directory"""
        print(f"{Colors.HEADER}🔍 Discovering media files in: {self.directory}{Colors.ENDC}")
        
        mkv_files = []
        srt_files = []
        
        for file_path in self.directory.rglob('*'):
            if file_path.is_file():
                if file_path.suffix.lower() == '.mkv':
                    mkv_files.append(MediaFile(file_path, file_path.stem, file_path.suffix))
                elif file_path.suffix.lower() == '.srt':
                    srt_files.append(MediaFile(file_path, file_path.stem, file_path.suffix))
        
        print(f"{Colors.OKGREEN}Found {len(mkv_files)} MKV files and {len(srt_files)} SRT files{Colors.ENDC}")
        
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
                # Extract JSON from response if it's wrapped in markdown
                if "```json" in content:
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1)
                elif "```" in content:
                    json_match = re.search(r'```\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1)
                
                return json.loads(content)
            except json.JSONDecodeError:
                print(f"{Colors.WARNING}Failed to parse JSON response: {content}{Colors.ENDC}")
                return {"best_match": None, "confidence": 0.0, "reason": "Failed to parse response"}
        
        except Exception as e:
            print(f"{Colors.FAIL}Error querying LLM: {e}{Colors.ENDC}")
            return {"best_match": None, "confidence": 0.0, "reason": f"Error: {e}"}
    
    def find_matches(self) -> List[MatchResult]:
        """Find matches between MKV and SRT files using LLM"""
        print(f"{Colors.HEADER}🤖 Analyzing file matches with {self.provider.value} ({self.model}){Colors.ENDC}")
        
        matches = []
        
        for mkv_file in tqdm(self.mkv_files, desc="Processing MKV files", 
                           bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'):
            
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
                    matches.append(MatchResult(
                        mkv_file=mkv_file,
                        srt_file=matching_srt,
                        confidence=result["confidence"],
                        reason=result["reason"]
                    ))
            
            # Small delay to respect API rate limits
            time.sleep(0.1)
        
        return matches
    
    def display_matches(self, matches: List[MatchResult]):
        """Display the found matches with fancy formatting"""
        print(f"\n{Colors.HEADER}📋 MATCHING RESULTS{Colors.ENDC}")
        print("=" * 80)
        
        if not matches:
            print(f"{Colors.WARNING}No matches found!{Colors.ENDC}")
            return
        
        for i, match in enumerate(matches, 1):
            confidence_color = Colors.OKGREEN if match.confidence > 0.8 else Colors.WARNING if match.confidence > 0.5 else Colors.FAIL
            
            print(f"\n{Colors.BOLD}Match #{i}:{Colors.ENDC}")
            print(f"  {Colors.OKBLUE}MKV:{Colors.ENDC} {match.mkv_file.name}")
            print(f"  {Colors.OKCYAN}SRT:{Colors.ENDC} {match.srt_file.name}")
            print(f"  {Colors.BOLD}Confidence:{Colors.ENDC} {confidence_color}{match.confidence:.2%}{Colors.ENDC}")
            print(f"  {Colors.BOLD}Reason:{Colors.ENDC} {match.reason}")
    
    def rename_files(self, matches: List[MatchResult], dry_run: bool = True):
        """Rename SRT files to match MKV files"""
        action = "Would rename" if dry_run else "Renaming"
        print(f"\n{Colors.HEADER}🔄 {action} SRT files{Colors.ENDC}")
        
        renamed_count = 0
        
        for match in matches:
            old_path = match.srt_file.path
            new_name = match.mkv_file.name + ".srt"
            new_path = old_path.parent / new_name
            
            if old_path.name == new_name:
                print(f"  {Colors.OKCYAN}SKIP:{Colors.ENDC} {old_path.name} (already correctly named)")
                continue
            
            if new_path.exists():
                print(f"  {Colors.WARNING}SKIP:{Colors.ENDC} {new_name} (target file already exists)")
                continue
            
            print(f"  {Colors.OKGREEN}{'WOULD RENAME' if dry_run else 'RENAME'}:{Colors.ENDC}")
            print(f"    {Colors.FAIL}From:{Colors.ENDC} {old_path.name}")
            print(f"    {Colors.OKGREEN}To:{Colors.ENDC}   {new_name}")
            
            if not dry_run:
                try:
                    old_path.rename(new_path)
                    renamed_count += 1
                except Exception as e:
                    print(f"    {Colors.FAIL}ERROR:{Colors.ENDC} {e}")
            else:
                renamed_count += 1
        
        if dry_run:
            print(f"\n{Colors.WARNING}DRY RUN: {renamed_count} files would be renamed{Colors.ENDC}")
            print(f"{Colors.BOLD}Use --execute to actually rename files{Colors.ENDC}")
        else:
            print(f"\n{Colors.OKGREEN}Successfully renamed {renamed_count} files{Colors.ENDC}")

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
    
    args = parser.parse_args()
    
    # Print banner
    print(f"{Colors.HEADER}")
    print("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    print("┃                  🎬 SRT Names Sync                       ┃")
    print("┃              AI-Powered Subtitle Matching               ┃") 
    print("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    print(f"{Colors.ENDC}")
    
    # Validate directory
    if not Path(args.directory).exists():
        print(f"{Colors.FAIL}Error: Directory '{args.directory}' does not exist{Colors.ENDC}")
        sys.exit(1)
    
    # Initialize app
    provider = LLMProvider(args.provider)
    app = SRTNamesSync(args.directory, provider, args.model)
    
    # Discover files
    mkv_files, srt_files = app.discover_files()
    
    if not mkv_files:
        print(f"{Colors.WARNING}No MKV files found in the directory{Colors.ENDC}")
        sys.exit(0)
    
    if not srt_files:
        print(f"{Colors.WARNING}No SRT files found in the directory{Colors.ENDC}")
        sys.exit(0)
    
    # Find matches
    matches = app.find_matches()
    
    # Display results
    app.display_matches(matches)
    
    # Rename files
    if matches:
        app.rename_files(matches, dry_run=not args.execute)
    
    print(f"\n{Colors.OKGREEN}✨ Done!{Colors.ENDC}")

if __name__ == "__main__":
    main()
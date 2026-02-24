#!/usr/bin/env python3

import os
import re
import argparse
import signal
from openai import OpenAI
from anthropic import Anthropic
from dotenv import load_dotenv
import concurrent.futures
import threading
import queue as _queue
from tqdm import tqdm
import time
import sys
import json
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Global clients (initialized when needed)
openai_client = None
anthropic_client = None
lmstudio_client = None
openrouter_client = None
xai_client = None
mistral_client = None
groq_client = None
deepseek_client = None
moonshot_client = None
gemini_client = None
zai_client = None

def get_openai_client(api_key=None):
    """Get OpenAI client, initializing if needed."""
    global openai_client
    if openai_client is None:
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required")
        openai_client = OpenAI(api_key=api_key)
    return openai_client

def get_anthropic_client(api_key=None):
    """Get Anthropic client, initializing if needed."""
    global anthropic_client
    if anthropic_client is None:
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key is required")
        anthropic_client = Anthropic(api_key=api_key)
    return anthropic_client

def get_lmstudio_client():
    """Get LM Studio client, initializing if needed."""
    global lmstudio_client
    if lmstudio_client is None:
        lmstudio_client = OpenAI(
            base_url="http://localhost:1234/v1",
            api_key="not-needed"
        )
    return lmstudio_client

def get_openrouter_client(api_key=None):
    """Get OpenRouter client, initializing if needed."""
    global openrouter_client
    if openrouter_client is None:
        api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OpenRouter API key is required")
        openrouter_client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    return openrouter_client

def get_xai_client(api_key=None):
    """Get xAI (Grok) client, initializing if needed."""
    global xai_client
    if xai_client is None:
        api_key = api_key or os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError("xAI API key is required")
        xai_client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
    return xai_client

def get_mistral_client(api_key=None):
    """Get Mistral client, initializing if needed."""
    global mistral_client
    if mistral_client is None:
        api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("Mistral API key is required")
        mistral_client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
    return mistral_client

def get_groq_client(api_key=None):
    """Get Groq client, initializing if needed."""
    global groq_client
    if groq_client is None:
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Groq API key is required")
        groq_client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    return groq_client

def get_deepseek_client(api_key=None):
    """Get DeepSeek client, initializing if needed."""
    global deepseek_client
    if deepseek_client is None:
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DeepSeek API key is required")
        deepseek_client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    return deepseek_client

def get_moonshot_client(api_key=None):
    """Get Moonshot (Kimi) client, initializing if needed."""
    global moonshot_client
    if moonshot_client is None:
        api_key = api_key or os.getenv("MOONSHOT_API_KEY")
        if not api_key:
            raise ValueError("Moonshot API key is required")
        moonshot_client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")
    return moonshot_client

def get_gemini_client(api_key=None):
    """Get Google Gemini client (OpenAI-compatible endpoint), initializing if needed."""
    global gemini_client
    if gemini_client is None:
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key is required")
        gemini_client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    return gemini_client

def get_zai_client(api_key=None):
    """Get Z.ai (GLM) client (OpenAI-compatible endpoint), initializing if needed."""
    global zai_client
    if zai_client is None:
        api_key = api_key or os.getenv("ZAI_API_KEY")
        if not api_key:
            raise ValueError("Z.ai API key is required")
        zai_client = OpenAI(api_key=api_key, base_url="https://api.z.ai/api/paas/v4/")
    return zai_client

# Available models
OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo"]
CLAUDE_MODELS = ["claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001", "claude-opus-4-5-20251101"]
OPENROUTER_MODELS = [
    "anthropic/claude-sonnet-4-5-20250929",
    "anthropic/claude-haiku-4-5-20251001",
    "anthropic/claude-opus-4-5-20251101",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "google/gemini-pro-1.5",
    "meta-llama/llama-3.1-405b-instruct",
    "custom"  # Allow custom model IDs
]
LMSTUDIO_MODELS = ["local"]

# Maximum retries for invalid chunks
MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Subtitle output validation
# ---------------------------------------------------------------------------

try:
    import pysrt as _pysrt
    _PYSRT_AVAILABLE = True
except ImportError:
    _PYSRT_AVAILABLE = False

_TIMECODE_PATTERN = re.compile(
    r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})'
)

def _tc_ms(h, m, s, ms):
    return int(h) * 3600_000 + int(m) * 60_000 + int(s) * 1_000 + int(ms)

def _parse_srt_builtin(content):
    """Minimal pure-Python SRT parser. Returns list of (index, start_ms, end_ms, text)."""
    subs = []
    for block in re.split(r'\n[ \t]*\n', content.strip()):
        lines = [l.rstrip() for l in block.strip().splitlines()]
        if not lines:
            continue
        tc_idx = next((i for i, l in enumerate(lines) if _TIMECODE_PATTERN.search(l)), None)
        if tc_idx is None:
            continue
        m = _TIMECODE_PATTERN.search(lines[tc_idx])
        start = _tc_ms(*m.group(1, 2, 3, 4))
        end   = _tc_ms(*m.group(5, 6, 7, 8))
        idx = 0
        if tc_idx > 0 and lines[tc_idx - 1].strip().isdigit():
            idx = int(lines[tc_idx - 1].strip())
        text = '\n'.join(lines[tc_idx + 1:]).strip()
        subs.append((idx, start, end, text))
    return subs


def validate_srt_file(filepath):
    """
    Validate a translated SRT file for format, timing, and content quality.

    Checks performed:
    - File exists and is non-empty
    - UTF-8 encoding (warns on BOM or non-UTF-8)
    - Parseable SRT structure (uses pysrt when available, built-in fallback)
    - At least one subtitle entry
    - Each subtitle: start time < end time
    - Subtitle ordering: no backward time jumps
    - Subtitle overlap detection (> 100 ms overlap flagged)
    - Empty subtitle text
    - Broken encoding replacement characters (U+FFFD)
    - Excessively long lines (> 84 characters)

    Returns dict:
        valid         bool   — False if any error was found
        subtitle_count int
        errors        list   — blocking issues
        warnings      list   — non-blocking quality concerns
        stats         dict   — numeric summary
        parser        str    — 'pysrt' or 'built-in'
    """
    result = {
        "valid": True,
        "subtitle_count": 0,
        "errors": [],
        "warnings": [],
        "stats": {},
        "parser": "pysrt" if _PYSRT_AVAILABLE else "built-in",
    }

    # 1. File existence / size
    if not os.path.isfile(filepath):
        result["valid"] = False
        result["errors"].append(f"Output file not found: {filepath}")
        return result

    file_size = os.path.getsize(filepath)
    if file_size == 0:
        result["valid"] = False
        result["errors"].append("Output file is empty")
        return result

    # 2. Encoding check
    try:
        with open(filepath, 'rb') as fh:
            raw = fh.read()
        content = raw.decode('utf-8')
    except UnicodeDecodeError:
        try:
            content = raw.decode('latin-1')
            result["warnings"].append(
                "Output file is not UTF-8 encoded — some players may display characters incorrectly"
            )
        except Exception as exc:
            result["valid"] = False
            result["errors"].append(f"Cannot decode output file: {exc}")
            return result

    if content.startswith('\ufeff'):
        content = content[1:]
        result["warnings"].append(
            "Output file has a UTF-8 BOM — some subtitle players may show a leading character"
        )

    # 3. Parse
    subs = []  # list of (index, start_ms, end_ms, text)
    if _PYSRT_AVAILABLE:
        try:
            pysrt_file = _pysrt.open(filepath, error_handling=_pysrt.ERROR_LOG)
            for sub in pysrt_file:
                subs.append((sub.index, sub.start.ordinal, sub.end.ordinal, sub.text))
        except Exception as exc:
            result["valid"] = False
            result["errors"].append(f"SRT parse error: {exc}")
            return result
    else:
        try:
            subs = _parse_srt_builtin(content)
        except Exception as exc:
            result["valid"] = False
            result["errors"].append(f"SRT parse error: {exc}")
            return result

    if not subs:
        result["valid"] = False
        result["errors"].append("No subtitle entries found in output file")
        return result

    result["subtitle_count"] = len(subs)

    # 4. Per-subtitle checks
    timing_errors      = []
    ordering_errors    = []
    overlap_warnings   = []
    empty_subs         = []
    encoding_issues    = []
    long_line_subs     = []
    MAX_REPORT = 5

    for i, (idx, start_ms, end_ms, text) in enumerate(subs):
        label = f"#{idx}"

        # 4a. Duration validity (start must be strictly before end)
        if start_ms >= end_ms:
            dur = end_ms - start_ms
            timing_errors.append(f"{label}: start >= end (duration {dur:+d} ms)")

        if i > 0:
            prev_idx, prev_start, prev_end, _ = subs[i - 1]
            prev_label = f"#{prev_idx}"

            # 4b. Ordering: no backward jumps
            if start_ms < prev_start:
                ordering_errors.append(
                    f"{label} starts before {prev_label} ({start_ms} ms < {prev_start} ms)"
                )
            # 4c. Overlap
            elif start_ms < prev_end:
                overlap_ms = prev_end - start_ms
                if overlap_ms > 100:
                    overlap_warnings.append(
                        f"{label} overlaps {prev_label} by {overlap_ms} ms"
                    )

        # 4d. Empty text
        clean_text = re.sub(r'\{[^}]*\}', '', text).strip()  # strip ASS tags
        if not clean_text:
            empty_subs.append(label)

        # 4e. Replacement character (broken encoding)
        if '\ufffd' in text:
            encoding_issues.append(label)

        # 4f. Overly long lines
        for line in text.split('\n'):
            visible = re.sub(r'\{[^}]*\}', '', line).strip()
            if len(visible) > 84:
                long_line_subs.append(f"{label} ({len(visible)} chars)")
                break

    def _add_issues(bucket, label, result_list, max_r=MAX_REPORT):
        if not bucket:
            return
        shown = bucket[:max_r]
        result_list.extend(shown)
        if len(bucket) > max_r:
            result_list.append(f"  … and {len(bucket) - max_r} more")

    _add_issues([f"Timing error — {e}" for e in timing_errors],    "timing",    result["errors"])
    _add_issues([f"Order error — {e}" for e in ordering_errors],   "ordering",  result["errors"])
    _add_issues([f"Overlap — {e}" for e in overlap_warnings],      "overlap",   result["warnings"])

    if empty_subs:
        result["warnings"].append(
            f"{len(empty_subs)} subtitle(s) with empty text: "
            + ", ".join(empty_subs[:MAX_REPORT])
            + (" …" if len(empty_subs) > MAX_REPORT else "")
        )

    if encoding_issues:
        result["warnings"].append(
            f"{len(encoding_issues)} subtitle(s) contain encoding replacement characters (U+FFFD): "
            + ", ".join(encoding_issues[:MAX_REPORT])
            + (" …" if len(encoding_issues) > MAX_REPORT else "")
        )

    if long_line_subs:
        result["warnings"].append(
            f"{len(long_line_subs)} subtitle(s) have lines longer than 84 characters: "
            + ", ".join(long_line_subs[:MAX_REPORT])
            + (" …" if len(long_line_subs) > MAX_REPORT else "")
        )

    # 5. Stats
    total_duration_ms = subs[-1][2] if subs else 0
    result["stats"] = {
        "subtitle_count":   len(subs),
        "timing_errors":    len(timing_errors),
        "ordering_errors":  len(ordering_errors),
        "overlaps":         len(overlap_warnings),
        "empty_subtitles":  len(empty_subs),
        "encoding_issues":  len(encoding_issues),
        "long_lines":       len(long_line_subs),
        "duration_seconds": round(total_duration_ms / 1000, 1),
        "file_size_kb":     round(file_size / 1024, 1),
        "parser":           result["parser"],
    }

    if result["errors"]:
        result["valid"] = False

    return result


def repair_srt_timing(filepath):
    """
    Attempt to fix common timing errors in an SRT file in-place.

    Repairs:
    - start >= end: resets end = start + estimated_duration
      Estimated duration = duration of the next valid subtitle, capped to 3 s,
      with a 1-second minimum so the subtitle is always visible.

    Returns:
        dict: {fixed: int, skipped: int, error: str|None}
              fixed   — number of entries that were corrected
              skipped — entries that could not be repaired
              error   — None on success, error message on failure
    """
    import re as _re

    TIMECODE_RE = _re.compile(
        r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})"
    )

    def tc_to_ms(h, m, s, ms):
        return ((int(h) * 3600) + (int(m) * 60) + int(s)) * 1000 + int(ms)

    def ms_to_tc(total_ms):
        total_ms = max(0, int(round(total_ms)))
        ms = total_ms % 1000
        s = (total_ms // 1000) % 60
        m = (total_ms // 60000) % 60
        h = total_ms // 3600000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    ARROW_RE = _re.compile(
        r"(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})"
    )

    try:
        with open(filepath, 'r', encoding='utf-8-sig', errors='replace') as fh:
            content = fh.read()
    except OSError as exc:
        return {"fixed": 0, "skipped": 0, "error": str(exc)}

    # Split into blocks: index, timecode-line, text, blank
    blocks = _re.split(r'\n\n+', content.strip())
    parsed = []   # (raw_block, start_ms, end_ms, arrow_match_span)

    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            parsed.append((block, None, None, None))
            continue
        # timecode line is usually lines[1], but search all just in case
        tc_line_idx = None
        tc_match = None
        for li, line in enumerate(lines):
            m = ARROW_RE.search(line)
            if m:
                tc_line_idx = li
                tc_match = m
                break
        if tc_match is None:
            parsed.append((block, None, None, None))
            continue

        tcs = TIMECODE_RE.findall(tc_match.group(0))
        if len(tcs) < 2:
            parsed.append((block, None, None, None))
            continue

        start_ms = tc_to_ms(*tcs[0])
        end_ms   = tc_to_ms(*tcs[1])
        parsed.append((block, start_ms, end_ms, (tc_line_idx, tc_match)))

    fixed = 0
    skipped = 0
    new_blocks = []

    for i, (block, start_ms, end_ms, tc_info) in enumerate(parsed):
        if tc_info is None or start_ms is None:
            new_blocks.append(block)
            continue

        if start_ms < end_ms:
            # Already valid
            new_blocks.append(block)
            continue

        # Need to repair: end <= start
        # Estimate a sensible duration from the next valid entry
        estimated_dur = 2000  # 2-second default
        for j in range(i + 1, len(parsed)):
            _, ns, ne, _ = parsed[j]
            if ns is not None and ne is not None and ne > ns:
                estimated_dur = min(ne - ns, 3000)
                break

        new_end_ms = start_ms + max(estimated_dur, 1000)

        # Make sure new end doesn't overlap next subtitle's start
        for j in range(i + 1, len(parsed)):
            _, ns, ne, _ = parsed[j]
            if ns is not None and ns > start_ms:
                new_end_ms = min(new_end_ms, ns - 50)
                break

        new_end_ms = max(new_end_ms, start_ms + 100)  # at least 100 ms

        tc_line_idx, tc_match = tc_info
        lines = block.strip().splitlines()
        old_tc_line = lines[tc_line_idx]
        new_tc_line = old_tc_line[:tc_match.start(2)] + ms_to_tc(new_end_ms) + old_tc_line[tc_match.end(2):]
        lines[tc_line_idx] = new_tc_line
        new_blocks.append('\n'.join(lines))
        fixed += 1

    if fixed == 0:
        return {"fixed": 0, "skipped": skipped, "error": None}

    try:
        with open(filepath, 'w', encoding='utf-8') as fh:
            fh.write('\n\n'.join(new_blocks) + '\n')
    except OSError as exc:
        return {"fixed": 0, "skipped": 0, "error": str(exc)}

    return {"fixed": fixed, "skipped": skipped, "error": None}


# Global JSONL mode flag
JSONL_MODE = False


class FatalTranslationError(Exception):
    """Exception for fatal errors that should stop all translation immediately."""
    pass


def is_authentication_error(error):
    """Check if an error is an authentication/authorization error that shouldn't be retried."""
    error_str = str(error).lower()
    # Check for common authentication error patterns
    auth_patterns = [
        'authentication_error',
        'invalid x-api-key',
        'invalid api key',
        'invalid_api_key',
        'unauthorized',
        'error code: 401',
        'status code: 401',
        '401 unauthorized',
        'api key is required',
        'api_key_invalid',
    ]
    return any(pattern in error_str for pattern in auth_patterns)

def emit_jsonl(event_type, msg, progress=None, data=None):
    """Emit a JSONL event to stdout if in JSONL mode"""
    if not JSONL_MODE:
        return
    
    event = {
        "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "stage": "translate",
        "type": event_type,
        "msg": msg
    }
    
    if progress is not None:
        event["progress"] = progress
    
    if data is not None:
        event["data"] = data
    
    try:
        print(json.dumps(event), flush=True)
    except BrokenPipeError:
        # Handle broken pipe gracefully - parent process may have closed
        sys.exit(0)
    except Exception as e:
        # Log to stderr if stdout fails
        print(f"WARNING: Failed to emit JSONL: {e}", file=sys.stderr, flush=True)

def log_output(msg, color_code="", jsonl_type=None, progress=None, data=None):
    """Output message with color in normal mode or JSONL in JSONL mode"""
    if JSONL_MODE and jsonl_type:
        emit_jsonl(jsonl_type, msg, progress, data)
    elif not JSONL_MODE:
        try:
            print(f"{color_code}{msg}\033[0m" if color_code else msg)
        except BrokenPipeError:
            # Handle broken pipe gracefully
            sys.exit(0)

def animate_progress(description):
    if JSONL_MODE:
        # In JSONL mode, don't animate, just emit a start event
        emit_jsonl("info", description)
        while True:
            yield
    else:
        animation = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0
        while True:
            sys.stdout.write(f"\r\033[1;36m{animation[idx]} {description}\033[0m")
            sys.stdout.flush()
            time.sleep(0.1)  # Add a small delay to make animation visible
            idx = (idx + 1) % len(animation)
            yield

def split_into_chunks(content, chunk_size=50):
    """Split content into chunks of approximately chunk_size subtitles each"""
    # Split content into individual subtitle blocks
    subtitle_blocks = []
    current_block = []
    
    for line in content.strip().split('\n'):
        current_block.append(line)
        if not line.strip():  # Empty line indicates end of subtitle block
            if current_block:
                subtitle_block = '\n'.join(current_block).strip()
                if subtitle_block:  # Only add non-empty blocks
                    subtitle_blocks.append(subtitle_block)
                current_block = []
    
    # Add the last block if it exists
    if current_block:
        subtitle_block = '\n'.join(current_block).strip()
        if subtitle_block:
            subtitle_blocks.append(subtitle_block)
    
    # Split blocks into chunks, ensuring each chunk ends with an empty line
    chunks = []
    current_chunk = []
    current_size = 0
    
    for block in subtitle_blocks:
        current_chunk.append(block)
        current_size += 1
        
        if current_size >= chunk_size:
            chunk_text = '\n\n'.join(current_chunk)
            if not chunk_text.endswith('\n'):
                chunk_text += '\n'
            chunks.append(chunk_text)
            current_chunk = []
            current_size = 0
    
    # Add any remaining subtitles
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        if not chunk_text.endswith('\n'):
            chunk_text += '\n'
        chunks.append(chunk_text)
    
    return chunks

def get_system_prompt(provider, source_lang="English", target_lang="Bulgarian", context=None):
    _openai_compat = {"openai", "openrouter", "xai", "mistral", "groq", "deepseek", "moonshot", "gemini", "zai"}
    if provider in _openai_compat:
        prompt = f"""You are a translator that translates subtitles from {source_lang} to {target_lang}.
        CRITICAL RULES:
        1. Output ONLY the translated subtitles
        2. DO NOT add any formatting marks like ``` or markdown
        3. DO NOT add any explanatory text
        4. Keep ALL numbers exactly as they are
        5. Keep ALL timecodes EXACTLY as they are, including:
           - Keep the leading "00:" even for short times
           - Keep ALL digits and punctuation (,-->)
           - Example: 00:01:23,456 --> 00:01:25,789
        6. Translate ONLY the text content
        7. Keep ALL line breaks exactly as they are
        8. Keep ALL empty lines exactly as they are
        9. DO NOT add or remove any lines
        10. DO NOT wrap the output in any code block or formatting

        Output the translation EXACTLY as provided, with NO additional formatting."""
    elif provider == "claude":
        prompt = f"""IMPORTANT: You are a subtitle translator working in COMPLETE SILENCE mode.
        YOUR TASK:
        - Translate ALL provided subtitles from {source_lang} to {target_lang}
        - Process the ENTIRE chunk of subtitles provided, no matter how long
        - NEVER stop mid-way or ask to continue
        - NEVER add ANY commentary or questions
        
        ABSOLUTE RULES FOR TIMECODES:
        1. NEVER modify timecode format
        2. ALL timecodes MUST keep leading "00:" even for short times
        3. ALL timecodes MUST be in format: 00:MM:SS,mmm --> 00:MM:SS,mmm
        4. NEVER remove leading zeros
        5. NEVER change commas to dots in timecodes
        6. NEVER change the --> separator
        
        ABSOLUTE RULES FOR CONTENT:
        1. Output ONLY the translated subtitles
        2. Process ALL subtitles in the chunk, from first to last
        3. Keep ALL numbers exactly as they are
        4. Keep ALL line breaks and empty lines exactly as they are
        5. DO NOT add ANY text that isn't a direct translation
        6. DO NOT ask questions or add notes
        7. DO NOT mention translation progress
        8. DO NOT offer to continue
        9. NEVER stop before translating the entire chunk
        
        EXAMPLE TIMECODE FORMAT TO PRESERVE:
        00:01:23,456 --> 00:01:25,789
        
        REMEMBER: You are in COMPLETE SILENCE mode - output ONLY translations, nothing else."""
    else:  # lmstudio - simpler prompt for local models
        prompt = f"""You are a translator. Translate subtitles from {source_lang} to {target_lang}.
        Rules:
        1. Keep ALL numbers exactly as they are
        2. Keep ALL timecodes exactly as they are, including leading "00:"
        3. Example timecode format: 00:01:23,456 --> 00:01:25,789
        4. Keep ALL line breaks and empty lines
        5. Only translate the text content
        6. Do not add any extra text or formatting"""

    if context:
        prompt += f"\n\nContext about the film/show: {context}"
        prompt += "\nUse this context to provide more accurate and contextually appropriate translations."
    
    return prompt

def clean_openai_response(text):
    # Remove markdown or code block formatting
    text = re.sub(r'^```\w*\n', '', text)  # Remove opening code block
    text = re.sub(r'\n```$', '', text)     # Remove closing code block
    text = text.strip()
    return text

def clean_claude_response(text):
    # Remove any lines that contain common Claude commentary
    lines = text.split('\n')
    cleaned_lines = []
    skip_next_empty = False
    
    for line in lines:
        # Skip lines containing common Claude commentary
        if any(phrase in line.lower() for phrase in [
            "here's the", "would you like", "translation", "i will", "continue",
            "note:", "proceeding with", "proceed with", "continuing with"
        ]):
            skip_next_empty = True
            continue
            
        # Skip empty line after removed commentary
        if skip_next_empty and not line.strip():
            skip_next_empty = False
            continue
            
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def normalize_timestamp(line):
    """
    Normalizes the timestamp format to ensure exactly one space around -->
    Also tries to fix timestamps without --> by adding it if the format matches two timestamps
    Example: '00:00:01,000-->00:00:02,000' becomes '00:00:01,000 --> 00:00:02,000'
    Example: '00:00:01,000 00:00:02,000' becomes '00:00:01,000 --> 00:00:02,000'
    """
    # Try to match two timestamps with or without -->
    timestamp = r'00:\d{2}:\d{2},\d{3}'
    full_pattern = fr'{timestamp}\s*(?:-->)?\s*{timestamp}'
    if not re.match(full_pattern, line):
        return line
    
    # Split on --> if it exists, otherwise on whitespace
    if '-->' in line:
        parts = re.split(r'\s*-->\s*', line)
    else:
        parts = re.split(r'\s+', line)
    
    if len(parts) == 2:
        return f"{parts[0].strip()} --> {parts[1].strip()}"
    return line

def validate_srt_chunk(chunk, strict_numbering=False):
    """
    Validates if a chunk follows SRT format rules.
    Returns (is_valid, error_message) or (is_valid, normalized_text)
    """
    lines = chunk.strip().split('\n')
    if not lines:
        return False, "Empty chunk"

    # First fix any common issues
    lines = fix_subtitle_text(lines)

    # State tracking
    last_number = None
    state = 'number'  # States: number, timestamp, text
    subtitle_count = 0
    normalized_lines = []
    current_subtitle_lines = []  # Track lines of current subtitle for error context
    all_subtitle_blocks = []     # Store all subtitle blocks
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        current_subtitle_lines.append(line)
        
        if state == 'number':
            if not line:
                normalized_lines.append(line)
                i += 1
                continue
            if not line.isdigit():
                # Show context around the error
                block_index = len(all_subtitle_blocks)
                context_start = max(0, block_index - 2)
                context_end = block_index + 3
                error_context = []
                
                for block in all_subtitle_blocks[context_start:block_index]:
                    error_context.extend(block)
                    error_context.append('')
                
                error_context.extend(current_subtitle_lines)
                error_context.append('⚠️ Error occurred here ⚠️')
                
                debug_text = '\n'.join(error_context)
                if not JSONL_MODE:
                    tqdm.write(f"\n\033[96mContext around error:\n{debug_text}\033[0m")
                else:
                    emit_jsonl("warning", f"Context around error: {debug_text}")
                return False, f"Expected subtitle number, got: {line}"
            
            last_number = int(line)
            state = 'timestamp'
            normalized_lines.append(line)
            
        elif state == 'timestamp':
            if not line:
                return False, f"Unexpected empty line after subtitle number {last_number}"
            
            # Try to normalize the timestamp first
            normalized_timestamp = normalize_timestamp(line)
            if '-->' in normalized_timestamp:
                normalized_lines.append(normalized_timestamp)
                state = 'text'
            else:
                # Show context around the error
                block_index = len(all_subtitle_blocks)
                context_start = max(0, block_index - 2)
                context_end = block_index + 3
                error_context = []
                
                for block in all_subtitle_blocks[context_start:block_index]:
                    error_context.extend(block)
                    error_context.append('')
                
                error_context.extend(current_subtitle_lines)
                error_context.append('⚠️ Error occurred here ⚠️')
                
                debug_text = '\n'.join(error_context)
                if not JSONL_MODE:
                    tqdm.write(f"\n\033[96mContext around error:\n{debug_text}\033[0m")
                else:
                    emit_jsonl("warning", f"Context around error: {debug_text}")
                return False, f"Invalid timestamp format: {line}"
            
        elif state == 'text':
            if not line:  # Empty line marks end of subtitle
                state = 'number'
                subtitle_count += 1
                all_subtitle_blocks.append(current_subtitle_lines)
                current_subtitle_lines = []
            normalized_lines.append(line)
        
        i += 1
    
    # Handle the last subtitle
    if state == 'text':
        subtitle_count += 1
        all_subtitle_blocks.append(current_subtitle_lines)
        # Always add empty line after text
        if normalized_lines[-1].strip():
            normalized_lines.append('')
    
    # Final validation
    if subtitle_count == 0:
        return False, "No valid subtitles found in chunk"
    
    # Process the lines one more time to ensure empty lines between subtitles
    result = []
    i = 0
    while i < len(normalized_lines):
        line = normalized_lines[i]
        result.append(line)
        
        # If this is subtitle text and next is a number, add empty line
        if (i < len(normalized_lines) - 1 and 
            not line.isdigit() and 
            '-->' not in line and 
            normalized_lines[i + 1].isdigit() and
            line.strip()):  # Only if current line is not empty
            result.append('')
        
        i += 1
    
    # Ensure chunk ends with empty line
    if result:
        result.append('')
    
    # Return the normalized chunk
    return True, '\n'.join(result)

def fix_subtitle_text(lines):
    """
    Fixes common subtitle text issues:
    - Splits merged subtitle numbers
    - Ensures empty lines between subtitles
    Returns list of fixed lines
    """
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # If we find a subtitle number in the middle of text
        if i > 0 and line.isdigit():
            prev_line = fixed_lines[-1]
            if prev_line.endswith(line):
                # Split the number from text
                fixed_lines[-1] = prev_line[:-len(line)].rstrip('.')
                fixed_lines.append('')
                fixed_lines.append(line)
            else:
                # Add empty line between subtitles if missing
                if fixed_lines and fixed_lines[-1].strip():
                    fixed_lines.append('')
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
        
        i += 1
    
    # Process the lines to ensure empty lines between subtitles
    result = []
    i = 0
    while i < len(fixed_lines):
        line = fixed_lines[i]
        result.append(line)
        
        # If this is a subtitle text (not a number and not a timestamp)
        if (i < len(fixed_lines) - 1 and 
            not line.isdigit() and 
            '-->' not in line and 
            fixed_lines[i + 1].isdigit()):
            result.append('')
            
        i += 1
    
    # Ensure chunk ends with empty line
    if result and result[-1].strip():
        result.append('')
    
    return result

def ensure_srt_format(text):
    """
    Ensures the text has exactly one empty line at the end.
    Returns the formatted text.
    """
    # Remove any trailing whitespace first
    text = text.rstrip()
    
    # Add exactly one empty line
    return text + '\n'

def ensure_subtitle_spacing(text):
    """
    Ensures proper spacing between subtitles:
    - Exactly one empty line between subtitles
    - Preserves all subtitle content
    """
    if not text.strip():
        return text
        
    # Split into lines, preserving trailing whitespace info but normalizing
    lines = text.split('\n')
    
    # Process lines to ensure proper SRT format
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i].rstrip()  # Remove trailing whitespace
        
        # If this is a subtitle number
        if line.isdigit():
            # Add empty line before subtitle number if not at start and previous line wasn't empty
            if result and result[-1].strip():
                result.append('')
            result.append(line)
            
            # Add timestamp (next line)
            i += 1
            if i < len(lines):
                timestamp = lines[i].rstrip()
                result.append(timestamp)
                
                # Add subtitle text lines until we hit empty line or next number
                i += 1
                while i < len(lines):
                    current_line = lines[i].rstrip()
                    
                    # If we hit another subtitle number, break
                    if current_line.isdigit():
                        i -= 1  # Back up to process this number
                        break
                    
                    # Add the line (could be text or empty)
                    result.append(current_line)
                    
                    # If this was an empty line, we're done with this subtitle
                    if not current_line.strip():
                        break
                        
                    i += 1
        else:
            # Non-number line, just add it
            result.append(line)
        
        i += 1
    
    # Ensure file ends with exactly one empty line
    while result and not result[-1].strip():
        result.pop()
    result.append('')
    
    return '\n'.join(result)

def retry_translation(chunk, provider, model, system_prompt, max_retries=MAX_RETRIES):
    """
    Attempts to translate a chunk with retries if validation fails.
    Returns (translated_text, success)
    """
    chunk_info = _format_chunk_info(chunk)
    for attempt in range(max_retries):
        try:
            if provider == "openai":
                translated = translate_with_openai(chunk, model, system_prompt)
            elif provider == "claude":
                translated = translate_with_claude(chunk, model, system_prompt)
            elif provider == "openrouter":
                translated = translate_with_openrouter(chunk, model, system_prompt)
            elif provider == "xai":
                translated = translate_with_xai(chunk, model, system_prompt)
            elif provider == "mistral":
                translated = translate_with_mistral(chunk, model, system_prompt)
            elif provider == "groq":
                translated = translate_with_groq(chunk, model, system_prompt)
            elif provider == "deepseek":
                translated = translate_with_deepseek(chunk, model, system_prompt)
            elif provider == "moonshot":
                translated = translate_with_moonshot(chunk, model, system_prompt)
            elif provider == "gemini":
                translated = translate_with_gemini(chunk, model, system_prompt)
            elif provider == "zai":
                translated = translate_with_zai(chunk, model, system_prompt)
            else:  # lmstudio / local
                translated = translate_with_lmstudio(chunk, model, system_prompt)

            # Ensure proper SRT format
            translated = ensure_srt_format(translated)

            # Validate and normalize the translation
            is_valid, result = validate_srt_chunk(translated)
            if is_valid:
                return result, True  # Return normalized text

            # If invalid, emit detailed diagnostics
            response_sample = _format_response_sample(translated)
            diag_msg = (
                f"Attempt {attempt + 1}/{max_retries} — chunk: {chunk_info}\n"
                f"Validation error: {result}\n"
                f"AI response: {response_sample}"
            )
            if not JSONL_MODE:
                tqdm.write(f"\n\033[95m{diag_msg}\033[0m")
            else:
                emit_jsonl("warning", diag_msg)

        except Exception as e:
            error_msg = f"Attempt {attempt + 1}/{max_retries} failed (chunk: {chunk_info}): {str(e)}"
            if not JSONL_MODE:
                tqdm.write(f"\033[91m❌ {error_msg}\033[0m")
            else:
                emit_jsonl("error", error_msg)

    # If all retries failed, return the original chunk and failure status
    return chunk, False

def split_chunk_by_subtitles(chunk):
    """
    Split a chunk into two roughly equal parts, ensuring we split at subtitle boundaries.
    Returns tuple of (first_half, second_half)
    """
    lines = chunk.split('\n')
    subtitle_starts = [i for i, line in enumerate(lines) if line.strip().isdigit()]
    
    if len(subtitle_starts) <= 1:
        return chunk, ""  # Can't split if only one subtitle
        
    # Find middle subtitle index
    mid_point = len(subtitle_starts) // 2
    split_index = subtitle_starts[mid_point]
    
    # Ensure first half ends with a newline
    first_half = '\n'.join(lines[:split_index]).rstrip() + '\n'
    
    # Ensure second half starts with a newline if it doesn't already
    second_half_lines = lines[split_index:]
    if second_half_lines and second_half_lines[0].strip():  # If first line isn't empty
        second_half = '\n' + '\n'.join(second_half_lines)
    else:
        second_half = '\n'.join(second_half_lines)
    
    return first_half, second_half

def _format_chunk_info(chunk):
    """Return a compact summary of a chunk for diagnostic messages."""
    lines = chunk.strip().split('\n')
    numbers = [l.strip() for l in lines if l.strip().isdigit()]
    sub_range = f"subs #{numbers[0]}–#{numbers[-1]}" if len(numbers) >= 2 else (
        f"sub #{numbers[0]}" if numbers else "no sub numbers found"
    )
    return f"{len(numbers)} subtitles ({sub_range}), {len(lines)} lines, {len(chunk)} chars"


def _format_response_sample(raw):
    """Return a diagnostic string showing the AI response with metadata."""
    if not raw or not raw.strip():
        return f"[EMPTY — {len(raw)} chars, repr: {repr(raw[:80])}]"
    all_lines = raw.split('\n')
    total = len(all_lines)
    # Show up to 20 lines; if longer show first 15 + last 3
    if total <= 20:
        sample = '\n'.join(all_lines)
    else:
        sample = '\n'.join(all_lines[:15]) + f"\n... ({total - 18} lines omitted) ...\n" + '\n'.join(all_lines[-3:])
    return f"[{len(raw)} chars, {total} lines]\n{sample}"


def retry_translation_with_split(chunk, provider, model, system_prompt, split_depth=0, max_splits=2):
    """
    Attempts to translate a chunk, if fails, splits it and tries each half.
    Returns (translated_text, success)
    """
    chunk_info = _format_chunk_info(chunk)
    try:
        if provider == "openai":
            translated = translate_with_openai(chunk, model, system_prompt)
        elif provider == "claude":
            translated = translate_with_claude(chunk, model, system_prompt)
        elif provider == "openrouter":
            translated = translate_with_openrouter(chunk, model, system_prompt)
        elif provider == "xai":
            translated = translate_with_xai(chunk, model, system_prompt)
        elif provider == "mistral":
            translated = translate_with_mistral(chunk, model, system_prompt)
        elif provider == "groq":
            translated = translate_with_groq(chunk, model, system_prompt)
        elif provider == "deepseek":
            translated = translate_with_deepseek(chunk, model, system_prompt)
        elif provider == "moonshot":
            translated = translate_with_moonshot(chunk, model, system_prompt)
        elif provider == "gemini":
            translated = translate_with_gemini(chunk, model, system_prompt)
        elif provider == "zai":
            translated = translate_with_zai(chunk, model, system_prompt)
        else:  # lmstudio / local
            translated = translate_with_lmstudio(chunk, model, system_prompt)

        # Ensure proper SRT format and spacing
        translated = ensure_srt_format(translated)
        translated = ensure_subtitle_spacing(translated)

        # Validate the translation
        is_valid, result = validate_srt_chunk(translated)
        if is_valid:
            return result, True

        # If invalid, emit detailed diagnostics
        response_sample = _format_response_sample(translated)
        diag_msg = (
            f"Chunk validation failed (depth={split_depth}) — input: {chunk_info}\n"
            f"Validation error: {result}\n"
            f"AI response: {response_sample}"
        )
        if not JSONL_MODE:
            tqdm.write(f"\n\033[95m{diag_msg}\033[0m")
        else:
            emit_jsonl("warning", diag_msg)

    except Exception as e:
        error_msg = f"Translation API error (depth={split_depth}, chunk: {chunk_info}): {str(e)}"
        if not JSONL_MODE:
            tqdm.write(f"\033[91m❌ {error_msg}\033[0m")
        else:
            emit_jsonl("error", error_msg)

        # Check if this is an authentication error - if so, stop immediately
        if is_authentication_error(e):
            raise FatalTranslationError(f"Authentication failed: {str(e)}")

    # If we've reached max splits, return the original chunk with a warning
    if split_depth >= max_splits:
        warning_msg = f"Max split depth reached — giving up on chunk: {chunk_info}"
        if not JSONL_MODE:
            tqdm.write(f"\033[93m⚠️ {warning_msg}\033[0m")
        else:
            emit_jsonl("warning", warning_msg)
        return chunk, False
    
    # Split the chunk and try each half
    first_half, second_half = split_chunk_by_subtitles(chunk)
    
    # If we couldn't split further, return the original
    if not second_half:
        return chunk, False
    
    split_msg = f"Splitting chunk at depth {split_depth + 1} — {chunk_info}"
    if not JSONL_MODE:
        tqdm.write(f"\n\033[96m{split_msg}\033[0m")
    else:
        emit_jsonl("info", split_msg)
    
    # Translate each half recursively
    first_translated, first_success = retry_translation_with_split(
        first_half, provider, model, system_prompt, 
        split_depth=split_depth + 1, max_splits=max_splits
    )
    
    second_translated, second_success = retry_translation_with_split(
        second_half, provider, model, system_prompt, 
        split_depth=split_depth + 1, max_splits=max_splits
    )
    
    # Combine the results ensuring no content loss
    # Remove trailing newlines from first part and leading newlines from second part
    first_clean = first_translated.rstrip('\n')
    second_clean = second_translated.lstrip('\n')
    
    # Combine with proper spacing
    if first_clean and second_clean:
        combined = first_clean + '\n\n' + second_clean
    elif first_clean:
        combined = first_clean
    elif second_clean:
        combined = second_clean
    else:
        combined = ""
    
    # Ensure proper formatting
    combined = ensure_subtitle_spacing(combined)
    
    # Return combined result and overall success status
    return combined, (first_success and second_success)

def translate_with_openai(content, model, system_prompt):
    client = get_openai_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Translate this content to Bulgarian. Output ONLY the translation with NO formatting:\n\n{content}"}
        ],
        max_tokens=_estimate_max_tokens(content),
    )
    translated_text = _check_openai_response(response, f"model={model}")
    return clean_openai_response(translated_text)

def translate_with_claude(content, model, system_prompt):
    # Set max tokens based on model
    max_tokens = 8192 if "haiku" in model.lower() else 100000
    
    client = get_anthropic_client()
    response = client.messages.create(
        model=model,
        system=system_prompt,
        max_tokens=max_tokens,  # Use model-specific token limit
        temperature=0,  # Make output more deterministic
        messages=[{
            "role": "user",
            "content": f"TRANSLATE TO BULGARIAN - OUTPUT ONLY TRANSLATION:\n\n{content}"
        }]
    )
    translated_text = response.content[0].text.strip()
    return clean_claude_response(translated_text)

def translate_with_lmstudio(content, model, system_prompt):
    try:
        client = get_lmstudio_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Translate this content to Bulgarian. Output ONLY the translation with NO formatting:\n\n{content}"}
            ],
            temperature=0.3,  # Lower temperature for more consistent output
            max_tokens=_estimate_max_tokens(content),
        )
        translated_text = _check_openai_response(response, "lmstudio")
        return clean_openai_response(translated_text)
    except Exception as e:
        error_msg = f"Error with LM Studio: {str(e)}"
        helper_msg = "Make sure LM Studio is running and a model is loaded."
        if not JSONL_MODE:
            print(f"\n⚠️ {error_msg}")
            print(helper_msg)
        else:
            emit_jsonl("error", error_msg)
            emit_jsonl("error", helper_msg)
        sys.exit(1)

def translate_with_openrouter(content, model, system_prompt):
    client = get_openrouter_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Translate this content. Output ONLY the translation with NO formatting:\n\n{content}"}
        ],
        temperature=0.1,
        max_tokens=_estimate_max_tokens(content),
    )
    translated_text = _check_openai_response(response, f"model={model}")
    return clean_openai_response(translated_text)

def _estimate_max_tokens(content: str) -> int:
    """
    Estimate the max_tokens needed to return a full translation of *content*.

    Heuristic:
      - Mixed SRT content (timecodes, numbers, text) tokenises at ~3.5 chars/token.
      - Target language may expand by up to 50 % vs. source.
      - Apply a 1.5× safety buffer.
      Floor at 4096, ceiling at 32768 (supported by virtually every provider).
    """
    estimated = int(len(content) / 3.5 * 1.5)
    return max(4096, min(estimated, 32768))


def _check_openai_response(response, context_label: str) -> str:
    """
    Extract text from an OpenAI-compatible response, raising a descriptive
    error when the model returns empty content or stopped for a bad reason.
    """
    choice = response.choices[0]
    finish_reason = getattr(choice, "finish_reason", "unknown")
    content = choice.message.content or ""
    content = content.strip()

    if not content:
        raise ValueError(
            f"Model returned empty content for {context_label} "
            f"(finish_reason={finish_reason!r}). "
            "Possible causes: content_filter, provider rate-limit, "
            "model refusing large input, or max_tokens exhausted."
        )
    if finish_reason == "length":
        # Content was cut off — raise so the caller can split and retry cleanly
        # rather than receiving truncated (unparseable) output.
        raise ValueError(
            f"Response for {context_label} was TRUNCATED by token limit "
            f"(finish_reason=length). Chunk will be split and retried automatically."
        )
    return content


def _translate_with_openai_compat(client, content, model, system_prompt):
    """Generic translate using any OpenAI-compatible client."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Translate this content. Output ONLY the translation with NO formatting:\n\n{content}"}
        ],
        temperature=0.1,
        max_tokens=_estimate_max_tokens(content),
    )
    translated_text = _check_openai_response(response, f"model={model}")
    return clean_openai_response(translated_text)

def translate_with_xai(content, model, system_prompt):
    return _translate_with_openai_compat(get_xai_client(), content, model, system_prompt)

def translate_with_mistral(content, model, system_prompt):
    return _translate_with_openai_compat(get_mistral_client(), content, model, system_prompt)

def translate_with_groq(content, model, system_prompt):
    return _translate_with_openai_compat(get_groq_client(), content, model, system_prompt)

def translate_with_deepseek(content, model, system_prompt):
    return _translate_with_openai_compat(get_deepseek_client(), content, model, system_prompt)

def translate_with_moonshot(content, model, system_prompt):
    return _translate_with_openai_compat(get_moonshot_client(), content, model, system_prompt)

def translate_with_gemini(content, model, system_prompt):
    return _translate_with_openai_compat(get_gemini_client(), content, model, system_prompt)

def translate_with_zai(content, model, system_prompt):
    return _translate_with_openai_compat(get_zai_client(), content, model, system_prompt)

# ---------------------------------------------------------------------------
# Structured (text-only) translation — the preferred approach
# ---------------------------------------------------------------------------

def _parse_srt_to_records(content: str) -> list:
    """
    Parse SRT content into a list of dicts: {index, timecode_line, text}.
    Multi-line subtitle text is preserved with embedded \\n.
    """
    records = []
    for block in re.split(r'\n[ \t]*\n', content.strip()):
        lines = [l.rstrip() for l in block.strip().splitlines()]
        if not lines:
            continue
        tc_idx = next((i for i, l in enumerate(lines) if _TIMECODE_PATTERN.search(l)), None)
        if tc_idx is None:
            continue
        idx = (int(lines[tc_idx - 1]) if tc_idx > 0 and lines[tc_idx - 1].strip().isdigit()
               else len(records) + 1)
        timecode_line = lines[tc_idx]
        text = '\n'.join(lines[tc_idx + 1:]).strip()
        records.append({'index': idx, 'timecode': timecode_line, 'text': text})
    return records


def _reconstruct_srt(records: list, translated_texts: list) -> str:
    """Reconstruct SRT from original records + translated text list."""
    blocks = []
    for rec, text in zip(records, translated_texts):
        blocks.append(f"{rec['index']}\n{rec['timecode']}\n{text}")
    return '\n\n'.join(blocks) + '\n'


def _timecode_start_ms(timecode_line: str) -> int:
    """Extract start time in milliseconds from a timecode line."""
    m = _TIMECODE_PATTERN.search(timecode_line)
    return _tc_ms(*m.group(1, 2, 3, 4)) if m else 0


def _ms_to_hhmm(ms: int) -> str:
    """Format milliseconds as HH:MM for compact display."""
    s = ms // 1000
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"


def _group_consecutive(indices: list) -> list:
    """
    Group a sorted list of integers into consecutive ranges.
    Returns list of (start, end) inclusive tuples.
    """
    if not indices:
        return []
    groups, start, prev = [], indices[0], indices[0]
    for i in indices[1:]:
        if i == prev + 1:
            prev = i
        else:
            groups.append((start, prev))
            start = prev = i
    groups.append((start, prev))
    return groups


def _call_provider_raw(content_for_tokens: str, user_message: str,
                       provider: str, model: str, system_prompt: str,
                       _token_sink=None) -> str:
    """
    Call the appropriate LLM provider with a fully custom user_message.
    Returns the raw (stripped) response text.
    Uses _estimate_max_tokens based on content_for_tokens size.
    If _token_sink is provided, calls _token_sink(prompt_tokens, completion_tokens)
    after each successful API call for cost tracking.
    """
    max_tok = _estimate_max_tokens(content_for_tokens)

    if provider == "openai":
        client = get_openai_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_message}],
            max_tokens=max_tok,
        )
        if _token_sink and response.usage:
            _token_sink(response.usage.prompt_tokens, response.usage.completion_tokens)
        return _check_openai_response(response, f"model={model}")

    elif provider == "claude":
        max_tokens_claude = 8192 if "haiku" in model.lower() else 100000
        client = get_anthropic_client()
        response = client.messages.create(
            model=model, system=system_prompt,
            max_tokens=max_tokens_claude, temperature=0,
            messages=[{"role": "user", "content": user_message}],
        )
        if _token_sink and response.usage:
            _token_sink(response.usage.input_tokens, response.usage.output_tokens)
        return clean_claude_response(response.content[0].text.strip())

    elif provider == "openrouter":
        client = get_openrouter_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_message}],
            temperature=0.1, max_tokens=max_tok,
        )
        if _token_sink and response.usage:
            _token_sink(response.usage.prompt_tokens, response.usage.completion_tokens)
        return _check_openai_response(response, f"model={model}")

    else:
        _compat_clients = {
            "xai": get_xai_client, "mistral": get_mistral_client,
            "groq": get_groq_client, "deepseek": get_deepseek_client,
            "moonshot": get_moonshot_client, "gemini": get_gemini_client,
            "zai": get_zai_client,
        }
        client = _compat_clients[provider]() if provider in _compat_clients else get_lmstudio_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_message}],
            temperature=0.1, max_tokens=max_tok,
        )
        if _token_sink and response.usage:
            _token_sink(response.usage.prompt_tokens, response.usage.completion_tokens)
        return _check_openai_response(response, f"model={model}")


def _parse_json_translation(raw: str, expected_count: int) -> list:
    """
    Extract a JSON array of strings from an LLM response.
    Raises ValueError if parsing fails or element count doesn't match.
    """
    # Strip markdown code fences
    raw = re.sub(r'^```[a-z]*\n?', '', raw.strip())
    raw = re.sub(r'\n?```$', '', raw).strip()

    def _try_extract(text):
        result = json.loads(text)
        if isinstance(result, list):
            return result
        # Unwrap common wrapper keys
        for key in ('translations', 't', 'result', 'data', 'strings', 'output'):
            if isinstance(result.get(key), list):
                return result[key]
        return None

    # 1. Try the whole string
    try:
        arr = _try_extract(raw)
        if arr is not None:
            if len(arr) != expected_count:
                raise ValueError(
                    f"Count mismatch: sent {expected_count} texts, got {len(arr)} back")
            return arr
    except json.JSONDecodeError:
        pass

    # 2. Extract the first [...] block from the response
    m = re.search(r'\[.*\]', raw, re.DOTALL)
    if m:
        try:
            arr = json.loads(m.group(0))
            if isinstance(arr, list):
                if len(arr) != expected_count:
                    raise ValueError(
                        f"Count mismatch: sent {expected_count} texts, got {len(arr)} back")
                return arr
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not parse a JSON array from response "
        f"(expected {expected_count} strings). "
        f"Response preview: {raw[:300]!r}")


def _translate_chunk_json(texts: list, provider: str, model: str,
                          source_lang: str, target_lang: str, context: str = None,
                          _token_sink=None) -> list:
    """
    Translate a list of plain-text subtitle strings via JSON array format.
    Sends only the text — no timecodes, no SRT syntax.
    Returns a translated list of the same length.
    """
    system_prompt = (
        f"You are a subtitle translator. "
        f"Translate each string from {source_lang} to {target_lang}.\n"
        f"Rules:\n"
        f"1. Return ONLY a valid JSON array of strings.\n"
        f"2. The array MUST have exactly {len(texts)} elements.\n"
        f"3. Preserve \\n (newline) characters within strings.\n"
        f"4. No explanations, no markdown, no commentary."
    )
    if context:
        system_prompt += f"\n\nFilm/show context: {context}"

    payload = json.dumps(texts, ensure_ascii=False)
    user_message = (
        f"Translate these {len(texts)} subtitle strings "
        f"from {source_lang} to {target_lang}. "
        f"Return ONLY the JSON array:\n\n{payload}"
    )

    raw = _call_provider_raw(payload, user_message, provider, model, system_prompt, _token_sink)
    return _parse_json_translation(raw, len(texts))


def _translate_chunk_json_with_retry(texts: list, provider: str, model: str,
                                     source_lang: str, target_lang: str,
                                     context: str = None, depth: int = 0) -> list:
    """
    Translate a text list via JSON. On failure, splits in half and retries.
    Returns a list of the same length (falls back to original text on total failure).
    """
    chunk_label = f"{len(texts)} texts (depth={depth})"
    try:
        return _translate_chunk_json(texts, provider, model, source_lang, target_lang, context)
    except FatalTranslationError:
        raise
    except Exception as e:
        if is_authentication_error(e):
            raise FatalTranslationError(f"Authentication failed: {e}")

        warn = f"JSON chunk failed ({chunk_label}): {e}"
        if JSONL_MODE:
            emit_jsonl("warning", warn)
        else:
            tqdm.write(f"\033[93m⚠ {warn}\033[0m")

        if depth >= 2 or len(texts) <= 1:
            # Give up — return originals so the rest can continue
            warn2 = f"Giving up on {len(texts)} subtitle(s) after splits — keeping original text."
            if JSONL_MODE:
                emit_jsonl("warning", warn2)
            else:
                tqdm.write(f"\033[93m⚠ {warn2}\033[0m")
            return list(texts)

        mid = len(texts) // 2
        split_msg = f"Splitting JSON chunk at depth {depth + 1} ({len(texts)} → {mid}+{len(texts)-mid})"
        if JSONL_MODE:
            emit_jsonl("info", split_msg)
        else:
            tqdm.write(f"\033[96m{split_msg}\033[0m")

        first = _translate_chunk_json_with_retry(
            texts[:mid], provider, model, source_lang, target_lang, context, depth + 1)
        second = _translate_chunk_json_with_retry(
            texts[mid:], provider, model, source_lang, target_lang, context, depth + 1)
        return first + second


def translate_srt_content_structured(content, context=None, provider="openai", model=None,
                                     max_workers=None, chunk_size=None,
                                     source_lang="English", target_lang="Bulgarian",
                                     price_input=0.0, price_output=0.0):
    """
    Structured translation: parse SRT → send only text as JSON → reconstruct.

    Uses an adaptive work queue: when a chunk fails and must be split to size N,
    all subsequent queued chunks are automatically re-queued at size N instead
    of repeatedly attempting the original (too-large) size.

    Advantages over SRT-format approach:
    - ~50-60% fewer tokens (no timecodes or index numbers sent)
    - LLM cannot corrupt timecodes (they are never sent)
    - Validation is a simple count check, not SRT syntax parsing
    - Adaptive chunk sizing avoids wasting API calls on known-bad sizes
    """
    records = _parse_srt_to_records(content)
    if not records:
        log_output("Could not parse SRT structure; input may not be valid SRT.", "⚠️  ", "warning")
        return content

    if chunk_size is None:
        chunk_size = 20
    if max_workers is None:
        max_workers = 2

    all_texts = [r['text'] for r in records]
    total = len(all_texts)
    translated_texts = [None] * total

    # ── Shared adaptive state ────────────────────────────────────────────────
    _eff_size    = [chunk_size]       # current working chunk size
    _size_lock   = threading.Lock()
    _fatal       = [None]
    _result_lock = threading.Lock()
    _done_subs   = [0]               # subtitles successfully stored
    _fallback_set = set()            # indices where original text was kept
    _stats = {                       # process counters for final summary
        'api_calls':       0,        # successful API calls
        'api_failures':    0,        # failed API calls
        'splits':          0,        # chunks split due to failure
        'pre_splits':      0,        # chunks pre-split (no API call wasted)
        'size_reductions': 0,        # times effective chunk size was lowered
        'input_tokens':    0,        # total prompt tokens consumed
        'output_tokens':   0,        # total completion tokens generated
    }

    def _track_tokens(in_tok: int, out_tok: int) -> None:
        """Accumulate token counts for cost reporting (called from worker threads)."""
        with _result_lock:
            _stats['input_tokens']  += in_tok
            _stats['output_tokens'] += out_tok

    # ── Work queue ───────────────────────────────────────────────────────────
    work_q   = _queue.Queue()
    _pending = [0]
    _plock   = threading.Lock()

    def enqueue(start_idx, texts):
        """Add a work item and increment the in-flight counter."""
        with _plock:
            _pending[0] += 1
        work_q.put((start_idx, texts))

    def item_done():
        """Decrement the in-flight counter; emit sentinel when all work is done."""
        with _plock:
            _pending[0] -= 1
            if _pending[0] == 0:
                work_q.put(None)  # sentinel: no more work

    # Seed the queue with initial chunks
    initial_chunks = 0
    for i in range(0, total, chunk_size):
        enqueue(i, all_texts[i:i + chunk_size])
        initial_chunks += 1

    log_output(
        f"Structured translation: {total} subtitles, ~{initial_chunks} chunks, "
        f"{max_workers} workers, chunk size {chunk_size} (adaptive, text-only JSON mode)",
        "🔄 ", "info",
        data={"total_subtitles": total, "initial_chunks": initial_chunks,
              "provider": provider, "model": model, "chunk_size": chunk_size},
    )

    # ── Worker function ──────────────────────────────────────────────────────
    def worker():
        while True:
            item = work_q.get()

            if item is None:                    # sentinel — propagate and exit
                work_q.put(None)
                break

            if _fatal[0]:                       # abort without processing
                item_done()
                continue

            start_idx, texts = item

            # Pre-split if the effective size has been reduced since this
            # item was enqueued (avoids wasting a call on a known-bad size).
            with _size_lock:
                cur_size = _eff_size[0]

            if len(texts) > cur_size:
                for j in range(0, len(texts), cur_size):
                    enqueue(start_idx + j, texts[j:j + cur_size])
                with _result_lock:
                    _stats['pre_splits'] += 1
                item_done()
                continue

            # ── Attempt translation ──────────────────────────────────────
            try:
                result = _translate_chunk_json(
                    texts, provider, model, source_lang, target_lang, context,
                    _token_sink=_track_tokens)

                with _result_lock:
                    for k, text in enumerate(result):
                        if start_idx + k < total:
                            translated_texts[start_idx + k] = text
                    _done_subs[0] += len(result)
                    _stats['api_calls'] += 1
                    progress = int((_done_subs[0] / total) * 100)

                if JSONL_MODE:
                    emit_jsonl("progress",
                               f"Translated {_done_subs[0]}/{total} subtitles", progress)
                item_done()

            except FatalTranslationError as e:
                _fatal[0] = e
                item_done()

            except Exception as e:
                if is_authentication_error(e):
                    _fatal[0] = FatalTranslationError(f"Authentication failed: {e}")
                    item_done()
                    return

                # Reduce effective chunk size and re-queue as two halves
                with _result_lock:
                    _stats['api_failures'] += 1

                if len(texts) > 1:
                    new_size = max(1, len(texts) // 2)
                    with _size_lock:
                        if new_size < _eff_size[0]:
                            _eff_size[0] = new_size
                            with _result_lock:
                                _stats['size_reductions'] += 1
                            msg = (f"Chunk size reduced to {new_size} "
                                   f"(all remaining chunks will use this size)")
                            log_output(msg, "📉 ", "info")

                    mid = len(texts) // 2
                    enqueue(start_idx,       texts[:mid])
                    enqueue(start_idx + mid, texts[mid:])
                    with _result_lock:
                        _stats['splits'] += 1
                    item_done()   # original item replaced by two halves
                else:
                    # Single subtitle — keep original text, mark as fallback
                    log_output(
                        f"Subtitle #{records[start_idx]['index']} could not be translated; "
                        f"keeping original text.", "⚠️  ", "warning")
                    with _result_lock:
                        translated_texts[start_idx] = texts[0]
                        _fallback_set.add(start_idx)
                        _done_subs[0] += 1
                    item_done()

    # ── Run workers ──────────────────────────────────────────────────────────
    threads = [threading.Thread(target=worker, daemon=True) for _ in range(max_workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if _fatal[0]:
        if JSONL_MODE:
            emit_jsonl("result", "Translation failed", 0,
                       {"success": False, "error": str(_fatal[0])})
        sys.exit(1)

    # Fill any None slots before the repair pass
    for i in range(total):
        if translated_texts[i] is None:
            translated_texts[i] = all_texts[i]
            _fallback_set.add(i)

    # ── Completeness check & repair pass ─────────────────────────────────────
    # Find indices where translation was not completed (explicit fallbacks).
    # Group them into time ranges and re-translate each range once.
    missing_indices = sorted(_fallback_set)

    if missing_indices:
        groups = _group_consecutive(missing_indices)

        # Build human-readable time range summary
        range_strs = []
        for gs, ge in groups:
            t0 = _ms_to_hhmm(_timecode_start_ms(records[gs]['timecode']))
            t1 = _ms_to_hhmm(_timecode_start_ms(records[ge]['timecode']))
            label = (f"{t0}–{t1}" if t0 != t1 else t0)
            range_strs.append(
                f"{label} (#{records[gs]['index']}–#{records[ge]['index']})")

        log_output(
            f"Completeness check: {len(missing_indices)} subtitle(s) not translated "
            f"across {len(groups)} time range(s): {', '.join(range_strs)}",
            "🔍 ", "warning",
            data={"missing_count": len(missing_indices),
                  "missing_ranges": range_strs})

        recovered = 0
        for gs, ge in groups:
            # Include up to 2 subtitles of context on each side for quality
            ctx_start = max(0, gs - 2)
            ctx_end   = min(total - 1, ge + 2)
            group_texts = all_texts[ctx_start:ctx_end + 1]
            offset = gs - ctx_start          # position of missing range within group_texts
            count  = ge - gs + 1

            t0 = _ms_to_hhmm(_timecode_start_ms(records[gs]['timecode']))
            t1 = _ms_to_hhmm(_timecode_start_ms(records[ge]['timecode']))
            label = f"{t0}–{t1}" if t0 != t1 else t0

            try:
                result = _translate_chunk_json(
                    group_texts, provider, model, source_lang, target_lang, context,
                    _token_sink=_track_tokens)
                for k in range(count):
                    translated_texts[gs + k] = result[offset + k]
                recovered += count
                log_output(
                    f"Recovered {count} subtitle(s) at {label}",
                    "✅ ", "info")
            except Exception as exc:
                log_output(
                    f"Repair failed for range {label}: {exc} — original text kept.",
                    "⚠️  ", "warning")

        if recovered > 0:
            log_output(
                f"Repair complete: {recovered}/{len(missing_indices)} subtitle(s) recovered.",
                "✅ ", "info")
        if recovered < len(missing_indices):
            log_output(
                f"{len(missing_indices) - recovered} subtitle(s) could not be recovered "
                f"and retain original text.",
                "⚠️  ", "warning")
    else:
        log_output(
            f"Completeness check passed — all {total} subtitles translated.",
            "✅ ", "info")

    # ── Final summary ─────────────────────────────────────────────────────────
    recovered      = sum(1 for i in _fallback_set if translated_texts[i] != all_texts[i])
    still_original = len(_fallback_set) - recovered
    size_note      = (f"{chunk_size} → {_eff_size[0]} "
                      f"(reduced {_stats['size_reductions']}×)"
                      if _eff_size[0] < chunk_size else str(chunk_size))

    in_tok  = _stats['input_tokens']
    out_tok = _stats['output_tokens']
    token_line = (f"  Tokens      : {in_tok:,} in + {out_tok:,} out"
                  if in_tok or out_tok else None)
    cost_line = None
    if (price_input > 0 or price_output > 0) and (in_tok or out_tok):
        cost = in_tok / 1_000_000 * price_input + out_tok / 1_000_000 * price_output
        cost_line = f"  Cost        : ${cost:.4f} USD"

    lines = [
        "─" * 48,
        "Translation Summary",
        "─" * 48,
        f"  Subtitles   : {total} total",
        f"  Chunk size  : {size_note}",
        f"  Workers     : {max_workers}",
        f"  API calls   : {_stats['api_calls']} ok"
        + (f" + {_stats['api_failures']} failed" if _stats['api_failures'] else ""),
        f"  Splits      : {_stats['splits']}"
        + (f"  ({_stats['pre_splits']} pre-split without extra API call)"
           if _stats['pre_splits'] else ""),
    ]
    if token_line:
        lines.append(token_line)
    if cost_line:
        lines.append(cost_line)

    if _fallback_set:
        comp_line = (
            f"  Completeness: {total - still_original}/{total} translated"
            + (f" ({recovered} recovered by repair pass)" if recovered else "")
            + (f" — {still_original} kept original ⚠" if still_original else " ✓")
        )
    else:
        comp_line = f"  Completeness: {total}/{total} ✓"
    lines.append(comp_line)

    if _stats['api_failures'] or still_original:
        lines.append("─" * 48)
        lines.append("  ⚠ Issues detected — check log above for details.")
    lines.append("─" * 48)

    summary_text = "\n".join(lines)
    _cost = ((in_tok / 1_000_000 * price_input + out_tok / 1_000_000 * price_output)
             if (price_input > 0 or price_output > 0) else None)
    log_output(summary_text, "", "info",
               data={
                   "total_subtitles":  total,
                   "chunk_size_start": chunk_size,
                   "chunk_size_final": _eff_size[0],
                   "size_reductions":  _stats['size_reductions'],
                   "api_calls_ok":     _stats['api_calls'],
                   "api_calls_failed": _stats['api_failures'],
                   "splits":           _stats['splits'],
                   "pre_splits":       _stats['pre_splits'],
                   "fallback_count":   len(_fallback_set),
                   "recovered":        recovered,
                   "still_original":   still_original,
                   "input_tokens":     in_tok,
                   "output_tokens":    out_tok,
                   "cost_usd":         _cost,
               })

    return _reconstruct_srt(records, translated_texts)


def process_chunk(data):
    """Process a single chunk of subtitles"""
    chunk, index, provider, model, system_prompt = data
    try:
        translated_text, success = retry_translation_with_split(chunk, provider, model, system_prompt)
        return index, translated_text
    except FatalTranslationError:
        # Re-raise fatal errors to stop all processing
        raise
    except Exception as e:
        error_msg = f"ERROR: Failed to translate chunk {index + 1}: {str(e)}"
        if not JSONL_MODE:
            tqdm.write(f"\n\033[91m{error_msg}\033[0m")
        else:
            emit_jsonl("error", error_msg)
        return index, error_msg

def translate_srt_content(content, context=None, provider="openai", model=None, max_workers=None, chunk_size=None, source_lang="English", target_lang="Bulgarian"):
    system_prompt = get_system_prompt(provider, source_lang, target_lang, context)

    # Set default chunk size based on provider if not specified.
    # 50 is safe for all providers — large chunks (200+) hit max_tokens limits
    # on models that aren't Claude.  Users can override via --chunk-size.
    if chunk_size is None:
        chunk_size = 50

    # Split content into chunks
    chunks = split_into_chunks(content, chunk_size)
    total_chunks = len(chunks)
    translated_chunks = [None] * total_chunks  # Pre-allocate list for results

    # Prepare chunk data
    chunk_data = [(chunk, i, provider, model, system_prompt) for i, chunk in enumerate(chunks)]
    
    # Set number of workers based on provider and user input
    if max_workers is None:
        max_workers = 2 if provider == "claude" else 10
    
    # Emit initial progress info
    if JSONL_MODE:
        emit_jsonl("info", f"Starting translation with {model} ({max_workers} workers, chunk size {chunk_size})", 0, {
            "provider": provider,
            "model": model,
            "max_workers": max_workers,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks
        })
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chunk = {executor.submit(process_chunk, data): data[1] for data in chunk_data}
        fatal_error = None

        if JSONL_MODE:
            # JSONL mode - no tqdm progress bar
            completed_chunks = 0
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_index = future_to_chunk[future]
                try:
                    index, translated_text = future.result()
                    if translated_text.startswith("ERROR:"):
                        emit_jsonl("error", f"Chunk {index + 1} failed: {translated_text}")
                    else:
                        translated_chunks[index] = translated_text
                        emit_jsonl("info", f"Completed chunk {index + 1}/{total_chunks}")
                    completed_chunks += 1
                    progress = int((completed_chunks / total_chunks) * 100)
                    emit_jsonl("progress", f"Translation progress: {completed_chunks}/{total_chunks} chunks", progress)
                except FatalTranslationError as e:
                    # Authentication or other fatal error - cancel all pending futures and stop
                    fatal_error = e
                    emit_jsonl("error", f"Fatal error: {str(e)}")
                    for f in future_to_chunk:
                        f.cancel()
                    break
                except Exception as e:
                    emit_jsonl("error", f"Chunk {chunk_index + 1} generated an exception: {str(e)}")
        else:
            # Normal mode with tqdm progress bar
            with tqdm(total=total_chunks,
                     desc=f"\033[1;36mTranslating with {model} ({max_workers} workers, chunk size {chunk_size})\033[0m",
                     unit="chunk",
                     bar_format="{desc}: {percentage:3.0f}%|{bar:30}\033[92m|\033[0m{n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                     colour='green') as pbar:

                for future in concurrent.futures.as_completed(future_to_chunk):
                    chunk_index = future_to_chunk[future]
                    try:
                        index, translated_text = future.result()
                        if translated_text.startswith("ERROR:"):
                            tqdm.write(f"\033[91mChunk {index + 1} failed: {translated_text}\033[0m")
                        else:
                            translated_chunks[index] = translated_text
                        pbar.update(1)
                    except FatalTranslationError as e:
                        # Authentication or other fatal error - cancel all pending futures and stop
                        fatal_error = e
                        tqdm.write(f"\033[91m\n❌ Fatal error: {str(e)}\033[0m")
                        for f in future_to_chunk:
                            f.cancel()
                        break
                    except Exception as e:
                        tqdm.write(f"\033[91mChunk {chunk_index + 1} generated an exception: {str(e)}\033[0m")

        # If there was a fatal error, exit with error code
        if fatal_error:
            error_msg = str(fatal_error)
            if JSONL_MODE:
                emit_jsonl("result", "Translation failed", 0, {
                    "success": False,
                    "error": error_msg,
                    "error_type": "authentication_error" if "authentication" in error_msg.lower() else "fatal_error"
                })
            sys.exit(1)

    # Check for any failed chunks
    if any(chunk is None for chunk in translated_chunks):
        error_msg = "Some chunks failed to translate. Check the errors above."
        if not JSONL_MODE:
            print(f"\n⚠️ {error_msg}")
        else:
            emit_jsonl("error", error_msg)
        sys.exit(1)

    # Join all chunks ensuring no content is lost
    # Filter out None values and ensure proper spacing between chunks
    valid_chunks = [chunk for chunk in translated_chunks if chunk is not None]
    
    if not valid_chunks:
        return ""
    
    # Join chunks with proper spacing
    result = []
    for i, chunk in enumerate(valid_chunks):
        chunk_clean = chunk.strip()
        if chunk_clean:
            result.append(chunk_clean)
    
    # Join with double newlines to ensure separation, then normalize
    combined = '\n\n'.join(result)
    
    # Final formatting pass
    return ensure_subtitle_spacing(combined)

def read_file_with_encoding(file_path):
    """
    Try to read file with different encodings.
    Returns the content in successful encoding.
    """
    encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    
    raise UnicodeDecodeError(f"Failed to read file with any of these encodings: {', '.join(encodings)}")

def process_srt_file(input_file, output_file, context=None, provider="openai", model=None, max_workers=None, chunk_size=None, source_lang="English", target_lang="Bulgarian", price_input=0.0, price_output=0.0):
    log_output(f"Reading file: {input_file}", "\n📂 ", "info")
    
    try:
        content = read_file_with_encoding(input_file)
    except UnicodeDecodeError as e:
        error_msg = f"Error reading file: {e}"
        log_output(error_msg, "\n❌ ", "error")
        sys.exit(1)

    # Count the number of subtitle entries for progress info
    subtitle_count = len([line for line in content.split('\n') if line.strip().isdigit()])
    log_output(f"Found {subtitle_count} subtitles to translate", "📊 ", "info", data={"subtitle_count": subtitle_count})
    
    context_msg = f" (with provided context)" if context else ""
    log_output(f"Starting translation using {provider} {model}{context_msg}...", "🔄 ", "info", data={
        "provider": provider,
        "model": model,
        "has_context": bool(context),
        "source_lang": source_lang,
        "target_lang": target_lang
    })
    
    start_time = time.time()
    translated_content = translate_srt_content_structured(
        content, context, provider, model, max_workers, chunk_size, source_lang, target_lang,
        price_input=price_input, price_output=price_output)
    end_time = time.time()
    
    duration = end_time - start_time
    log_output(f"Translation completed in {duration:.1f} seconds", "✨ ", "info", data={"duration": duration})
    
    log_output(f"Writing translation to: {output_file}", "💾 ", "info")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(translated_content)
    log_output("File saved successfully", "✅ ", "info")

    # --- Subtitle output validation (with auto-repair) ---
    log_output("Validating output file…", "🔍 ", "info")

    # First pass: validate to detect issues
    vr = validate_srt_file(output_file)
    _timing_errors = vr["stats"].get("timing_errors", 0) if vr["stats"] else 0
    _ordering_errors = vr["stats"].get("ordering_errors", 0) if vr["stats"] else 0

    # Auto-repair timing issues (start >= end) and re-validate
    if not vr["valid"] and (_timing_errors > 0 or _ordering_errors > 0):
        repair_result = repair_srt_timing(output_file)
        if repair_result["error"] is None and repair_result["fixed"] > 0:
            log_output(
                f"Auto-repaired {repair_result['fixed']} subtitle(s) with invalid timecodes",
                "🔧 ", "warning"
            )
            # Re-validate after repair
            vr = validate_srt_file(output_file)
        elif repair_result["error"]:
            log_output(f"Timing repair failed: {repair_result['error']}", "⚠️  ", "warning")

    _vparser = vr["stats"].get("parser", "built-in") if vr["stats"] else "built-in"

    if vr["valid"] and not vr["warnings"]:
        log_output(
            f"Validation passed ✓  {vr['subtitle_count']} subtitles  "
            f"{vr['stats'].get('duration_seconds', 0):.1f}s  "
            f"{vr['stats'].get('file_size_kb', 0):.1f} KB  "
            f"[{_vparser}]",
            "✅ ", "info",
            data={"validation": vr}
        )
    elif vr["valid"]:
        log_output(
            f"Validation passed with warnings  {vr['subtitle_count']} subtitles  "
            f"[{_vparser}]",
            "⚠️  ", "warning",
            data={"validation": vr}
        )
        for warn in vr["warnings"]:
            log_output(f"  ⚠  {warn}", "", "warning")
    else:
        # Validation found errors — report as WARNING so the pipeline continues.
        # The file was successfully translated and saved; these are quality issues,
        # not translation failures. The user can see them in the log.
        log_output(
            f"Validation found {len(vr['errors'])} issue(s)  "
            f"{vr['subtitle_count']} subtitles parsed  [{_vparser}]",
            "⚠️  ", "warning",
            data={"validation": vr}
        )
        for err in vr["errors"]:
            log_output(f"  ✗  {err}", "", "warning")
        for warn in vr["warnings"]:
            log_output(f"  ⚠  {warn}", "", "warning")

    # Emit final result in JSONL mode
    if JSONL_MODE:
        try:
            emit_jsonl("result", "Translation completed successfully", 100, {
                "input_file": input_file,
                "output_file": output_file,
                "duration": duration,
                "outputs": [output_file],
                "validation": vr,
            })
            # Force flush all output before exit
            sys.stdout.flush()
            sys.stderr.flush()
        except BrokenPipeError:
            # Parent process closed pipe - exit gracefully
            sys.exit(0)

def process_directory(directory, context=None, provider="openai", model=None, max_workers=None, chunk_size=None, source_lang="English", target_lang="Bulgarian", price_input=0.0, price_output=0.0):
    # Get list of SRT files first
    srt_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.srt'):
                srt_files.append(os.path.join(root, file))
    
    if not srt_files:
        log_output("No SRT files found in directory", "❌ ", "error")
        return
        
    log_output(f"Found {len(srt_files)} SRT files to process", "📁 ", "info", data={"file_count": len(srt_files)})
    
    outputs = []
    failed_files = []
    
    if JSONL_MODE:
        # JSONL mode - no tqdm progress bar
        for i, file in enumerate(srt_files):
            input_path = file
            output_path = get_output_filename(input_path)
            try:
                process_srt_file(input_path, output_path, context, provider, model, max_workers, chunk_size, source_lang, target_lang, price_input=price_input, price_output=price_output)
                outputs.append(output_path)
                progress = int(((i + 1) / len(srt_files)) * 100)
                emit_jsonl("progress", f"Processing files: {i + 1}/{len(srt_files)}", progress)
            except Exception as e:
                failed_files.append({"file": input_path, "error": str(e)})
                emit_jsonl("error", f"Failed to process {input_path}: {str(e)}")
        
        # Emit final result
        try:
            emit_jsonl("result", "Directory processing completed", 100, {
                "directory": directory,
                "total_files": len(srt_files),
                "successful_files": len(outputs),
                "failed_files": len(failed_files),
                "outputs": outputs,
                "failures": failed_files
            })
            # Force flush all output before exit
            sys.stdout.flush()
            sys.stderr.flush()
        except BrokenPipeError:
            # Parent process closed pipe - exit gracefully
            sys.exit(0)
    else:
        # Normal mode with tqdm progress bar
        with tqdm(total=len(srt_files), 
                 desc="\033[1;36mProcessing files\033[0m",
                 bar_format="{desc}: {percentage:3.0f}%|{bar:30}\033[92m|\033[0m{n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                 colour='green') as pbar:
            for file in srt_files:
                input_path = file
                output_path = get_output_filename(input_path)
                try:
                    process_srt_file(input_path, output_path, context, provider, model, max_workers, chunk_size, source_lang, target_lang, price_input=price_input, price_output=price_output)
                    outputs.append(output_path)
                except Exception as e:
                    failed_files.append({"file": input_path, "error": str(e)})
                    print(f"❌ Failed to process {input_path}: {str(e)}")
                pbar.update(1)

def get_output_filename(input_file, output_file=None):
    if output_file:
        return output_file
    base_name = os.path.splitext(input_file)[0]
    return f"{base_name}.bg.srt"

def handle_sigpipe(signum, frame):
    """Handle SIGPIPE signal gracefully."""
    sys.exit(0)

if __name__ == "__main__":
    # Handle SIGPIPE gracefully to prevent crashes when parent process closes pipe
    signal.signal(signal.SIGPIPE, handle_sigpipe)
    
    # Early debug output
    try:
        print(f"DEBUG: Script starting with args: {sys.argv}", file=sys.stderr, flush=True)
    except BrokenPipeError:
        sys.exit(0)
    
    parser = argparse.ArgumentParser(description="Translate SRT files between languages")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="Path to the input SRT file")
    group.add_argument("-d", "--directory", help="Path to directory containing SRT files")
    parser.add_argument("-o", "--output", help="Output file path (optional)")
    parser.add_argument("-c", "--context", help="Context about the film/show to improve translation")
    parser.add_argument("-p", "--provider", choices=["openai", "claude", "openrouter", "local", "xai", "mistral", "groq", "deepseek", "moonshot", "gemini", "zai"], default="openai", help="Translation provider")
    parser.add_argument("-m", "--model", help="Model to use (provider-specific)")
    parser.add_argument("-w", "--workers", type=int, help="Number of concurrent workers")
    parser.add_argument("-s", "--chunk-size", type=int, help="Number of subtitles per chunk")
    parser.add_argument("--source-lang", default="English", help="Source language (default: English)")
    parser.add_argument("--target-lang", default="Bulgarian", help="Target language (default: Bulgarian)")
    parser.add_argument("--price-input", type=float, default=0.0, help="Price per 1M input tokens in USD (for cost tracking)")
    parser.add_argument("--price-output", type=float, default=0.0, help="Price per 1M output tokens in USD (for cost tracking)")
    parser.add_argument("--jsonl", action="store_true", help="Enable JSONL output mode (suppresses colored output)")
    args = parser.parse_args()
    
    # Early debug output about parsed args
    print(f"DEBUG: Parsed args - provider: {args.provider}, model: {args.model}, file: {getattr(args, 'file', None)}", file=sys.stderr, flush=True)
    
    # Set global JSONL mode
    JSONL_MODE = args.jsonl

    # Set default model based on provider; accept any non-empty model string (live-fetched models)
    print(f"DEBUG: Starting model validation for provider: {args.provider}, model: {args.model}", file=sys.stderr, flush=True)
    _provider_defaults = {
        "openai":     "gpt-4o-mini",
        "claude":     "claude-haiku-4-5-20251001",
        "openrouter": "anthropic/claude-haiku-4-5-20251001",
        "xai":        "grok-beta",
        "mistral":    "mistral-small-latest",
        "groq":       "llama-3.3-70b-versatile",
        "deepseek":   "deepseek-chat",
        "moonshot":   "moonshot-v1-8k",
        "gemini":     "gemini-1.5-flash",
        "zai":        "glm-4.7",
    }
    if args.provider == "local":
        args.model = "local"  # LM Studio always uses the currently loaded model
    else:
        if not args.model or not args.model.strip():
            args.model = _provider_defaults.get(args.provider, "")
            if not args.model:
                error_msg = f"Error: No model specified for provider '{args.provider}'"
                log_output(error_msg, "", "error")
                sys.exit(1)

    if args.directory:
        log_output(f"Starting translation of all SRT files in {args.directory}", "", "info")
        process_directory(args.directory, args.context, args.provider, args.model, args.workers, args.chunk_size, args.source_lang, args.target_lang, price_input=args.price_input, price_output=args.price_output)
        log_output("All translations complete", "", "info")
    else:
        output_file = get_output_filename(args.file, args.output)
        process_srt_file(args.file, output_file, args.context, args.provider, args.model, args.workers, args.chunk_size, args.source_lang, args.target_lang, price_input=args.price_input, price_output=args.price_output)
        log_output("Translation complete", "", "info")

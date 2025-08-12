#!/usr/bin/env python3

import os
import re
import argparse
import signal
from openai import OpenAI
from anthropic import Anthropic
from dotenv import load_dotenv
import concurrent.futures
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

# Available models
OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo"]
CLAUDE_MODELS = ["claude-3-opus-20240229", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-haiku-20240307"]
LMSTUDIO_MODELS = ["local"]

# Maximum retries for invalid chunks
MAX_RETRIES = 3

# Global JSONL mode flag
JSONL_MODE = False

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
    if provider == "openai":
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
    for attempt in range(max_retries):
        try:
            if provider == "openai":
                translated = translate_with_openai(chunk, model, system_prompt)
            elif provider == "claude":
                translated = translate_with_claude(chunk, model, system_prompt)
            else:  # lmstudio
                translated = translate_with_lmstudio(chunk, model, system_prompt)
            
            # Ensure proper SRT format
            translated = ensure_srt_format(translated)
            
            # Validate and normalize the translation
            is_valid, result = validate_srt_chunk(translated)
            if is_valid:
                return result, True  # Return normalized text
            
            # If invalid, show the AI response and error
            debug_lines = translated.split('\n')[:6]
            debug_text = '\n'.join(debug_lines)
            if len(debug_lines) < len(translated.split('\n')):
                debug_text += "\n..."
            if not JSONL_MODE:
                tqdm.write(f"\n\033[95mAI Response Sample:\n{debug_text}\033[0m")
            else:
                emit_jsonl("warning", f"AI Response Sample: {debug_text}")
            if isinstance(result, str):  # If result is an error message
                warning_msg = f"Attempt {attempt + 1}/{max_retries}: Invalid SRT format in chunk: {result}"
                if not JSONL_MODE:
                    tqdm.write(f"\033[93m⚠️ {warning_msg}\033[0m")
                else:
                    emit_jsonl("warning", warning_msg)
            
        except Exception as e:
            error_msg = f"Attempt {attempt + 1}/{max_retries} failed with error: {str(e)}"
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

def retry_translation_with_split(chunk, provider, model, system_prompt, split_depth=0, max_splits=2):
    """
    Attempts to translate a chunk, if fails, splits it and tries each half.
    Returns (translated_text, success)
    """
    try:
        if provider == "openai":
            translated = translate_with_openai(chunk, model, system_prompt)
        elif provider == "claude":
            translated = translate_with_claude(chunk, model, system_prompt)
        else:  # lmstudio
            translated = translate_with_lmstudio(chunk, model, system_prompt)
        
        # Ensure proper SRT format and spacing
        translated = ensure_srt_format(translated)
        translated = ensure_subtitle_spacing(translated)
        
        # Validate the translation
        is_valid, result = validate_srt_chunk(translated)
        if is_valid:
            return result, True
            
        # If invalid, show the error and proceed to splitting
        debug_lines = translated.split('\n')[:6]
        debug_text = '\n'.join(debug_lines)
        if len(debug_lines) < len(translated.split('\n')):
            debug_text += "\n..."
        if not JSONL_MODE:
            tqdm.write(f"\n\033[95mAI Response Sample:\n{debug_text}\033[0m")
            tqdm.write(f"\033[93m⚠️ Invalid SRT format in chunk: {result}\033[0m")
        else:
            emit_jsonl("warning", f"AI Response Sample: {debug_text}")
            emit_jsonl("warning", f"Invalid SRT format in chunk: {result}")
        
    except Exception as e:
        error_msg = f"Translation failed with error: {str(e)}"
        if not JSONL_MODE:
            tqdm.write(f"\033[91m❌ {error_msg}\033[0m")
        else:
            emit_jsonl("error", error_msg)
    
    # If we've reached max splits, return the original chunk with a warning
    if split_depth >= max_splits:
        warning_msg = "Max split depth reached. Some subtitles may be invalid."
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
    
    split_msg = f"Splitting chunk at depth {split_depth + 1} and retrying translation"
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
        ]
    )
    translated_text = response.choices[0].message.content.strip()
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
            max_tokens=4000,
        )
        translated_text = response.choices[0].message.content.strip()
        return clean_openai_response(translated_text)  # Use same cleaning as OpenAI
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

def process_chunk(data):
    """Process a single chunk of subtitles"""
    chunk, index, provider, model, system_prompt = data
    try:
        translated_text, success = retry_translation_with_split(chunk, provider, model, system_prompt)
        return index, translated_text
    except Exception as e:
        error_msg = f"ERROR: Failed to translate chunk {index + 1}: {str(e)}"
        if not JSONL_MODE:
            tqdm.write(f"\n\033[91m{error_msg}\033[0m")
        else:
            emit_jsonl("error", error_msg)
        return index, error_msg

def translate_srt_content(content, context=None, provider="openai", model=None, max_workers=None, chunk_size=None, source_lang="English", target_lang="Bulgarian"):
    system_prompt = get_system_prompt(provider, source_lang, target_lang, context)

    # Set default chunk size based on provider if not specified
    if chunk_size is None:
        chunk_size = 50 if provider == "claude" else 200

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
                    except Exception as e:
                        tqdm.write(f"\033[91mChunk {chunk_index + 1} generated an exception: {str(e)}\033[0m")

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

def process_srt_file(input_file, output_file, context=None, provider="openai", model=None, max_workers=None, chunk_size=None, source_lang="English", target_lang="Bulgarian"):
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
    translated_content = translate_srt_content(content, context, provider, model, max_workers, chunk_size, source_lang, target_lang)
    end_time = time.time()
    
    duration = end_time - start_time
    log_output(f"Translation completed in {duration:.1f} seconds", "✨ ", "info", data={"duration": duration})
    
    log_output(f"Writing translation to: {output_file}", "💾 ", "info")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(translated_content)
    log_output("File saved successfully", "✅ ", "info")
    
    # Emit final result in JSONL mode
    if JSONL_MODE:
        try:
            emit_jsonl("result", "Translation completed successfully", 100, {
                "input_file": input_file,
                "output_file": output_file,
                "duration": duration,
                "outputs": [output_file]
            })
            # Force flush all output before exit
            sys.stdout.flush()
            sys.stderr.flush()
        except BrokenPipeError:
            # Parent process closed pipe - exit gracefully
            sys.exit(0)

def process_directory(directory, context=None, provider="openai", model=None, max_workers=None, chunk_size=None, source_lang="English", target_lang="Bulgarian"):
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
                process_srt_file(input_path, output_path, context, provider, model, max_workers, chunk_size, source_lang, target_lang)
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
                    process_srt_file(input_path, output_path, context, provider, model, max_workers, chunk_size, source_lang, target_lang)
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
    parser.add_argument("-p", "--provider", choices=["openai", "claude", "local"], default="openai", help="Translation provider")
    parser.add_argument("-m", "--model", help="Model to use (provider-specific)")
    parser.add_argument("-w", "--workers", type=int, help="Number of concurrent workers")
    parser.add_argument("-s", "--chunk-size", type=int, help="Number of subtitles per chunk")
    parser.add_argument("--source-lang", default="English", help="Source language (default: English)")
    parser.add_argument("--target-lang", default="Bulgarian", help="Target language (default: Bulgarian)")
    parser.add_argument("--jsonl", action="store_true", help="Enable JSONL output mode (suppresses colored output)")
    args = parser.parse_args()
    
    # Early debug output about parsed args
    print(f"DEBUG: Parsed args - provider: {args.provider}, model: {args.model}, file: {getattr(args, 'file', None)}", file=sys.stderr, flush=True)
    
    # Set global JSONL mode
    JSONL_MODE = args.jsonl

    # Validate and set default model based on provider
    print(f"DEBUG: Starting model validation for provider: {args.provider}, model: {args.model}", file=sys.stderr, flush=True)
    if args.provider == "openai":
        if not args.model:
            args.model = "gpt-4o-mini"
        elif args.model not in OPENAI_MODELS:
            error_msg = f"Error: Invalid OpenAI model. Available models: {', '.join(OPENAI_MODELS)}"
            log_output(error_msg, "", "error")
            sys.exit(1)
    elif args.provider == "claude":
        if not args.model:
            args.model = "claude-3-5-sonnet-20241022"
        elif args.model not in CLAUDE_MODELS:
            error_msg = f"Error: Invalid Claude model. Available models: {', '.join(CLAUDE_MODELS)}"
            log_output(error_msg, "", "error")
            sys.exit(1)
    else:  # lmstudio
        args.model = "local"  # LM Studio always uses the currently loaded model

    if args.directory:
        log_output(f"Starting translation of all SRT files in {args.directory}", "", "info")
        process_directory(args.directory, args.context, args.provider, args.model, args.workers, args.chunk_size, args.source_lang, args.target_lang)
        log_output("All translations complete", "", "info")
    else:
        output_file = get_output_filename(args.file, args.output)
        process_srt_file(args.file, output_file, args.context, args.provider, args.model, args.workers, args.chunk_size, args.source_lang, args.target_lang)
        log_output("Translation complete", "", "info")

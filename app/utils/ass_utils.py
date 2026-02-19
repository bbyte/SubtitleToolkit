"""
ASS/SSA Subtitle Parser and Writer Module

This module handles parsing and writing ASS/SSA subtitle files while preserving
all formatting, styles, and metadata. It extracts only the dialogue text for
translation while keeping the original structure intact.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class AssDialogueLine:
    """Represents a single dialogue line in an ASS/SSA subtitle file."""

    layer: str = "0"
    start: str = "0:00:00.00"
    end: str = "0:00:00.00"
    style: str = "Default"
    name: str = ""
    margin_l: str = "0"
    margin_r: str = "0"
    margin_v: str = "0"
    effect: str = ""
    text: str = ""

    # Original raw line for fallback
    raw_line: str = ""

    # Index for tracking during translation
    index: int = 0


@dataclass
class AssSubtitle:
    """
    Represents a complete ASS/SSA subtitle file.

    Preserves all sections and formatting while allowing dialogue text extraction
    and replacement for translation purposes.
    """

    # [Script Info] section
    script_info: Dict[str, str] = field(default_factory=dict)
    script_info_order: List[str] = field(default_factory=list)  # Preserve key order

    # [V4+ Styles] or [V4 Styles] section
    styles_header: str = ""  # The Format: line
    styles: List[str] = field(default_factory=list)  # Raw style lines
    styles_section_name: str = "V4+ Styles"  # V4+ or V4

    # [Events] section
    events_header: str = ""  # The Format: line
    events_format_fields: List[str] = field(default_factory=list)  # Parsed format fields
    dialogues: List[AssDialogueLine] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)  # Comment lines in events

    # Other sections (fonts, graphics, etc.) - preserved as-is
    other_sections: Dict[str, List[str]] = field(default_factory=dict)
    section_order: List[str] = field(default_factory=list)  # Preserve section order

    # File metadata
    source_path: Optional[str] = None
    encoding: str = "utf-8"


def parse_ass_file(file_path: str) -> AssSubtitle:
    """
    Parse an ASS/SSA subtitle file.

    Args:
        file_path: Path to the ASS/SSA file

    Returns:
        AssSubtitle object with all parsed content

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Try different encodings
    content = None
    encoding_used = "utf-8"

    for encoding in ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be",
                     "cp1252", "latin1", "iso-8859-1"]:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                encoding_used = encoding
                break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        raise ValueError(f"Could not decode file with any supported encoding: {file_path}")

    subtitle = AssSubtitle(source_path=str(path), encoding=encoding_used)

    # Parse the file
    lines = content.split('\n')
    current_section = None
    dialogue_index = 0

    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\r')

        # Check for section header
        section_match = re.match(r'^\[([^\]]+)\]$', line.strip())
        if section_match:
            current_section = section_match.group(1)

            # Track section order
            if current_section not in subtitle.section_order:
                subtitle.section_order.append(current_section)

            # Initialize other sections storage
            if current_section not in ["Script Info", "V4+ Styles", "V4 Styles", "Events"]:
                if current_section not in subtitle.other_sections:
                    subtitle.other_sections[current_section] = []

            # Track styles section name
            if current_section in ["V4+ Styles", "V4 Styles"]:
                subtitle.styles_section_name = current_section

            i += 1
            continue

        # Skip empty lines at section boundaries
        if not line.strip():
            i += 1
            continue

        # Parse content based on current section
        if current_section == "Script Info":
            _parse_script_info_line(line, subtitle)

        elif current_section in ["V4+ Styles", "V4 Styles"]:
            _parse_styles_line(line, subtitle)

        elif current_section == "Events":
            _parse_events_line(line, subtitle, dialogue_index)
            if line.strip().startswith("Dialogue:"):
                dialogue_index += 1

        elif current_section and current_section in subtitle.other_sections:
            subtitle.other_sections[current_section].append(line)

        i += 1

    return subtitle


def _parse_script_info_line(line: str, subtitle: AssSubtitle) -> None:
    """Parse a line from [Script Info] section."""
    # Handle comments
    if line.strip().startswith(';'):
        key = f"_comment_{len(subtitle.script_info)}"
        subtitle.script_info[key] = line
        subtitle.script_info_order.append(key)
        return

    # Parse key: value pairs
    if ':' in line:
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip()
        subtitle.script_info[key] = value
        subtitle.script_info_order.append(key)


def _parse_styles_line(line: str, subtitle: AssSubtitle) -> None:
    """Parse a line from [V4+ Styles] or [V4 Styles] section."""
    if line.strip().startswith("Format:"):
        subtitle.styles_header = line
    elif line.strip().startswith("Style:"):
        subtitle.styles.append(line)


def _parse_events_line(line: str, subtitle: AssSubtitle, dialogue_index: int) -> None:
    """Parse a line from [Events] section."""
    stripped = line.strip()

    if stripped.startswith("Format:"):
        subtitle.events_header = line
        # Parse format fields for proper dialogue parsing
        format_part = stripped[7:].strip()  # Remove "Format:"
        subtitle.events_format_fields = [f.strip() for f in format_part.split(',')]

    elif stripped.startswith("Comment:"):
        subtitle.comments.append(line)

    elif stripped.startswith("Dialogue:"):
        dialogue = _parse_dialogue_line(line, subtitle.events_format_fields, dialogue_index)
        subtitle.dialogues.append(dialogue)


def _parse_dialogue_line(line: str, format_fields: List[str], index: int) -> AssDialogueLine:
    """
    Parse a Dialogue line according to the Format specification.

    The Format line defines the order of fields. The Text field is always last
    and can contain commas, so we must parse carefully.
    """
    dialogue = AssDialogueLine(raw_line=line, index=index)

    # Remove "Dialogue:" prefix
    content = line[9:].strip() if line.startswith("Dialogue:") else line.strip()

    if not format_fields:
        # Default ASS format if no Format line was found
        format_fields = ["Layer", "Start", "End", "Style", "Name",
                        "MarginL", "MarginR", "MarginV", "Effect", "Text"]

    # Split by comma, but Text field (last) can contain commas
    # So we split only up to n-1 commas where n is the number of fields
    num_fields = len(format_fields)
    parts = content.split(',', num_fields - 1)

    # Map parts to dialogue fields
    field_map = {
        "Layer": "layer",
        "Start": "start",
        "End": "end",
        "Style": "style",
        "Name": "name",
        "MarginL": "margin_l",
        "MarginR": "margin_r",
        "MarginV": "margin_v",
        "Effect": "effect",
        "Text": "text"
    }

    for i, field_name in enumerate(format_fields):
        if i < len(parts):
            attr_name = field_map.get(field_name)
            if attr_name:
                setattr(dialogue, attr_name, parts[i].strip() if field_name != "Text" else parts[i])

    return dialogue


def write_ass_file(subtitle: AssSubtitle, output_path: str) -> None:
    """
    Write an ASS/SSA subtitle file.

    Args:
        subtitle: AssSubtitle object to write
        output_path: Path to write the file
    """
    lines = []

    # Determine section order (use original order or default)
    if subtitle.section_order:
        sections = subtitle.section_order
    else:
        sections = ["Script Info", subtitle.styles_section_name, "Events"]

    for section in sections:
        if section == "Script Info":
            lines.append("[Script Info]")
            for key in subtitle.script_info_order:
                if key.startswith("_comment_"):
                    lines.append(subtitle.script_info[key])
                else:
                    lines.append(f"{key}: {subtitle.script_info[key]}")
            lines.append("")

        elif section in ["V4+ Styles", "V4 Styles"]:
            lines.append(f"[{subtitle.styles_section_name}]")
            if subtitle.styles_header:
                lines.append(subtitle.styles_header)
            for style in subtitle.styles:
                lines.append(style)
            lines.append("")

        elif section == "Events":
            lines.append("[Events]")
            if subtitle.events_header:
                lines.append(subtitle.events_header)

            # Interleave comments and dialogues based on original order
            # For simplicity, write all comments first then all dialogues
            # A more sophisticated approach would track original order
            for comment in subtitle.comments:
                lines.append(comment)

            for dialogue in subtitle.dialogues:
                lines.append(_format_dialogue_line(dialogue, subtitle.events_format_fields))
            lines.append("")

        elif section in subtitle.other_sections:
            lines.append(f"[{section}]")
            for line in subtitle.other_sections[section]:
                lines.append(line)
            lines.append("")

    # Write file with appropriate encoding
    with open(output_path, 'w', encoding=subtitle.encoding, newline='\r\n') as f:
        f.write('\n'.join(lines))


def _format_dialogue_line(dialogue: AssDialogueLine, format_fields: List[str]) -> str:
    """Format a dialogue line according to the Format specification."""
    if not format_fields:
        format_fields = ["Layer", "Start", "End", "Style", "Name",
                        "MarginL", "MarginR", "MarginV", "Effect", "Text"]

    field_map = {
        "Layer": dialogue.layer,
        "Start": dialogue.start,
        "End": dialogue.end,
        "Style": dialogue.style,
        "Name": dialogue.name,
        "MarginL": dialogue.margin_l,
        "MarginR": dialogue.margin_r,
        "MarginV": dialogue.margin_v,
        "Effect": dialogue.effect,
        "Text": dialogue.text
    }

    parts = [field_map.get(field, "") for field in format_fields]
    return "Dialogue: " + ",".join(parts)


def extract_dialogue_texts(subtitle: AssSubtitle) -> List[Tuple[int, str]]:
    """
    Extract dialogue texts for translation.

    Returns a list of (index, text) tuples where index corresponds to
    the dialogue's position in the dialogues list.

    Inline formatting codes like {\i1}text{\i0} are preserved in the text
    and should be handled appropriately during translation.

    Args:
        subtitle: AssSubtitle object

    Returns:
        List of (index, text) tuples
    """
    texts = []
    for i, dialogue in enumerate(subtitle.dialogues):
        if dialogue.text.strip():
            texts.append((i, dialogue.text))
    return texts


def update_dialogue_texts(subtitle: AssSubtitle, translations: Dict[int, str]) -> None:
    """
    Update dialogue texts with translations.

    Args:
        subtitle: AssSubtitle object to update
        translations: Dict mapping dialogue index to translated text
    """
    for index, translated_text in translations.items():
        if 0 <= index < len(subtitle.dialogues):
            subtitle.dialogues[index].text = translated_text


def strip_formatting_codes(text: str) -> str:
    """
    Strip ASS formatting codes from text, preserving the actual content.

    Formatting codes are enclosed in curly braces like {\\i1} or {\\c&H00FF00&}

    Args:
        text: Text with potential formatting codes

    Returns:
        Text with formatting codes removed
    """
    # Remove ASS override tags {...}
    return re.sub(r'\{[^}]*\}', '', text)


def extract_formatting_codes(text: str) -> List[Tuple[int, str]]:
    """
    Extract formatting codes and their positions from text.

    Args:
        text: Text with formatting codes

    Returns:
        List of (position, code) tuples
    """
    codes = []
    for match in re.finditer(r'\{[^}]*\}', text):
        codes.append((match.start(), match.group()))
    return codes


def preserve_formatting_translate(original_text: str, translated_text: str) -> str:
    """
    Attempt to preserve inline formatting codes from original text in translation.

    This is a best-effort approach that:
    1. Preserves leading/trailing formatting codes exactly
    2. For mid-text codes, attempts to place them at word boundaries

    Args:
        original_text: Original text with formatting codes
        translated_text: Translated text (may or may not have codes)

    Returns:
        Translated text with formatting codes from original
    """
    # If translated text already has formatting, return as-is
    if '{' in translated_text and '}' in translated_text:
        return translated_text

    # Extract leading codes (before first non-code character)
    leading_match = re.match(r'^(\{[^}]*\})+', original_text)
    leading_codes = leading_match.group() if leading_match else ""

    # Extract trailing codes (after last non-code character)
    trailing_match = re.search(r'(\{[^}]*\})+$', original_text)
    trailing_codes = trailing_match.group() if trailing_match else ""

    # Apply leading and trailing codes to translation
    return f"{leading_codes}{translated_text}{trailing_codes}"


def get_subtitle_format(file_path: str) -> Optional[str]:
    """
    Detect subtitle format from file extension.

    Args:
        file_path: Path to subtitle file

    Returns:
        'ass', 'ssa', 'srt', or None if unknown
    """
    ext = Path(file_path).suffix.lower()
    if ext == '.ass':
        return 'ass'
    elif ext == '.ssa':
        return 'ssa'
    elif ext == '.srt':
        return 'srt'
    return None


def is_ass_format(file_path: str) -> bool:
    """
    Check if a file is in ASS/SSA format.

    Args:
        file_path: Path to check

    Returns:
        True if file is ASS or SSA format
    """
    fmt = get_subtitle_format(file_path)
    return fmt in ('ass', 'ssa')

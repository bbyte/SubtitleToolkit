"""
Configuration data classes for SubtitleToolkit script execution.

These classes define the configuration structure for each processing stage
and provide validation methods.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class ExtractConfig:
    """Configuration for MKV subtitle extraction."""

    # Input configuration (can be directory or single file path)
    input_directory: str
    language_code: str = "eng"  # Default to English
    output_directory: Optional[str] = None  # None means same as input

    # Track selection
    track_indices: List[int] = field(default_factory=list)  # Specific track indices to extract

    # Processing options
    recursive: bool = True
    overwrite_existing: bool = False

    # Tool paths (from settings)
    ffmpeg_path: Optional[str] = None
    ffprobe_path: Optional[str] = None

    def validate(self) -> tuple[bool, str]:
        """Validate the extract configuration.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        # Check input path exists (can be directory or file)
        input_path = Path(self.input_directory)
        if not input_path.exists():
            return False, f"Input path does not exist: {self.input_directory}"

        # Validate input path - can be directory or single MKV file
        if input_path.is_file():
            # Single file mode - must be MKV file
            if not input_path.suffix.lower() == '.mkv':
                return False, f"Single file input must be an MKV file: {self.input_directory}"
        elif not input_path.is_dir():
            return False, f"Input path must be either a directory or an MKV file: {self.input_directory}"

        # Check output directory if specified
        if self.output_directory:
            output_path = Path(self.output_directory)
            if not output_path.exists():
                try:
                    output_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    return False, f"Cannot create output directory: {e}"
            elif not output_path.is_dir():
                return False, f"Output path is not a directory: {self.output_directory}"

        # Validate language code format (basic validation)
        if not self.language_code or len(self.language_code) < 2:
            return False, "Language code must be at least 2 characters"

        return True, ""

    def to_cli_args(self) -> List[str]:
        """Convert configuration to CLI arguments for extract_mkv_subtitles.py."""
        args = [self.input_directory]

        # Add track indices if specified (overrides language-based selection)
        if self.track_indices:
            indices_str = ",".join(str(idx) for idx in self.track_indices)
            args.extend(["-t", indices_str])
        elif self.language_code != "eng":
            # Only add language if no specific tracks are specified
            args.extend(["-l", self.language_code])

        if self.output_directory:
            args.extend(["-o", self.output_directory])

        if self.overwrite_existing:
            args.append("--overwrite")

        # Always add JSONL flag for desktop app
        args.append("--jsonl")

        return args

    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables needed for the script."""
        # Extract script doesn't need special environment variables
        return {}


@dataclass
class TranslateConfig:
    """Configuration for SRT translation."""

    # Input configuration
    input_files: List[str] = field(default_factory=list)
    input_directory: Optional[str] = None
    output_directory: Optional[str] = None

    # Translation settings
    source_language: str = "auto"
    target_language: str = "en"
    provider: str = "openai"  # openai, anthropic, lm_studio
    model: str = ""  # Will be set based on provider defaults

    # Provider credentials (from settings)
    api_key: str = ""
    base_url: Optional[str] = None  # For LM Studio

    # Processing options
    max_workers: int = 3
    chunk_size: int = 20
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 30

    # Cost tracking (USD per 1M tokens, 0 = disabled)
    price_input: float = 0.0
    price_output: float = 0.0

    # Output options
    overwrite_existing: bool = False
    preserve_formatting: bool = True

    def validate(self) -> tuple[bool, str]:
        """Validate the translation configuration.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        # Must have either input files or input directory
        if not self.input_files and not self.input_directory:
            return False, "Either input files or input directory must be specified"

        # Check input files exist
        for file_path in self.input_files:
            if not Path(file_path).exists():
                return False, f"Input file does not exist: {file_path}"
            if not file_path.lower().endswith('.srt'):
                return False, f"Input file is not an SRT file: {file_path}"

        # Check input directory if specified
        if self.input_directory:
            input_path = Path(self.input_directory)
            if not input_path.exists():
                return False, f"Input directory does not exist: {self.input_directory}"
            if not input_path.is_dir():
                return False, f"Input path is not a directory: {self.input_directory}"

        # Check output directory if specified
        if self.output_directory:
            output_path = Path(self.output_directory)
            if not output_path.exists():
                try:
                    output_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    return False, f"Cannot create output directory: {e}"
            elif not output_path.is_dir():
                return False, f"Output path is not a directory: {self.output_directory}"

        # Validate provider (both script names and internal names)
        valid_providers = [
            "openai", "claude", "openrouter", "local", "anthropic", "lm_studio",
            "xai", "mistral", "groq", "deepseek", "moonshot", "gemini", "zai",
        ]
        if self.provider not in valid_providers:
            return False, f"Invalid provider: {self.provider}. Must be one of {valid_providers}"

        # Providers that need an API key
        _keyed_providers = {"openai", "claude", "anthropic", "openrouter",
                            "xai", "mistral", "groq", "deepseek", "moonshot", "gemini", "zai"}
        if self.provider in _keyed_providers:
            if not self.api_key:
                _display = {
                    "claude": "Claude", "anthropic": "Claude",
                    "openrouter": "OpenRouter", "xai": "xAI",
                    "mistral": "Mistral", "groq": "Groq",
                    "deepseek": "DeepSeek", "moonshot": "Moonshot (Kimi)",
                    "gemini": "Gemini", "zai": "Z.ai",
                }
                provider_display = _display.get(self.provider, self.provider.upper())
                return False, (f"API key required for {provider_display} provider. "
                               f"Please set the API key in Settings > Translators > {provider_display}.")

            # Validate key format only for providers with known prefixes
            if self.provider in ["claude", "anthropic"]:
                if not self.api_key.startswith("sk-ant-"):
                    return False, ("Invalid Claude API key format. Claude API keys should start with 'sk-ant-'. "
                                   "Please check your API key in Settings > Translators > Claude.")
            elif self.provider == "openai":
                if not self.api_key.startswith("sk-"):
                    return False, ("Invalid OpenAI API key format. OpenAI API keys should start with 'sk-'. "
                                   "Please check your API key in Settings > Translators > OpenAI.")
            elif self.provider == "openrouter":
                if not self.api_key.startswith("sk-or-"):
                    return False, ("Invalid OpenRouter API key format. OpenRouter API keys should start with 'sk-or-'. "
                                   "Please check your API key in Settings > Translators > OpenRouter.")

        # Validate model is specified
        if not self.model:
            return False, f"Model must be specified for provider: {self.provider}"

        # Validate numeric parameters
        if self.max_workers <= 0:
            return False, "Max workers must be positive"
        if self.chunk_size <= 0:
            return False, "Chunk size must be positive"
        if not (0 <= self.temperature <= 2):
            return False, "Temperature must be between 0 and 2"
        if self.max_tokens <= 0:
            return False, "Max tokens must be positive"
        if self.timeout <= 0:
            return False, "Timeout must be positive"

        # Validate language codes
        if not self.source_language or len(self.source_language) < 2:
            return False, "Source language code must be at least 2 characters"
        if not self.target_language or len(self.target_language) < 2:
            return False, "Target language code must be at least 2 characters"

        return True, ""

    def to_cli_args(self) -> List[str]:
        """Convert configuration to CLI arguments for srtTranslateWhole.py."""
        args = []

        # Input specification
        if self.input_files:
            # For multiple files, we'll need to run the script multiple times
            # For now, handle single file case
            if len(self.input_files) == 1:
                # Ensure proper path handling for files with special characters
                file_path = self.input_files[0]
                args.extend(["-f", file_path])
            else:
                # Use directory mode if multiple files
                return []  # Will need special handling
        elif self.input_directory:
            args.extend(["-d", self.input_directory])

        # Output directory
        if self.output_directory:
            args.extend(["-o", self.output_directory])

        # Languages
        args.extend(["--source-lang", self.source_language])
        args.extend(["--target-lang", self.target_language])

        # Provider and model
        args.extend(["-p", self.provider])
        args.extend(["-m", self.model])

        # Processing options (only include supported arguments)
        args.extend(["-w", str(self.max_workers)])
        args.extend(["-s", str(self.chunk_size)])

        # Cost tracking (only pass if non-zero)
        if self.price_input > 0:
            args.extend(["--price-input", str(self.price_input)])
        if self.price_output > 0:
            args.extend(["--price-output", str(self.price_output)])

        # Note: temperature, max_tokens, timeout not supported by script
        # overwrite_existing not supported by script

        # Always add JSONL flag for desktop app
        args.append("--jsonl")

        return args

    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables needed for the script."""
        env = {}

        if not self.api_key:
            return env

        _env_var_map = {
            "openai":     "OPENAI_API_KEY",
            "anthropic":  "ANTHROPIC_API_KEY",
            "claude":     "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "xai":        "XAI_API_KEY",
            "mistral":    "MISTRAL_API_KEY",
            "groq":       "GROQ_API_KEY",
            "deepseek":   "DEEPSEEK_API_KEY",
            "moonshot":   "MOONSHOT_API_KEY",
            "gemini":     "GEMINI_API_KEY",
            "zai":        "ZAI_API_KEY",
        }
        env_var = _env_var_map.get(self.provider)
        if env_var:
            env[env_var] = self.api_key

        return env


@dataclass
class SyncConfig:
    """Configuration for SRT name synchronization."""

    # Input configuration
    input_directory: str

    # Sync settings
    provider: str = "openai"  # openai, claude (script expects 'claude' not 'anthropic')
    model: str = ""  # Will be set based on provider defaults
    confidence_threshold: float = 0.8
    language_filter: str = ""  # Filter by language code (e.g., 'bg' for .bg.srt)

    # Provider credentials (from settings)
    api_key: str = ""

    # Processing options
    dry_run: bool = True  # Default to dry run for safety
    auto_backup_existing: bool = True  # Auto-rename existing target files to .original.srt
    recursive: bool = True
    naming_template: str = "{show_title} - S{season:02d}E{episode:02d} - {episode_title}"

    # Filtering options
    include_patterns: List[str] = field(default_factory=lambda: ["*.srt"])
    exclude_patterns: List[str] = field(default_factory=list)

    def validate(self) -> tuple[bool, str]:
        """Validate the sync configuration.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        # Check input directory exists
        input_path = Path(self.input_directory)
        if not input_path.exists():
            return False, f"Input directory does not exist: {self.input_directory}"
        if not input_path.is_dir():
            return False, f"Input path is not a directory: {self.input_directory}"

        # Validate provider
        # Note: Sync script expects 'claude' not 'anthropic'
        valid_providers = [
            "openai", "claude", "openrouter",
            "xai", "mistral", "groq", "deepseek", "moonshot", "gemini", "zai",
        ]
        if self.provider not in valid_providers:
            return False, f"Invalid provider: {self.provider}. Must be one of {valid_providers}"

        # Check API key
        if not self.api_key:
            return False, f"API key required for provider: {self.provider}"

        # Validate model is specified
        if not self.model:
            return False, "Model must be specified"

        # Validate confidence threshold
        if not (0 <= self.confidence_threshold <= 1):
            return False, "Confidence threshold must be between 0 and 1"

        # Note: The naming template is currently not used by the sync script
        # The script uses AI to match and rename files intelligently
        # Template validation is removed to allow any user preference

        return True, ""

    def to_cli_args(self) -> List[str]:
        """Convert configuration to CLI arguments for srt_names_sync.py."""
        args = [self.input_directory]

        # Provider settings
        args.extend(["--provider", self.provider])
        args.extend(["--model", self.model])
        args.extend(["--min-confidence", str(self.confidence_threshold)])

        # Language filter if specified
        if self.language_filter:
            args.extend(["--language-filter", self.language_filter])

        # Auto-backup existing files
        if self.auto_backup_existing:
            args.append("--auto-backup-existing")

        # Note: Template is not used by the script - script uses AI matching
        # The template field is kept in UI for potential future use
        # if self.naming_template:
        #     args.extend(["--template", self.naming_template])

        # Processing options
        if not self.dry_run:
            args.append("--execute")

        # Note: --no-recursive is not supported by current script
        # if not self.recursive:
        #     args.append("--no-recursive")

        # Note: Include/exclude patterns not supported by current script
        # for pattern in self.include_patterns:
        #     args.extend(["--include", pattern])
        #
        # for pattern in self.exclude_patterns:
        #     args.extend(["--exclude", pattern])

        # Always add JSONL flag for desktop app
        args.append("--jsonl")

        return args

    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables needed for the script."""
        env = {}

        if not self.api_key:
            return env

        _env_var_map = {
            "openai":     "OPENAI_API_KEY",
            "anthropic":  "ANTHROPIC_API_KEY",
            "claude":     "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "xai":        "XAI_API_KEY",
            "mistral":    "MISTRAL_API_KEY",
            "groq":       "GROQ_API_KEY",
            "deepseek":   "DEEPSEEK_API_KEY",
            "moonshot":   "MOONSHOT_API_KEY",
            "gemini":     "GEMINI_API_KEY",
            "zai":        "ZAI_API_KEY",
        }
        env_var = _env_var_map.get(self.provider)
        if env_var:
            env[env_var] = self.api_key

        return env


@dataclass
class FpsSyncConfig:
    """Configuration for subtitle FPS frame-rate conversion."""

    # Input configuration
    input_files: List[str] = field(default_factory=list)
    input_directory: Optional[str] = None

    # FPS settings
    source_fps: float = 25.0          # FPS the subtitles were authored for
    target_fps: Optional[float] = None  # None = auto-detect or use video
    auto_detect: bool = False          # Auto-detect target FPS from paired video

    # Optional explicit video file for FPS detection
    video_file: Optional[str] = None

    # Output options
    output_directory: Optional[str] = None
    overwrite_existing: bool = True    # Overwrite input file in-place by default
    recursive: bool = True

    # Tool paths
    ffprobe_path: Optional[str] = None

    def validate(self) -> tuple[bool, str]:
        """Validate the FPS sync configuration."""
        if not self.input_files and not self.input_directory:
            return False, "Either input files or input directory must be specified"

        for fp in self.input_files:
            if not Path(fp).exists():
                return False, f"Input file does not exist: {fp}"

        if self.input_directory:
            p = Path(self.input_directory)
            if not p.exists():
                return False, f"Input directory does not exist: {self.input_directory}"
            if not p.is_dir():
                return False, f"Input path is not a directory: {self.input_directory}"

        if self.output_directory:
            op = Path(self.output_directory)
            if not op.exists():
                try:
                    op.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    return False, f"Cannot create output directory: {e}"
            elif not op.is_dir():
                return False, f"Output path is not a directory: {self.output_directory}"

        if self.source_fps <= 0:
            return False, "Source FPS must be positive"

        if self.target_fps is not None and self.target_fps <= 0:
            return False, "Target FPS must be positive"

        if self.target_fps is None and not self.auto_detect and not self.video_file:
            return False, "Must specify target FPS, a video file, or enable auto-detect"

        if self.video_file and not Path(self.video_file).exists():
            return False, f"Video file does not exist: {self.video_file}"

        return True, ""

    def to_cli_args(self) -> List[str]:
        """Convert configuration to CLI arguments for srt_fps_convert.py."""
        args = []

        # Input
        if self.input_files:
            args.extend(["-f", self.input_files[0]])
        elif self.input_directory:
            args.extend(["-d", self.input_directory])

        # FPS
        args.extend(["--source-fps", str(self.source_fps)])

        if self.video_file:
            args.extend(["--video", self.video_file])
        elif self.auto_detect:
            args.append("--auto-detect")
        elif self.target_fps is not None:
            args.extend(["--target-fps", str(self.target_fps)])

        # Output
        if self.output_directory:
            args.extend(["-o", self.output_directory])

        if self.overwrite_existing:
            args.append("--overwrite")

        if not self.recursive:
            args.append("--no-recursive")

        if self.ffprobe_path:
            args.extend(["--ffprobe", self.ffprobe_path])

        # Always add JSONL flag for desktop app
        args.append("--jsonl")

        return args

    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables needed for the script."""
        return {}

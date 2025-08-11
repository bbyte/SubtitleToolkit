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
        
        if self.language_code != "eng":
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
        valid_providers = ["openai", "claude", "local", "anthropic", "lm_studio"]
        if self.provider not in valid_providers:
            return False, f"Invalid provider: {self.provider}. Must be one of {valid_providers}"
        
        # Check API key for external providers
        if self.provider in ["openai", "claude", "anthropic"] and not self.api_key:
            provider_display = "Claude" if self.provider in ["claude", "anthropic"] else self.provider.upper()
            return False, f"API key required for provider: {provider_display}"
        
        # Validate model is specified
        if not self.model:
            return False, "Model must be specified"
        
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
                args.extend(["-f", self.input_files[0]])
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
        
        # Note: temperature, max_tokens, timeout not supported by script
        # overwrite_existing not supported by script
        
        # Always add JSONL flag for desktop app
        args.append("--jsonl")
        
        return args
    
    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables needed for the script."""
        env = {}
        
        if self.provider == "openai" and self.api_key:
            env["OPENAI_API_KEY"] = self.api_key
        elif self.provider in ["anthropic", "claude"] and self.api_key:
            env["ANTHROPIC_API_KEY"] = self.api_key
        
        return env


@dataclass
class SyncConfig:
    """Configuration for SRT name synchronization."""
    
    # Input configuration
    input_directory: str
    
    # Sync settings
    provider: str = "openai"  # openai, anthropic
    model: str = ""  # Will be set based on provider defaults
    confidence_threshold: float = 0.8
    
    # Provider credentials (from settings)
    api_key: str = ""
    
    # Processing options
    dry_run: bool = True  # Default to dry run for safety
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
        valid_providers = ["openai", "anthropic"]
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
        
        # Validate naming template has required placeholders
        required_placeholders = ["{show_title}"]  # At minimum
        if not any(placeholder in self.naming_template for placeholder in required_placeholders):
            return False, "Naming template must contain at least {show_title} placeholder"
        
        return True, ""
    
    def to_cli_args(self) -> List[str]:
        """Convert configuration to CLI arguments for srt_names_sync.py."""
        args = [self.input_directory]
        
        # Provider settings
        args.extend(["--provider", self.provider])
        args.extend(["--model", self.model])
        args.extend(["--confidence", str(self.confidence_threshold)])
        
        # Template
        if self.naming_template:
            args.extend(["--template", self.naming_template])
        
        # Processing options
        if not self.dry_run:
            args.append("--execute")
        
        if not self.recursive:
            args.append("--no-recursive")
        
        # Include/exclude patterns
        for pattern in self.include_patterns:
            args.extend(["--include", pattern])
        
        for pattern in self.exclude_patterns:
            args.extend(["--exclude", pattern])
        
        # Always add JSONL flag for desktop app
        args.append("--jsonl")
        
        return args
    
    def get_env_vars(self) -> Dict[str, str]:
        """Get environment variables needed for the script."""
        env = {}
        
        if self.provider == "openai" and self.api_key:
            env["OPENAI_API_KEY"] = self.api_key
        elif self.provider in ["anthropic", "claude"] and self.api_key:
            env["ANTHROPIC_API_KEY"] = self.api_key
        
        return env
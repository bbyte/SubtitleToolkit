# PyInstaller hook for Anthropic package
# This ensures proper bundling of Anthropic resources

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all data files from anthropic package
datas = collect_data_files('anthropic')

# Collect all submodules to ensure complete bundling
hiddenimports = collect_submodules('anthropic')

# Add specific submodules that might be dynamically imported
hiddenimports.extend([
    'anthropic.resources',
    'anthropic._client',
    'anthropic.types',
    'anthropic._base_client',
    'anthropic._streaming',
    'anthropic._types',
    'anthropic._utils',
])
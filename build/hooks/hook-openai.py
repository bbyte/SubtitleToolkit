# PyInstaller hook for OpenAI package
# This ensures proper bundling of OpenAI resources

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all data files from openai package
datas = collect_data_files('openai')

# Collect all submodules to ensure complete bundling
hiddenimports = collect_submodules('openai')

# Add specific submodules that might be dynamically imported
hiddenimports.extend([
    'openai.resources',
    'openai._client',
    'openai.types',
    'openai.types.chat',
    'openai._base_client',
    'openai._streaming',
    'openai._types',
    'openai._utils',
])
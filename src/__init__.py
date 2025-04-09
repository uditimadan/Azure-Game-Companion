"""
Azure Game Companion - A generative AI gaming demo using Azure AI services.

This package provides an interactive game companion that demonstrates 
how Azure OpenAI and Azure Cognitive Services can be used to enhance 
gaming experiences with generative AI capabilities.
"""

# Package version
__version__ = '0.1.0'

# Import main components to make them available at the package level
from config.settings import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY,
    AZURE_SPEECH_KEY,
    AZURE_SPEECH_REGION
)

# Package metadata
__author__ = 'Uditi Madan'
__email__ = 'uditi.madan16@gmail.com'
__description__ = 'AI Game Companion Demo using Azure AI Services'
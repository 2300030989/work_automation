import os

ASSISTANT_NAME = "jarvis"
LLM_KEY = ""  # Google Gemini AI API key

# Default speech recognition language (Google recognizer language codes)
# Examples: 'en-US', 'en-GB', 'hi-IN', 'te-IN', 'es-ES', 'fr-FR'
DEFAULT_SPEECH_LANG = os.getenv('JARVIS_SPEECH_LANG', 'en-IN')

# You can get a free API key from: https://makersuite.google.com/app/apikey
# For now, we'll use a placeholder that won't cause errors
if not LLM_KEY:
    LLM_KEY = os.getenv('GOOGLE_API_KEY', '')

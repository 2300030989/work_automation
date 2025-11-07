import requests
import json
from engine.command import speak

def translate_text(text, target_language='en'):
    """
    Translate text using Google Translate API (free version)
    """
    try:
        # Using Google Translate's free web API
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            'client': 'gtx',
            'sl': 'auto',  # auto-detect source language
            'tl': target_language,  # target language
            'dt': 't',
            'q': text
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0 and len(result[0]) > 0:
                translated_text = result[0][0][0]
                return translated_text
            else:
                return text
        else:
            print(f"Translation API error: {response.status_code}")
            return text
            
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def detect_and_translate_telugu(text):
    """
    Detect if text is in Telugu and translate to English
    """
    # Common Telugu words/phrases for detection
    telugu_indicators = ['nenu', 'chaala', 'bagunnanu', 'నేను', 'చాలా', 'బాగున్నాను']
    
    # Check if text contains Telugu indicators
    text_lower = text.lower()
    if any(indicator in text_lower for indicator in telugu_indicators):
        print(f"Detected Telugu text: {text}")
        translated = translate_text(text, 'en')
        print(f"Translated to English: {translated}")
        return translated
    else:
        # Try to translate anyway in case it's Telugu
        translated = translate_text(text, 'en')
        return translated if translated != text else text

# Test the translation
if __name__ == "__main__":
    test_text = "nenu chaala bagunnanu"
    result = detect_and_translate_telugu(test_text)
    print(f"Original: {test_text}")
    print(f"Translated: {result}")

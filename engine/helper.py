import os
import re
import time
import markdown2
from bs4 import BeautifulSoup

def extract_yt_term(command):
    """Extract a YouTube search/play term from a free-form command.

    The function is forgiving and recognizes patterns like:
      - "play dosti song"
      - "play dosti song on youtube"
      - "youtube play dosti song"
      - "open youtube play dosti song"

    Returns the extracted search term (string) or None if nothing obvious found.
    """
    if not command:
        return None

    cmd = str(command)

    # First try: look for 'play <term>' with optional trailing 'on youtube' or 'in youtube'
    m = re.search(r"play\s+(.*?)(?:\s+(?:on|in)\s+youtube\b)?$", cmd, flags=re.IGNORECASE)
    if m:
        term = m.group(1).strip()
        # strip common trailing words that are not part of the title
        term = re.sub(r"\b(song|video|music)\b$", "", term, flags=re.IGNORECASE).strip()
        # remove leading polite words
        term = re.sub(r"^(please|now|please\s+play)\b\s*", "", term, flags=re.IGNORECASE).strip()
        if term:
            return term

    # Second try: phrases like 'youtube play <term>' or 'youtube <term>'
    m2 = re.search(r"youtube(?:\s+play)?\s+(.*)", cmd, flags=re.IGNORECASE)
    if m2:
        term = m2.group(1).strip()
        term = re.sub(r"\b(song|video|music)\b$", "", term, flags=re.IGNORECASE).strip()
        # strip leading verbs like 'please' or 'now'
        term = re.sub(r"^(please|now)\b\s*", "", term, flags=re.IGNORECASE).strip()
        if term:
            return term

    # Third try: if the whole command contains 'youtube' but also other words, try removing the word 'youtube'
    if 'youtube' in cmd.lower():
        cleaned = re.sub(r"\byoutube\b", "", cmd, flags=re.IGNORECASE).strip()
        # remove starter verbs like 'open', 'launch', 'start', 'play'
        cleaned = re.sub(r"^(open|launch|start|play)\b\s*", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\b(song|video|music)\b$", "", cleaned, flags=re.IGNORECASE).strip()
        # if after cleaning there is remaining text, consider that as the term
        if cleaned:
            return cleaned

    return None


def remove_words(input_string, words_to_remove):
    # Split the input string into words
    words = input_string.split()

    # Remove unwanted words
    filtered_words = [word for word in words if word.lower() not in words_to_remove]

    # Join the remaining words back into a string
    result_string = ' '.join(filtered_words)

    return result_string



# key events like receive call, stop call, go back
def keyEvent(key_code):
    command =  f'adb shell input keyevent {key_code}'
    os.system(command)
    time.sleep(0.2)

# Tap event used to tap anywhere on screen
def tapEvents(x, y):
    command =  f'adb shell input tap {x} {y}'
    os.system(command)
    time.sleep(0.2)

# Input Event is used to insert text in mobile
def adbInput(message):
    command =  f'adb shell input text "{message}"'
    os.system(command)
    time.sleep(0.2)

# to go complete back
def goback(key_code):
    for i in range(6):
        keyEvent(key_code)

# To replace space in string with %s for complete message send
def replace_spaces_with_percent_s(input_string):
    return input_string.replace(' ', '%s')

def markdown_to_text(md):
    html = markdown2.markdown(md)
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text().strip()
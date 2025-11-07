import json
import os
from pipes import quote
import re
import sqlite3
import struct
import subprocess
import time
import webbrowser
import threading
try:
    from playsound import playsound
except Exception:
    # Provide a safe fallback when playsound is not installed so imports don't fail
    def playsound(path):
        print(f"[no-playsound] would play: {path}")
try:
    import eel
except Exception:
    # Lightweight eel stub when 'eel' package is not installed.
    # This prevents ModuleNotFoundError during headless runs or when dependencies
    # are not available. The real GUI requires installing `eel`.
    class _EelStub:
        def init(self, *args, **kwargs):
            print('[eel stub] init', args, kwargs)

        def expose(self, f=None):
            if f is None:
                def _dec(fn):
                    return fn
                return _dec
            return f

        def DisplayMessage(self, msg=None):
            print(f"[eel stub] DisplayMessage: {msg}")

        def ShowHood(self):
            print('[eel stub] ShowHood')

        def hideMicStatus(self):
            print('[eel stub] hideMicStatus')

        def senderText(self, msg=None):
            print(f"[eel stub] senderText: {msg}")

        def receiverText(self, msg=None):
            print(f"[eel stub] receiverText: {msg}")

        def __getattr__(self, name):
            def _noop(*args, **kwargs):
                print(f'[eel stub] call: {name} args={args} kwargs={kwargs}')
            return _noop

    eel = _EelStub()
import pyaudio
import pyautogui
from engine.command import speak
from engine.config import ASSISTANT_NAME, LLM_KEY
# Playing assiatnt sound function
import pywhatkit as kit
import pvporcupine
import requests
from urllib.parse import quote_plus

from engine.helper import extract_yt_term, markdown_to_text, remove_words
from hugchat import hugchat
import pyperclip

con = sqlite3.connect("jarvis.db")
cursor = con.cursor()


def safe_speak(text):
    """Speak in a non-blocking way: spawn a daemon thread to call speak().
    Falls back to synchronous speak if thread creation fails."""
    try:
        threading.Thread(target=speak, args=(text,), daemon=True).start()
    except Exception:
        try:
            speak(text)
        except Exception:
            print(f"speak failed for: {text}")

@eel.expose
def playAssistantSound():
    # Use absolute path for the audio file (safe against CWD differences)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    music_rel = os.path.join('www', 'assets', 'audio', 'start_sound.mp3')
    music_dir = os.path.join(base_dir, music_rel)

    try:
        method_used = None
        # If the file is MP3, skip playsound (playsound uses MCI and often fails on MP3 paths)
        _, ext = os.path.splitext(music_dir)
        if ext.lower() == '.mp3':
            raise RuntimeError('MP3 detected - skip playsound to avoid MCI issues')
        # Try the normal playsound for non-mp3 types
        playsound(music_dir)
        return
    except Exception as e:
        print(f"Could not play audio with playsound: {e}")

    # If playsound failed, try WAV fallback via winsound (Windows) to avoid spawning external players
    # Try WAV fallback using winsound (Windows). If not available, beep.
    base, _ = os.path.splitext(music_dir)
    wav_candidate = base + '.wav'
    if os.name == 'nt' and os.path.exists(wav_candidate):
        try:
            import winsound
            winsound.PlaySound(wav_candidate, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception as e:
            print(f"winsound failed to play wav: {e}")

    # Final fallback: simple beep
    try:
        import winsound
        winsound.Beep(1000, 300)
    except Exception:
        pass
    return

    
def openCommand(query):
    # Normalize early to handle typos and detect qualifiers
    try:
        from engine.enhanced_parser import enhanced_parser
        try:
            query = enhanced_parser.normalize_query(query)
        except Exception:
            pass
    except Exception:
        pass

    # Preserve original query for complex-command detection
    orig_query = query

    # If the user simply said 'play <term>' (no explicit app), assume YouTube for short/music queries
    try:
        if re.search(r"\bplay\b", (orig_query or ''), flags=re.IGNORECASE):
            # Determine if it's a likely music/video request
            rest = re.sub(r"^.*?\bplay\b", '', orig_query, flags=re.IGNORECASE).strip()
            words_after = len(rest.split()) if rest else 0
            is_music_word = bool(re.search(r"\b(song|music|track|video)\b", orig_query, flags=re.IGNORECASE))
            # Heuristic: if user said 'play' and either included music/video keywords or provided a short phrase (<6 words), route to YouTube
            if is_music_word or (words_after > 0 and words_after <= 6):
                try:
                    print(f"openCommand: routing play request to PlayYoutube: {orig_query}")
                    # Call PlayYoutube without showing the UI modal for the old one-line behavior
                    return PlayYoutube(orig_query, show_modal=False)
                except Exception as e:
                    print(f"PlayYoutube routing failed: {e}")
    except Exception:
        pass

    # detect explicit qualifiers for web/desktop
    q_lower = (query or "").lower()
    force_web = bool(re.search(r"\b(web|in web|on web|in browser|in the browser|web version|web\.whatsapp|whatsapp web)\b", q_lower))
    force_desktop = bool(re.search(r"\b(desktop|in desktop|on desktop|desktop app|native app)\b", q_lower))

    # remove assistant name and leading verbs
    query = query.replace(ASSISTANT_NAME, "")
    query = re.sub(r"^(open|launch|start)\b\s*", "", query, flags=re.IGNORECASE)
    query = query.strip()

    # If the original query contains typing/translation intents (e.g. "open notepad and type ..."),
    # delegate to the complex command handler which can open notepad and type the content.
    try:
        # If this utterance contains messaging intents (send/message/dm) and mentions a platform
        # (whatsapp/telegram/instagram), forward to the complex command handler which can extract
        # platform, contact name and message and perform the send.
        if re.search(r"\b(type|write|translate)\b", (orig_query or ""), flags=re.IGNORECASE):
            try:
                # execute_complex_command expects the full textual command, so pass the original
                from engine.features import execute_complex_command
                handled = execute_complex_command(orig_query)
                if handled:
                    return True
            except Exception:
                # If complex command handling fails, fall through to normal open behavior
                pass

        # Detect messaging intents explicitly and forward them to the complex command handler
        if re.search(r"\b(send|message|dm|text|chat)\b", (orig_query or ""), flags=re.IGNORECASE) and \
           re.search(r"\b(whatsapp|telegram|instagram|insta)\b", (orig_query or ""), flags=re.IGNORECASE):
            try:
                from engine.features import execute_complex_command
                handled = execute_complex_command(orig_query)
                if handled:
                    return True
            except Exception as e:
                print(f"execute_complex_command routing failed: {e}")
                pass
    except Exception:
        pass

    # clean qualifiers and extra words
    app_name = query
    app_name = re.sub(r"\b(in|on)(?:\s+the)?\s+desktop(?:\s+app)?\b", "", app_name, flags=re.IGNORECASE)
    app_name = re.sub(r"\b(in|on)(?:\s+the)?\s+browser(?:\s+app)?\b", "", app_name, flags=re.IGNORECASE)
    app_name = re.sub(r"\bdesktop(?:\s+app)?\b", "", app_name, flags=re.IGNORECASE)
    app_name = re.sub(r"\bapp\b", "", app_name, flags=re.IGNORECASE)
    app_name = app_name.strip().lower()

    print(f"Trying to open (raw): '{query}' -> cleaned: '{app_name}' (force_web={force_web}, force_desktop={force_desktop})")

    if not app_name:
        speak("Please specify what to open")
        return False

    # Special-case YouTube: if the user asked to open YouTube with an action (play/search),
    # route to PlayYoutube or a search URL instead of trying to start an executable named
    # 'youtube play ...'
    try:
        if 'youtube' in app_name:
            # If the query includes an intent to play/search, forward to PlayYoutube
            # Use the original query (not cleaned) since it may contain the search term
            q_lower = (query or '').lower()
            if 'play' in q_lower or 'search' in q_lower or 'search for' in q_lower or 'play on youtube' in q_lower:
                try:
                    print(f"Detected YouTube intent in openCommand, forwarding to PlayYoutube: {query}")
                    return PlayYoutube(query)
                except Exception as e:
                    print(f"PlayYoutube forwarding failed: {e}")
                    # Fallthrough to opening YouTube home or search URL
            # If no play/search term, just open youtube.com
                try:
                    # Respect headless mode: do not attempt to open a browser there
                    headless = os.environ.get('JARVIS_HEADLESS', '').lower() in ('1', 'true', 'yes')
                    if headless:
                        print('[headless] would open https://www.youtube.com')
                        return True
                    safe_speak('Opening YouTube')
                    webbrowser.open('https://www.youtube.com')
                    print('Opened via: youtube-web')
                    try:
                        eel.DisplayMessage('Opened YouTube')
                    except Exception:
                        pass
                    return True
                except Exception as e:
                    print(f'openCommand youtube branch failed: {e}')
                    pass
    except Exception:
        pass

    try:
        # If user explicitly asked for web, open WhatsApp Web directly
        if force_web and 'whatsapp' in app_name:
            method_used = 'web'
            speak('Opening WhatsApp Web')
            webbrowser.open('https://web.whatsapp.com/')
            try:
                eel.DisplayMessage(f'Opened WhatsApp via web')
            except Exception:
                pass
            print(f'Opened via: {method_used}')
            return True

        # Try MS Store protocol/URI for some apps (fast path for Store-installed apps)
        store_protocols = {
            'whatsapp': 'whatsapp:',
            # Telegram store protocol possibilities (tg: is common for links)
            'telegram': 'tg:'
        }
        proto = store_protocols.get(app_name)
        if proto:
            try:
                print(f"Trying store protocol: start {proto}")
                rc = os.system(f'start {proto}')
                method_used = 'store-protocol'
                try:
                    eel.DisplayMessage(f'Opened WhatsApp via store protocol')
                except Exception:
                    pass
                print(f'Opened via: {method_used}')
                return True
            except Exception:
                pass

        # Use thread-safe database access
        from engine.thread_safe_db import get_system_command, get_web_command

        # Special handling for notepad - ensure it always opens
        if app_name == 'notepad':
            method_used = 'notepad-direct'
            print(f"Opening notepad directly")
            # Speak in a separate thread to avoid blocking task execution
            try:
                threading.Thread(target=speak, args=("Opening notepad",), daemon=True).start()
            except Exception:
                try:
                    speak("Opening notepad")
                except Exception:
                    pass
            try:
                # Try multiple methods to ensure notepad opens
                os.startfile('notepad.exe')
            except Exception:
                try:
                    os.system('start notepad.exe')
                except Exception:
                    # Last resort - try with full path
                    try:
                        notepad_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32', 'notepad.exe')
                        os.startfile(notepad_path)
                    except Exception as e:
                        print(f"Failed to open notepad: {e}")
                        speak("Could not open notepad")
                        return False
            try:
                eel.DisplayMessage('Opened notepad')
            except Exception:
                pass
            print(f'Opened via: {method_used}')
            return True
        
        # Check system commands first (DB lookup is case-insensitive)
        system_path = get_system_command(app_name)
        if system_path:
            method_used = 'db'
            print(f"Found system command: {system_path}")
            safe_speak("Opening "+app_name)
            try:
                os.startfile(system_path)
            except Exception:
                # fallback to os.system
                try:
                    os.system(f'start "" "{system_path}"')
                except Exception as e:
                    print(f"Failed to open via system command: {e}")
                    return False
            try:
                eel.DisplayMessage(f'Opened {app_name} via saved system command')
            except Exception:
                pass
            print(f'Opened via: {method_used}')
            return True

        # Check web commands
        web_url = get_web_command(app_name)
        if web_url:
            method_used = 'db-web'
            print(f"Found web command: {web_url}")
            safe_speak("Opening "+app_name)
            webbrowser.open(web_url)
            try:
                eel.DisplayMessage(f'Opened {app_name} via saved web command')
            except Exception:
                pass
            print(f'Opened via: {method_used}')
            return True

        # Try to find an executable on PATH
        import shutil
        exe_name = None
        # common exe names for some apps
        common_exec_candidates = {
            'brave': ['brave', 'brave-browser', 'brave.exe', 'brave-browser.exe'],
            'chrome': ['chrome', 'chrome.exe'],
            'edge': ['msedge', 'msedge.exe', 'edge.exe'],
            'firefox': ['firefox', 'firefox.exe'],
            'whatsapp': ['WhatsApp', 'WhatsApp.exe', 'WhatsAppDesktop.exe'],
            'telegram': ['Telegram', 'Telegram.exe', 'TelegramDesktop.exe', 'telegram.exe']
        }

        candidates = common_exec_candidates.get(app_name, [app_name, app_name + '.exe'])
        for c in candidates:
            path = shutil.which(c)
            if path:
                exe_name = path
                break

        # Try common Windows program files locations for known apps (app-specific only)
        if not exe_name:
            program_files = [os.environ.get('PROGRAMFILES', r'C:\Program Files'), os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')]
            app_specific_paths = {
                'brave': [os.path.join('{base}', 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe')],
                'chrome': [os.path.join('{base}', 'Google', 'Chrome', 'Application', 'chrome.exe')],
                'edge': [os.path.join('{base}', 'Microsoft', 'Edge', 'Application', 'msedge.exe')],
                'firefox': [os.path.join('{base}', 'Mozilla Firefox', 'firefox.exe')],
                'whatsapp': [os.path.join('{base}', 'WhatsApp', 'WhatsApp.exe'), os.path.join('{base}', 'WhatsApp', 'WhatsAppDesktop.exe')],
                'telegram': [
                    # Typical installer location under Program Files
                    os.path.join('{base}', 'Telegram Desktop', 'Telegram.exe'),
                    # Per-user install locations (LocalAppData/Programs)
                    os.path.join(os.environ.get('LOCALAPPDATA', r'C:\Users\%USERNAME%\AppData\Local'), 'Programs', 'Telegram Desktop', 'Telegram.exe'),
                    os.path.join(os.environ.get('LOCALAPPDATA', r'C:\Users\%USERNAME%\AppData\Local'), 'Telegram Desktop', 'Telegram.exe'),
                ],
                'vscode': [os.path.join('{base}', 'Microsoft VS Code', 'Code.exe')],
                'pycharm': [os.path.join('{base}', 'JetBrains', 'PyCharm', 'bin', 'pycharm.exe')]
            }

            candidates_for_app = app_specific_paths.get(app_name, [])
            for base in program_files:
                if not base:
                    continue
                for rel in candidates_for_app:
                    p = rel.format(base=base)
                    if os.path.exists(p):
                        exe_name = p
                        break
                if exe_name:
                    break

        # If we found an executable path, launch it
        if exe_name:
            print(f"Found executable: {exe_name}")
            # Persist this mapping for next time
            try:
                from engine.thread_safe_db import save_system_command
                saved = save_system_command(app_name, exe_name)
                if saved:
                    print(f"Saved sys_command: {app_name} -> {exe_name}")
            except Exception:
                pass
            method_used = 'exe'
            safe_speak("Opening "+app_name)
            try:
                os.startfile(exe_name)
            except Exception:
                os.system(f'start "" "{exe_name}"')
            try:
                eel.DisplayMessage(f'Opened {app_name} via executable and saved mapping')
            except Exception:
                pass
            print(f'Opened via: {method_used}')
            return True

        # Special handling: for whatsapp prefer desktop exe, else fallback to web
        if app_name == 'whatsapp':
            method_used = 'web-fallback'
            safe_speak('Opening WhatsApp Web')
            webbrowser.open('https://web.whatsapp.com/')
            try:
                eel.DisplayMessage('Opened WhatsApp via web fallback')
            except Exception:
                pass
            print(f'Opened via: {method_used}')
            return True

        # Fallback: try direct start command
        # Fallback: try direct start command with quoting to avoid mis-parsing
        print(f"Trying direct system command: start {app_name}")
        method_used = 'direct-start'
        safe_speak("Opening "+app_name)
        # Before doing a blind start, try the Windows Start search as a more reliable
        # fallback for modern Windows apps: press Win, type app name, press Enter.
        try:
            if windows_search_open(app_name):
                print('Opened via: windows-start-search')
                try:
                    eel.DisplayMessage(f'Attempted to open {app_name} via start search')
                except Exception:
                    pass
                return True
        except Exception:
            pass

        try:
            os.system(f'start "" "{app_name}"')
        except Exception:
            os.system(f'start {app_name}')
        try:
            eel.DisplayMessage(f'Attempted to open {app_name} via direct start')
        except Exception:
            pass
        print(f'Opened via: {method_used}')
        return True

    except Exception as e:
        # If Telegram failed to open via desktop, try web fallback as a last resort
        try:
            if app_name and 'telegram' in app_name.lower():
                try:
                    print(f"openCommand: fallback -> opening Telegram Web due to error: {e}")
                    safe_speak('Opening Telegram Web')
                    webbrowser.open('https://web.telegram.org/')
                    try:
                        eel.DisplayMessage('Opened Telegram Web as fallback')
                    except Exception:
                        pass
                    return True
                except Exception as _:
                    pass
        except Exception:
            pass
        print(f"Error opening {app_name}: {e}")
        safe_speak(f"Could not open {app_name}")
        return False


def windows_search_open(app_name: str, timeout: float = 2.0) -> bool:
    """Use Windows Start Menu search to find and open an application.
    This presses the Windows key, types the app_name, waits briefly, then presses Enter.
    Returns True if the sequence was performed (does not guarantee app opened).
    Respects the JARVIS_HEADLESS env var to avoid GUI actions in headless tests.
    """
    try:
        headless = os.environ.get('JARVIS_HEADLESS', '').lower() in ('1', 'true', 'yes')
        if headless:
            print(f"[headless] windows_search_open would press Win, type: {app_name}")
            return True

        # Ensure pyautogui is available
        try:
            import pyautogui as _pag
        except Exception:
            print('pyautogui not available for windows_search_open')
            return False

        # Small, conservative timings to avoid flaky behavior
        _pag.press('win')
        time.sleep(0.25)
        # Type the app name slowly but not too slow
        _pag.write(app_name, interval=0.03)
        time.sleep(0.2)
        _pag.press('enter')
        # Allow some time for the app to launch
        time.sleep(timeout)
        return True
    except Exception as e:
        print(f"windows_search_open failed: {e}")
        return False


def diagnose_open(query):
    """Diagnostic helper: shows normalization, DB lookup, PATH probes, and candidate locations for an app."""
    from engine.enhanced_parser import enhanced_parser
    from engine.thread_safe_db import get_system_command, get_web_command, get_all_system_names, get_all_web_names
    import shutil

    raw = query
    normalized = enhanced_parser.normalize_query(query)
    # clean qualifiers like in desktop and remove any leading verbs like 'open'
    cleaned = re.sub(r"\b(in|on)(?:\s+the)?\s+desktop(?:\s+app)?\b", "", normalized, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(in|on)(?:\s+the)?\s+browser(?:\s+app)?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdesktop(?:\s+app)?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bapp\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    # remove leading verb like 'open' or 'launch'
    cleaned = re.sub(r"^(open|launch|start)\b\s*", "", cleaned, flags=re.IGNORECASE).lower()

    print(f"Raw: {raw}")
    print(f"Normalized: {normalized}")
    print(f"Cleaned: {cleaned}")

    db_path = get_system_command(cleaned)
    web_url = get_web_command(cleaned)
    print(f"DB sys_command path: {db_path}")
    print(f"DB web_command url: {web_url}")

    print("Checking PATH candidates with shutil.which()...")
    common_exec_candidates = {
        'brave': ['brave', 'brave-browser', 'brave.exe', 'brave-browser.exe'],
        'chrome': ['chrome', 'chrome.exe'],
        'edge': ['msedge', 'msedge.exe', 'edge.exe'],
        'firefox': ['firefox', 'firefox.exe'],
        'whatsapp': ['WhatsApp', 'WhatsApp.exe', 'WhatsAppDesktop.exe']
    }
    candidates = common_exec_candidates.get(cleaned, [cleaned, cleaned + '.exe'])
    for c in candidates:
        which = shutil.which(c)
        print(f"  which({c}) -> {which}")

    print("Checking app-specific program files locations...")
    program_files = [os.environ.get('PROGRAMFILES', r'C:\Program Files'), os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')]
    app_specific_paths = {
        'brave': [os.path.join('{base}', 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe')],
        'chrome': [os.path.join('{base}', 'Google', 'Chrome', 'Application', 'chrome.exe')],
        'edge': [os.path.join('{base}', 'Microsoft', 'Edge', 'Application', 'msedge.exe')],
        'firefox': [os.path.join('{base}', 'Mozilla Firefox', 'firefox.exe')],
        'whatsapp': [os.path.join('{base}', 'WhatsApp', 'WhatsApp.exe'), os.path.join('{base}', 'WhatsApp', 'WhatsAppDesktop.exe')]
    }
    candidates_for_app = app_specific_paths.get(cleaned, [])
    for base in program_files:
        for rel in candidates_for_app:
            p = rel.format(base=base)
            print(f"  probe: {p} -> exists={os.path.exists(p)}")

    print("Done diagnostics.")
    return True

       

def PlayYoutube(query, show_modal=False):
    # Clean, easy-to-follow implementation
    try:
        headless = os.environ.get('JARVIS_HEADLESS', '').lower() in ('1', 'true', 'yes')

        # Extract a search term from the user query
        search_term = extract_yt_term(query)
        if not search_term:
            # fallback: remove the word 'youtube' and leading verbs
            cleaned = re.sub(r"\byoutube\b", "", str(query), flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"^(open|play|launch)\b\s*", "", cleaned, flags=re.IGNORECASE).strip()
            search_term = cleaned or None

        verbose = os.environ.get('JARVIS_DEBUG', '').lower() in ('1', 'true', 'yes')
        if verbose:
            print(f"PlayYoutube: extracted search_term={repr(search_term)} from query={repr(query)}")

        # If we don't have a search term, open YouTube homepage
        if not search_term:
            print("No search term for YouTube; opening YouTube homepage")
            speak('Opening YouTube')
            if headless:
                print('[headless] would open https://www.youtube.com')
                return True
            webbrowser.open('https://www.youtube.com')
            return True

        # If not headless and eel is available, ask for confirmation before playing
        confirmed = True
        if not headless and show_modal:
            try:
                confirmed = eel.showYouTubeConfirm(search_term)()
            except Exception:
                confirmed = True

        if not confirmed:
            print('User cancelled YouTube play')
            speak('Cancelled')
            return False

        # Try to deterministically find the top video URL from YouTube search page
        def _get_candidate_video_ids(term, max_candidates=6):
            try:
                search_url = f"https://www.youtube.com/results?search_query={quote_plus(term)}"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                resp = requests.get(search_url, headers=headers, timeout=8)
                text = resp.text
                ids = []
                # Find multiple occurrences of videoId
                for m in re.finditer(r'"videoId"\s*:\s*"([\w-]{11})"', text):
                    vid = m.group(1)
                    if vid not in ids:
                        ids.append(vid)
                        if len(ids) >= max_candidates:
                            break
                # Fallback: /watch?v= regex
                if not ids:
                    for m in re.finditer(r"/watch\?v=([\w-]{11})", text):
                        vid = m.group(1)
                        if vid not in ids:
                            ids.append(vid)
                            if len(ids) >= max_candidates:
                                break
                return ids
            except Exception:
                return []

        from difflib import SequenceMatcher

        def _score_candidate(vid, target_term):
            # Query oEmbed for metadata (title, author_name)
            url = f"https://www.youtube.com/watch?v={vid}"
            title = None
            author = None
            try:
                resp = requests.get(f'https://www.youtube.com/oembed?url={quote_plus(url)}&format=json', timeout=4)
                if resp.status_code == 200:
                    j = resp.json()
                    title = (j.get('title') or '').strip()
                    author = (j.get('author_name') or '').strip()
            except Exception:
                pass

            score = 0
            t = (title or '').lower()
            a = (author or '').lower()
            target = (target_term or '').lower()
            # Strong boost for exact title (after stripping non-alphanum)
            def _clean(s):
                return re.sub(r"[^a-z0-9 ]", "", (s or '').lower()).strip()

            ct = _clean(t)
            ctarget = _clean(target)
            if ct and ctarget and ct == ctarget:
                score += 150
            # If the full target appears in title (word sequence), strong boost
            elif ctarget and ctarget in ct:
                score += 80
            else:
                # Partial matches: count how many target words appear in title
                if ctarget:
                    target_words = [w for w in ctarget.split() if w]
                    matched = sum(1 for w in target_words if w in ct)
                    score += matched * 15

            # Similarity boost via SequenceMatcher
            try:
                if title and target:
                    ratio = SequenceMatcher(None, ct, ctarget).ratio()
                    if ratio > 0.9:
                        score += 60
                    elif ratio > 0.75:
                        score += 25
            except Exception:
                pass

            # Moderate bonus if author/channel name indicates a music label
            if any(k in a for k in ('vevo', 'official', 'music', 'tseries', 'lahari', 'sony', 'saregama', 'universal')):
                score += 10

            # small bonus for short titles (likely exact song title)
            if title and len(title) <= 60:
                score += 3

            return score, url, title, author

        candidates = _get_candidate_video_ids(search_term, max_candidates=8)
        top_url = None
        top_title = None
        if candidates:
            best = ( -1, None, None, None )
            for vid in candidates:
                sc, url, title, author = _score_candidate(vid, search_term)
                # print debug only when verbose
                if verbose:
                    print(f"candidate {vid} -> score={sc} title={repr(title)} author={repr(author)}")
                if sc > best[0]:
                    best = (sc, url, title, author)
            if best[1]:
                top_url = best[1]
                top_title = best[2]
        if top_url:
            if verbose:
                print(f"Top YouTube URL found: {top_url} title={repr(top_title)}")
            if headless:
                print(f"[headless] would open: {top_url}")
                return True
            # Try to get a friendly title via oEmbed for UI display
            try:
                oembed = requests.get(f'https://www.youtube.com/oembed?url={quote_plus(top_url)}&format=json', timeout=4)
                title = None
                if oembed.status_code == 200:
                    j = oembed.json()
                    title = j.get('title')
                else:
                    title = None
            except Exception:
                title = None

            try:
                # If eel is available, not headless, and show_modal is requested, notify the front-end with title+url
                if not headless and show_modal:
                    try:
                        eel.displayYouTubeResult(title or top_url, top_url)()
                    except Exception:
                        pass
            except Exception:
                pass

            webbrowser.open(top_url)
            return True

        # Fallbacks: use pywhatkit or open search results
        try:
            if headless:
                print(f"[headless] pywhatkit.playonyt would search for: {search_term}")
                return True
            kit.playonyt(search_term)
            return True
        except Exception as e:
            print(f"pywhatkit.playonyt failed: {e}")
            url = "https://www.youtube.com/results?search_query=" + quote_plus(search_term)
            if headless:
                print(f"[headless] would open search results: {url}")
                return True
            webbrowser.open(url)
            return True
    except Exception as e:
        print(f"Error playing YouTube video: {e}")
        speak("Could not play video on YouTube")
        return False


def hotword():
    porcupine=None
    paud=None
    audio_stream=None
    try:
       
        # pre trained keywords    
        porcupine=pvporcupine.create(keywords=["jarvis","alexa"]) 
        paud=pyaudio.PyAudio()
        audio_stream=paud.open(rate=porcupine.sample_rate,channels=1,format=pyaudio.paInt16,input=True,frames_per_buffer=porcupine.frame_length)
        
        # loop for streaming
        while True:
            keyword=audio_stream.read(porcupine.frame_length)
            keyword=struct.unpack_from("h"*porcupine.frame_length,keyword)

            # processing keyword comes from mic 
            keyword_index=porcupine.process(keyword)

            # checking first keyword detetcted for not
            if keyword_index>=0:
                print("hotword detected")

                # pressing shorcut key win+j
                import pyautogui as autogui
                autogui.keyDown("win")
                autogui.press("j")
                time.sleep(0.2)
                autogui.keyUp("win")
                
    except:
        if porcupine is not None:
            porcupine.delete()
        if audio_stream is not None:
            audio_stream.close()
        if paud is not None:
            paud.terminate()



# find contacts
def findContact(query):
    
    words_to_remove = [ASSISTANT_NAME, 'make', 'a', 'to', 'phone', 'call', 'send', 'message', 'wahtsapp', 'video']
    query = remove_words(query, words_to_remove)

    try:
        query = query.strip().lower()
        cursor.execute("SELECT mobile_no FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?", ('%' + query + '%', query + '%'))
        results = cursor.fetchall()
        print(results[0][0])
        mobile_number_str = str(results[0][0])

        if not mobile_number_str.startswith('+91'):
            mobile_number_str = '+91' + mobile_number_str

        return mobile_number_str, query
    except:
        speak('not exist in contacts')
        return 0, 0
    
def whatsApp(mobile_no, message, flag, name):
    

    if flag == 'message':
        target_tab = 12
        jarvis_message = "message send successfully to "+name

    elif flag == 'call':
        target_tab = 7
        message = ''
        jarvis_message = "calling to "+name

    else:
        target_tab = 6
        message = ''
        jarvis_message = "staring video call with "+name


    # Encode the message for URL
    encoded_message = quote(message)
    print(encoded_message)
    # Construct the URL
    whatsapp_url = f"whatsapp://send?phone={mobile_no}&text={encoded_message}"

    # Construct the full command
    full_command = f'start "" "{whatsapp_url}"'

    # Open WhatsApp with the constructed URL using cmd.exe
    subprocess.run(full_command, shell=True)
    time.sleep(0.5)
    subprocess.run(full_command, shell=True)
    try:
        pyautogui.hotkey('ctrl', 'f')

        for i in range(1, target_tab):
            pyautogui.hotkey('tab')

        pyautogui.hotkey('enter')
        speak(jarvis_message)
        return True
    except Exception as e:
        print(f"whatsApp automation error: {e}")
        # fallback: open WhatsApp Web and return success (best-effort)
        try:
            webbrowser.open('https://web.whatsapp.com/')
        except Exception:
            pass
        return False

# chat bot 
def chatBot(query):
    user_input = query.lower()
    chatbot = hugchat.ChatBot(cookie_path="engine/cookies.json")
    id = chatbot.new_conversation()
    chatbot.change_conversation(id)
    response =  chatbot.chat(user_input)
    print(response)
    speak(response)
    return response

# android automation

def makeCall(name, mobileNo):
    mobileNo =mobileNo.replace(" ", "")
    speak("Calling "+name)
    command = 'adb shell am start -a android.intent.action.CALL -d tel:'+mobileNo
    os.system(command)


# to send message
def sendMessage(message, mobileNo, name):
    from engine.helper import replace_spaces_with_percent_s, goback, keyEvent, tapEvents, adbInput
    message = replace_spaces_with_percent_s(message)
    mobileNo = replace_spaces_with_percent_s(mobileNo)
    speak("sending message")
    goback(4)
    time.sleep(0.2)
    keyEvent(3)
    # open sms app
    tapEvents(136, 2220)
    #start chat
    tapEvents(819, 2192)
    # search mobile no
    adbInput(mobileNo)
    #tap on name
    tapEvents(601, 574)
    # tap on input
    tapEvents(390, 2270)
    #message
    adbInput(message)
    #send
    tapEvents(957, 1397)
    speak("message send successfully to "+name)

def openNotepadAndType(text_to_type):
    """
    Open notepad and type the given text
    """
    try:
        # If running in headless mode (tests/CI), don't perform GUI actions — write to a file instead
        headless = os.environ.get('JARVIS_HEADLESS', '').lower() in ('1', 'true', 'yes')
        if headless:
            try:
                out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tools'))
                os.makedirs(out_dir, exist_ok=True)
                out_file = os.path.join(out_dir, 'headless_notepad_output.txt')
                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write(str(text_to_type))
                print(f"[headless] wrote notepad text to: {out_file}")
                return True
            except Exception as e:
                print(f"[headless] failed to write notepad text: {e}")
                return False
        from engine.auto_typer import type_in_application
        
        # Open notepad
        # Use non-blocking speak to avoid stalling the caller
        try:
            threading.Thread(target=speak, args=("Opening notepad",), daemon=True).start()
        except Exception:
            try:
                speak("Opening notepad")
            except Exception:
                pass
        os.system('start notepad.exe')
        
        # Wait for notepad to open
        time.sleep(0.5)
        
        # Type the text. For longer texts, type sentence-by-sentence with pauses
        # Use non-blocking speak for status messages
        try:
            threading.Thread(target=speak, args=("Typing the content in notepad",), daemon=True).start()
        except Exception:
            try:
                speak("Typing the content in notepad")
            except Exception:
                pass
        success = False
        try:
            if isinstance(text_to_type, str) and len(text_to_type) > 120:
                # Split into sentence-like chunks for natural slow typing
                import re as _re
                sentences = _re.split(r'(?<=[\.!?])\s+', text_to_type.strip())
                if not sentences:
                    sentences = [text_to_type]

                for i, s in enumerate(sentences):
                    s = s.strip()
                    if not s:
                        continue
                    # Type each sentence with a slightly slower per-character delay
                    type_in_application(s, delay=0.04)
                    # Add a short pause between sentences to appear natural
                    time.sleep(0.6)
                    # Optionally add a newline between sentences for readability
                    pyautogui.press('enter')

                success = True
            else:
                success = type_in_application(text_to_type, delay=0.03)
        except Exception as e:
            print(f"Sentence-by-sentence typing failed: {e}")
            # Fallback: try clipboard paste
            try:
                pyperclip.copy(text_to_type)
                time.sleep(0.2)
                pyautogui.hotkey('ctrl', 'v')
                success = True
            except Exception as e2:
                print(f"Clipboard paste fallback failed: {e2}")
                success = False
        
        if success:
            # Reset UI (hide mic/status) when running with UI present BEFORE speaking
            try:
                print('[features] calling eel.ShowHood()')
                eel.ShowHood()
                print('[features] eel.ShowHood() called')
            except Exception as _e:
                print(f"[features] eel.ShowHood() raised: {_e}")
            try:
                print('[features] calling eel.hideMicStatus()')
                eel.hideMicStatus()
                print('[features] eel.hideMicStatus() called')
            except Exception as _e:
                print(f"[features] eel.hideMicStatus() raised: {_e}")
            # Announce in background so UI updates are not blocked by TTS
            safe_speak("Text has been typed in notepad successfully")
        else:
            try:
                print('[features] calling eel.ShowHood() (failure path)')
                eel.ShowHood()
                print('[features] eel.ShowHood() called (failure path)')
            except Exception as _e:
                print(f"[features] eel.ShowHood() raised (failure path): {_e}")
            try:
                print('[features] calling eel.hideMicStatus() (failure path)')
                eel.hideMicStatus()
                print('[features] eel.hideMicStatus() called (failure path)')
            except Exception as _e:
                print(f"[features] eel.hideMicStatus() raised (failure path): {_e}")
            safe_speak("Failed to type text in notepad")
            
        return success
        
    except Exception as e:
        print(f"Error in openNotepadAndType: {e}")
        speak("Sorry, I couldn't open notepad or type the text")
        return False

def execute_complex_command(query):
    """
    Execute complex commands like 'open notepad and type translated text'
    """
    try:
        from engine.translator import detect_and_translate_telugu
        
        query_lower = query.lower()
        # Support patterns like:
        # - open notepad and write <text>
        # - open notepad and write on <topic>
        # - open notepad and type <text>
        # - open notepad and translate "<text>"
        import re

        # --- Robust messaging automation (WhatsApp, Telegram, Instagram)
        # Approach: split the utterance into sub-commands using the enhanced parser,
        # then run a small state machine to extract platform, contact name, and message.
        try:
            from engine.enhanced_parser import enhanced_parser as _parser
            parts = _parser.extract_commands(query)
            # parts is a list of dicts with 'type' and 'query'
            platform = None
            contact_name = None
            message_text = None

            # Prepare a small helper to detect greetings (we don't want to treat 'hi' as a contact)
            def _is_greeting(s: str) -> bool:
                if not s:
                    return False
                g = {'hi', 'hello', 'hey', 'hi there', 'hello there', 'good morning', 'good evening', 'good afternoon'}
                return s.strip().lower() in g

            # First pass: find explicit platform and 'search' parts to get contact
            for p in parts:
                ptext = (p.get('query') or '') if isinstance(p, dict) else str(p)
                low = ptext.lower()
                # detect platform
                if 'whatsapp' in low:
                    platform = 'whatsapp'
                    continue
                if 'telegram' in low:
                    platform = 'telegram'
                    continue
                if 'instagram' in low or 'insta' in low:
                    platform = 'instagram'
                    continue

                # prefer contact extraction from explicit search/find parts
                if re.search(r"\b(search|find|name)\b", low):
                    # Try to extract pattern: "search for <name>" or "search <name>" or "find <name>"
                    name_match = re.search(r"(?:search|find|name)(?:\s+for)?\s+([A-Za-z0-9_\-\.]{1,50})(?:\s+send\s+(.+))?$", ptext, flags=re.IGNORECASE)
                    if name_match:
                        potential_contact = name_match.group(1).strip()
                        potential_msg = name_match.group(2).strip() if name_match.lastindex >= 2 and name_match.group(2) else ''
                        # Clean contact name
                        potential_contact = re.sub(r"\b(open|telegram|whatsapp|instagram|insta|and|then)\b", '', potential_contact, flags=re.IGNORECASE).strip()
                        if potential_contact and not _is_greeting(potential_contact):
                            contact_name = potential_contact
                            if potential_msg and not message_text:
                                message_text = potential_msg
                            continue
                    
                    # Fallback: Remove the token 'search/find/name' then aggressively clean
                    txt = re.sub(r"\b(search|find|name)\b", '', ptext, flags=re.IGNORECASE).strip()
                    # remove leading prepositions and common verbs like 'open'
                    txt = re.sub(r"^(for|the|named?|to)\b\s*", '', txt, flags=re.IGNORECASE).strip()
                    txt = re.sub(r"^(open|launch|start)\b\s*", '', txt, flags=re.IGNORECASE).strip()
                    # strip platform words if present (telegram/whatsapp/instagram)
                    txt = re.sub(r"\b(whatsapp|telegram|instagram|insta)\b", '', txt, flags=re.IGNORECASE).strip()
                    # remove leftover conjunctions or punctuation
                    txt = re.sub(r"\b(and|then|also)\b", '', txt, flags=re.IGNORECASE).strip()
                    txt = txt.strip('"\'').strip()
                    
                    # Check if this text contains "send" - if so, split on "send" to get contact and message
                    if re.search(r"\bsend\b", txt, flags=re.IGNORECASE):
                        # Split on "send" - everything before is contact, after is message
                        send_split = re.split(r"\bsend\b", txt, flags=re.IGNORECASE, maxsplit=1)
                        if len(send_split) >= 2:
                            potential_contact = send_split[0].strip()
                            potential_msg = send_split[1].strip()
                            # Clean contact from remaining platform/action words
                            potential_contact = re.sub(r"\b(open|telegram|whatsapp|instagram|insta|search|find)\b", '', potential_contact, flags=re.IGNORECASE).strip()
                            if potential_contact and not _is_greeting(potential_contact):
                                contact_name = potential_contact
                                # Store message for later if not already set
                                if potential_msg and not message_text:
                                    message_text = potential_msg
                                continue
                    
                    # Final cleanup - remove any remaining action words
                    txt = re.sub(r"\b(open|search|find|send|message)\b", '', txt, flags=re.IGNORECASE).strip()
                    if txt and not _is_greeting(txt) and len(txt.split()) <= 3:  # Only accept if it looks like a name (max 3 words)
                        contact_name = txt
                        continue

            # Second pass: collect messages from 'send' parts and also fallback contact if missing
            for p in parts:
                ptext = (p.get('query') or '') if isinstance(p, dict) else str(p)
                low = ptext.lower()
                if re.search(r"\b(send|message|dm|say|saying|says|tell)\b", low):
                    # strip leading verbs
                    txt = re.sub(r"^(send|message|dm)\b\s*", '', ptext, flags=re.IGNORECASE).strip()
                    
                    # If we already have a contact_name and it appears in this text, extract message after the contact
                    if contact_name and contact_name.lower() in txt.lower():
                        # Split on the contact name to get the message part
                        parts_after_contact = re.split(re.escape(contact_name), txt, flags=re.IGNORECASE, maxsplit=1)
                        if len(parts_after_contact) > 1:
                            msg_part = parts_after_contact[1].strip()
                            # Remove any remaining action words like "send", "message", "saying"
                            msg_part = re.sub(r"^(send|message|dm|saying|says)\b\s*", '', msg_part, flags=re.IGNORECASE).strip()
                            # Remove common connecting words
                            msg_part = re.sub(r"^(to|on|in|for)\b\s*", '', msg_part, flags=re.IGNORECASE).strip()
                            if msg_part:
                                message_text = msg_part
                                continue
                    
                    # Pattern: "to <name> on <platform> saying <message>" or "to <name> saying <message>"
                    m = re.search(r"\bto\s+([A-Za-z0-9_]{1,30})\b.*?(?:saying|says|:)?\s*(.+)$", txt, flags=re.IGNORECASE)
                    if m:
                        maybe_name = m.group(1).strip()
                        maybe_msg = m.group(2).strip() if m.lastindex >= 2 else ''
                        # Remove platform words from message
                        maybe_msg = re.sub(r"\b(telegram|whatsapp|instagram|insta)\b", '', maybe_msg, flags=re.IGNORECASE).strip()
                        if maybe_msg and not message_text:
                            message_text = maybe_msg
                        if not contact_name and maybe_name and not _is_greeting(maybe_name):
                            contact_name = maybe_name
                            continue
                    
                    # Pattern: if text starts with 'to <name> ...', extract possible name and message
                    m = re.match(r"^(?:to\s+)?([A-Za-z ]{1,40})(?:\s+(?:saying|says|:|,)?\s*(.*))?$", txt, flags=re.IGNORECASE)
                    if m:
                        maybe_name = (m.group(1) or '').strip()
                        maybe_msg = (m.group(2) or '').strip()
                        # Clean message from platform words
                        maybe_msg = re.sub(r"\b(telegram|whatsapp|instagram|insta|on)\b", '', maybe_msg, flags=re.IGNORECASE).strip()
                        if maybe_msg and not message_text:
                            message_text = maybe_msg
                        # If contact not set and maybe_name looks like a name (not greeting), set it
                        if not contact_name and maybe_name and not _is_greeting(maybe_name):
                            # avoid capturing short greetings as names
                            contact_name = maybe_name
                            continue
                        # If maybe_name is a greeting, treat whole txt as message
                        if _is_greeting(maybe_name) and not message_text:
                            # Extract just the message part, removing platform words
                            clean_msg = re.sub(r"\b(telegram|whatsapp|instagram|insta|on|to|saying|says)\b", '', txt, flags=re.IGNORECASE).strip()
                            if clean_msg:
                                message_text = clean_msg
                            else:
                                message_text = txt
                            continue
                    else:
                        # fallback: everything after send is message (clean it first)
                        clean_txt = re.sub(r"\b(telegram|whatsapp|instagram|insta|on|to|saying|says)\b", '', txt, flags=re.IGNORECASE).strip()
                        if not message_text:
                            message_text = clean_txt if clean_txt else txt

                # If still no contact, try to detect 'platform NAME' patterns like 'whatsapp praveen'
                if not contact_name and re.search(r"\b(whatsapp|telegram|instagram)\b", low):
                    # strip platform word
                    txt = re.sub(r"\b(whatsapp|telegram|instagram|insta)\b", '', ptext, flags=re.IGNORECASE).strip()
                    txt = re.sub(r"^(for|to|name)\b\s*", '', txt, flags=re.IGNORECASE).strip()
                    if txt and not _is_greeting(txt):
                        contact_name = txt
                        continue

            # If we still don't have a contact_name, try cross-part extraction for natural phrases
            # like: "open telegram and search for praveen then say hi" where the platform
            # is in one part and the search/name is in the following part.
            if platform and not contact_name:
                for i, p in enumerate(parts):
                    ptext = (p.get('query') or '') if isinstance(p, dict) else str(p)
                    low = ptext.lower()
                    # If this part mentions the platform, look at the next part for a name
                    if re.search(rf"\b{re.escape(platform)}\b", low) and i + 1 < len(parts):
                        nxt = parts[i+1]
                        nxt_text = (nxt.get('query') or '') if isinstance(nxt, dict) else str(nxt)
                        # Try to extract name from patterns like 'search for X', 'find X', 'search X'
                        m = re.search(r"(?:search|find)(?:\s+for)?\s+(['\"]?)([A-Za-z0-9 _\-\.']{1,60})\1", nxt_text, flags=re.IGNORECASE)
                        if m:
                            cand = m.group(2).strip()
                        else:
                            # fallback: remove common verbs and platform words
                            cand = re.sub(r"\b(search|find|for|the|to|name|open|launch|start)\b", '', nxt_text, flags=re.IGNORECASE).strip()
                            cand = re.sub(r"\b(whatsapp|telegram|instagram|insta)\b", '', cand, flags=re.IGNORECASE).strip()
                        cand = cand.strip('"\'').strip()
                        if cand and not _is_greeting(cand):
                            contact_name = cand
                            break

            # If we found a platform and a contact_name, attempt send
            # Fallback: if we didn't extract a message_text from parts, try a final
            # regex over the whole query to capture patterns like 'send hola' or 'say hello'
            if not message_text:
                try:
                    fb = re.search(r"\b(?:send|say|saying|says)\b\s*(?:to\s+[A-Za-z0-9_@\.]+\s*)?[:\-]?\s*['\"]?(.+?)['\"]?\s*$", query, flags=re.IGNORECASE)
                    if fb and fb.group(1):
                        message_text = fb.group(1).strip()
                        print(f"execute_complex_command: fallback extracted message_text='{message_text}' from query='{query}'")
                except Exception as _e:
                    print(f"execute_complex_command: fallback message extraction failed: {_e}")
            if platform and contact_name:
                try:
                    contact_no, resolved_name = findContact(contact_name)
                except Exception:
                    contact_no, resolved_name = 0, contact_name

                if contact_no and contact_no != 0:
                    # Only send a message when an explicit message_text was provided.
                    # If no message_text is present, just open/select the chat without sending.
                    if message_text:
                        # route via whatsApp helper or platform-specific senders
                        if platform == 'whatsapp':
                            try:
                                whatsApp(contact_no, message_text, 'message', resolved_name)
                                return True
                            except Exception as e:
                                print(f"WhatsApp automation failed: {e}")
                                return False
                        elif platform == 'telegram':
                            # For Telegram, prefer desktop automation when message is provided
                            cleaned_name = resolved_name or contact_name
                            try:
                                if telegram_desktop_send(cleaned_name, message_text):
                                    return True
                            except Exception as e:
                                print(f"Telegram desktop send failed: {e}")
                            # Fallback to Telethon API if available
                            try:
                                if send_telegram(cleaned_name, message_text):
                                    return True
                            except Exception as e:
                                print(f"Telegram API send failed: {e}")
                            # Last resort: open via web/app (won't send, but opens chat)
                            if sendInApp(platform, contact_no, message_text, resolved_name):
                                print(f"Note: Opened Telegram but message may not be sent automatically")
                                return True
                            return False
                        else:
                            # Use generic helper for other platforms
                            if sendInApp(platform, contact_no, message_text, resolved_name):
                                return True
                            else:
                                print(f"sendInApp failed for {platform}")
                                return False
                    else:
                        # No message: open/select the chat only. Prefer desktop automation
                        try:
                            cleaned_name = resolved_name or contact_name
                            if platform == 'telegram':
                                if telegram_desktop_send(cleaned_name, ''):
                                    return True
                            if platform == 'whatsapp':
                                if whatsapp_desktop_send(cleaned_name, ''):
                                    return True
                            # For other platforms, fall back to opening via web/helper
                            if sendInApp(platform, contact_no, '', resolved_name):
                                return True
                        except Exception as e:
                            print(f"Open-chat (no message) fallback failed: {e}")
                        speak(f"I couldn't open the chat for {contact_name}")
                        return False
                else:
                    # If contact_name looks like a phone number, use it directly for WhatsApp/Telegram
                    def is_phone_number(s):
                        return bool(re.match(r"^(\+?91)?[6-9][0-9]{9}$", s.strip()))

                    cleaned_name = contact_name.strip()
                    if is_phone_number(cleaned_name):
                        # Format as +91 if missing
                        if not cleaned_name.startswith('+91'):
                            cleaned_name = '+91' + cleaned_name[-10:]
                        if platform == 'whatsapp':
                            if whatsApp(cleaned_name, message_text or '', 'message', cleaned_name):
                                return True
                        if platform == 'telegram':
                            # Telegram can use phone number for desktop send
                            if telegram_desktop_send(cleaned_name, message_text or ''):
                                return True
                        # For other platforms, fallback to generic sendInApp
                        if sendInApp(platform, cleaned_name, message_text or '', cleaned_name):
                            return True
                        speak(f"Tried sending to {cleaned_name}")
                        return False

                    # Otherwise, extract a clean contact name for desktop automation
                    def clean_contact_name(raw):
                        words_to_remove = [platform, 'open', 'search', 'find', 'send', 'message', 'dm', 'text', 'chat', 'to', 'and']
                        txt = raw
                        for w in words_to_remove:
                            txt = re.sub(rf"\\b{re.escape(w)}\\b", '', txt, flags=re.IGNORECASE)
                        txt = txt.strip().strip('"\'').strip()
                        return txt if txt else raw

                    cleaned_name = clean_contact_name(contact_name)
                    try:
                        # Do not default to 'Hi' when opening the desktop client; only send when a message was provided.
                        if platform == 'telegram':
                            if telegram_desktop_send(cleaned_name, message_text or ''):
                                return True
                        if platform == 'whatsapp':
                            if whatsapp_desktop_send(cleaned_name, message_text or ''):
                                return True
                    except Exception as e:
                        print(f"Desktop-send fallback failed: {e}")

                    speak(f"I couldn't find contact {cleaned_name} in your phonebook")
                    return False
        except Exception:
            # If any error here, fall through to other complex handling below
            pass

        # --- end whatsapp automation

        if "open notepad" in query_lower and ("translate" in query_lower or "type" in query_lower or "write" in query_lower):
            # Initialize flag to track if this is an "about" topic (for story generation)
            is_about_topic = False
            
            # Try quoted text first
            quoted_match = re.search(r'"([^"]*)"', query)
            if quoted_match:
                text_to_type = quoted_match.group(1)
            else:
                # Look for patterns after write/type/translate
                # First, specifically handle "type about X" or "write about X" pattern (for ANY topic)
                # Also handles "type about X in notepad" format - extract topic before "in notepad"
                about_pattern = re.search(r'(?:write|type)\s+about\s+([^.\n]+?)(?:\s+(?:in|on)\s+(?:notepad|the)\s+|\s+and\s+|\s+then\s+|$)', query, flags=re.IGNORECASE)
                if about_pattern:
                    # Extract the topic after "about" - works for ANY topic (tesla, apple, python, yourself, etc.)
                    text_to_type = about_pattern.group(1).strip()
                    # Mark this as an "about" topic so story generation happens later
                    is_about_topic = True
                else:
                    # Try general pattern for quoted text or direct text
                    m = re.search(r'(?:write(?: on| about)?|type(?: about)?|translate)\s*(?:to|in)?\s*(?:\'([^\']+)\'|"([^"]+)"|(?:about\s+)?(.+?)(?:\s+and\s+|\s+then\s+|$))', query, flags=re.IGNORECASE)
                    if m:
                        # pick the first non-empty capture
                        text_to_type = (m.group(1) or m.group(2) or m.group(3) or "").strip()
                    else:
                        # As a last resort, try to capture anything after 'write' or 'type'
                        m2 = re.search(r"(?:write(?: on| about)?|type(?: about)?)\s+(.+?)(?:\s+and\s+|\s+then\s+|$)", query, flags=re.IGNORECASE)
                        if m2:
                            text_to_type = m2.group(1).strip()
                        else:
                            # Ask user via voice input for the text to write
                            try:
                                from engine.command import takecommand
                                speak("What should I write in notepad?")
                                voice_text = takecommand()
                                if not voice_text:
                                    speak("I didn't receive any text to write")
                                    return False
                                text_to_type = voice_text
                            except Exception:
                                # fallback default
                                text_to_type = ""

            text_to_type = (text_to_type or "").strip().strip('"\'')
            if not text_to_type:
                speak("No text found to type in notepad")
                return False

            # If the command targeted YouTube typing, handle specially
            # Handle patterns like: "open youtube type in search bar Bahubali full movie"
            try:
                # look for youtube + typing/search intent
                yt_search_match = None
                if "youtube" in query_lower and ("search" in query_lower or "search bar" in query_lower or "type in search" in query_lower or "type in search bar" in query_lower):
                    # extract the search phrase after keywords
                    m = re.search(r"""(?:search(?:\s+for)?|type(?:\s+in)?(?:\s+the)?(?:\s+search\s+bar)?|type\s+in\s+search)\s+(?:for\s+)?(?:'([^']+)'|"([^"]+)"|(.+))""", query, flags=re.IGNORECASE)
                    if m:
                        yt_search_match = (m.group(1) or m.group(2) or m.group(3) or "").strip()
                    else:
                        # try simpler capture: anything after 'search' or 'search bar'
                        m2 = re.search(r"(?:search(?:\s+for)?|search\s+bar)\s+(.+)$", query, flags=re.IGNORECASE)
                        if m2:
                            yt_search_match = m2.group(1).strip()

                if yt_search_match:
                    # Open YouTube search results directly
                    try:
                        import urllib.parse
                        term = yt_search_match
                        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(term)
                        print(f"YouTube search URL: {url}")
                        speak(f"Searching YouTube for {term}")
                        webbrowser.open(url)
                        return True
                    except Exception as e:
                        print(f"YouTube search handling failed: {e}")
                        # fall through to normal behavior
                        pass
            except Exception:
                pass

            print(f"Text to type in notepad: {text_to_type}")

            # Detect requests to write a story/essay about a topic
            # This works for ANY topic the user mentions: tesla, apple, python, yourself, space, ai, etc.
            try:
                # Check if we already detected "type about X" pattern
                if is_about_topic:
                    # We already extracted the topic from "type about X" - use it directly
                    topic = text_to_type.strip()
                else:
                    # Try to match "write/type about X" or "write/type a story about X" patterns in the query
                    write_story_pattern = re.search(r"(?:write|type)\s+(?:a\s+story\s+about|an\s+essay\s+about|an\s+essay\s+on|essay\s+about|about)\s*(.+)", query, flags=re.IGNORECASE)
                    # Also handle when extracted text itself starts with 'about '
                    if write_story_pattern:
                        topic = write_story_pattern.group(1).strip().strip('"\'')
                    elif text_to_type.lower().startswith('about '):
                        topic = text_to_type[6:].strip()
                    else:
                        topic = None
            except Exception:
                topic = None

            if topic:
                # Generate an expanded story/essay for the topic
                def generate_story(t, short=True):
                    """Generate text about topic t. If short=True produce 1-2 sentences, else a longer 4-6 sentence paragraph."""
                    t = t.strip()
                    # Prefer using Google Generative API if configured
                    try:
                        if LLM_KEY:
                            try:
                                import google.generativeai as _genai
                                _genai.configure(api_key=LLM_KEY)
                                model = _genai.GenerativeModel("gemini-2.0-flash")
                                if short:
                                    prompt = f"Write a concise 1-2 sentence summary about {t} in clear English."
                                else:
                                    prompt = f"Write a short, engaging 4-6 sentence story about {t} in clear English."
                                response = model.generate_content(prompt)
                                return response.text
                            except Exception as e:
                                print(f"genai error: {e}")
                                # fall through to template
                        # No LLM or genai failed — return a simple template paragraph
                        if short:
                            sentences = [
                                f"{t} is a notable figure known for significant contributions in their field.",
                                f"{t} has had an important impact on many people and developments in recent years."
                            ]
                        else:
                            sentences = [
                                f"Here is a short story about {t}.",
                                f"{t} has had a significant impact on many people and events, shaping important moments in recent times.",
                                f"Many admire {t} for leadership, resilience, and the ability to connect with a wide audience.",
                                f"Through challenges and achievements, {t} remains a central figure in public life, inspiring others in various ways.",
                                "This story captures a brief, thoughtful snapshot rather than a comprehensive biography."
                            ]
                        return "\n\n".join(sentences)
                    except Exception as e:
                        print(f"Error generating story: {e}")
                        return text_to_type

                # Choose short vs long output: default to short when the user said simply 'write about <topic>'
                lower_q = query.lower()
                explicit_long = bool(re.search(r"\b(story|essay|long|paragraph)\b", lower_q))
                story_text = generate_story(topic, short=not explicit_long)
                return openNotepadAndType(story_text)

            # If translation requested, translate then type
            if 'translate' in query_lower:
                try:
                    translated_text = detect_and_translate_telugu(text_to_type)
                except Exception as e:
                    print(f"Translation failed: {e}")
                    speak("Translation failed, typing original text instead")
                    translated_text = text_to_type
                return openNotepadAndType(translated_text)

            # Normal typing
            return openNotepadAndType(text_to_type)

        return False

    except Exception as e:
        print(f"Error in execute_complex_command: {e}")
        return False

import google.generativeai as genai
def geminai(query):
    try:
        if not LLM_KEY:
            # Fallback to basic responses when no API key
            fallback_responses = {
                "hello": "Hello! How can I help you today?",
                "time": f"The current time is {time.strftime('%H:%M')}",
                "date": f"Today's date is {time.strftime('%B %d, %Y')}",
                "weather": "I don't have access to weather data right now. Please check a weather app.",
                "search": "I can help you search, but I need a Google API key for advanced AI responses."
            }
            
            query_lower = query.lower()
            for key, response in fallback_responses.items():
                if key in query_lower:
                    speak(response)
                    return
            
            speak("I'm sorry, I don't have access to AI features right now. Please set up a Google API key for full functionality.")
            return
        
        query = query.replace(ASSISTANT_NAME, "")
        query = query.replace("search", "")
        # Set your API key
        genai.configure(api_key=LLM_KEY)

        # Select a model
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Generate a response
        response = model.generate_content(query)
        filter_text = markdown_to_text(response.text)
        speak(filter_text)
    except Exception as e:
        print("Error:", e)
        speak("I'm having trouble processing that request right now.")


def sendInApp(platform, contact_no, message, name=None):
    """Generic send helper for messaging platforms. Returns True on success.

    Conservative implementation:
    - whatsapp: uses whatsApp helper
    - telegram: tries t.me/<username> or opens web.telegram.org
    - instagram: opens instagram direct inbox or profile
    Headless mode (JARVIS_HEADLESS) will simulate success and only log actions.
    """
    try:
        p = (platform or '').lower()
        headless = os.environ.get('JARVIS_HEADLESS', '').lower() in ('1', 'true', 'yes')

        if p == 'whatsapp':
            try:
                whatsApp(contact_no, message, 'message', name or contact_no)
                return True
            except Exception as e:
                print(f"whatsApp send failed: {e}")
                return False

        if p == 'telegram':
            # contact_no might be a username (e.g. '@user') or phone number
            try:
                if headless:
                    print(f"[headless] would open Telegram for contact: {contact_no}, message: {message}")
                    return True

                # If contact_no looks like a username
                if isinstance(contact_no, str) and contact_no.startswith('@'):
                    username = contact_no.lstrip('@')
                    url = f'https://t.me/{quote_plus(username)}'
                    webbrowser.open(url)
                    return True

                # If contact_no looks like plain username (no plus/plus-digit), try t.me
                if isinstance(contact_no, str) and re.match(r'^[A-Za-z0-9_\.]+$', contact_no):
                    url = f'https://t.me/{quote_plus(contact_no)}'
                    webbrowser.open(url)
                    return True

                # Fallback: open web Telegram for the user to complete action
                webbrowser.open('https://web.telegram.org/')
                return True
            except Exception as e:
                print(f"telegram sendInApp fallback failed: {e}")
                return False

        if p in ('instagram', 'insta'):
            try:
                if headless:
                    print(f"[headless] would open Instagram inbox/profile for {contact_no}")
                    return True

                # If contact_no looks like a username, open profile
                if isinstance(contact_no, str) and re.match(r'^[A-Za-z0-9_.]+$', contact_no):
                    profile_url = f'https://www.instagram.com/{quote_plus(contact_no)}/'
                    webbrowser.open(profile_url)
                    return True

                # Fallback: open Instagram direct inbox page
                webbrowser.open('https://www.instagram.com/direct/inbox/')
                return True
            except Exception as e:
                print(f"instagram sendInApp fallback failed: {e}")
                return False

        print(f"Unsupported platform for sendInApp: {platform}")
        return False
    except Exception as e:
        print(f"sendInApp error: {e}")
        return False


def send_telegram(contact, message):
    """Send a Telegram message using Telethon (user-auth client).
    Required env vars: TELEGRAM_API_ID, TELEGRAM_API_HASH, optional TELEGRAM_SESSION
    Returns True on success, False otherwise. Respects JARVIS_HEADLESS to simulate in tests.
    
    Note: On first run, this will prompt for phone number and authentication code.
    """
    try:
        headless = os.environ.get('JARVIS_HEADLESS', '').lower() in ('1', 'true', 'yes')
        if headless:
            print(f"[headless] send_telegram to={contact} msg={message}")
            return True

        api_id = os.environ.get('TELEGRAM_API_ID')
        api_hash = os.environ.get('TELEGRAM_API_HASH')
        session = os.environ.get('TELEGRAM_SESSION', 'jarvis_telegram')
        if not api_id or not api_hash:
            print('Telethon credentials not set (TELEGRAM_API_ID/TELEGRAM_API_HASH)')
            return False

        try:
            # Import telethon dynamically to avoid static import-time resolution errors in editors/linters
            import importlib
            telethon_mod = importlib.import_module('telethon')
            TelegramClient = getattr(telethon_mod, 'TelegramClient', None)
            # errors submodule may sometimes need explicit import
            try:
                errors_mod = importlib.import_module('telethon.errors')
            except Exception:
                errors_mod = getattr(telethon_mod, 'errors', None)
            SessionPasswordNeededError = getattr(errors_mod, 'SessionPasswordNeededError', None)
            if TelegramClient is None or SessionPasswordNeededError is None:
                raise ImportError('telethon not installed or missing required symbols')
        except Exception as e:
            print(f'Telethon not installed: {e}')
            return False

        client = TelegramClient(session, int(api_id), api_hash)
        try:
            client.connect()
            
            # If not authorized, start authentication
            if not client.is_user_authorized():
                print('Telegram session not authorized. Starting authentication...')
                print('You will be prompted for your phone number and authentication code.')
                client.start()
            
            # Send the message
            client.send_message(contact, message)
            print(f'Successfully sent Telegram message to {contact}')
            return True
        except SessionPasswordNeededError:
            print('Two-step verification is enabled. Password required.')
            print('This feature needs manual password input - please authenticate manually first.')
            return False
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False
        finally:
            client.disconnect()
    except Exception as e:
        print(f"send_telegram error: {e}")
        return False


def send_instagram(username, message):
    """Send Instagram DM using instagrapi. Reads IG_USERNAME and IG_PASSWORD from env.
    Returns True on success. Respects JARVIS_HEADLESS to simulate in tests.
    """
    try:
        headless = os.environ.get('JARVIS_HEADLESS', '').lower() in ('1', 'true', 'yes')
        if headless:
            print(f"[headless] send_instagram to={username} msg={message}")
            return True

        ig_user = os.environ.get('IG_USERNAME')
        ig_pass = os.environ.get('IG_PASSWORD')
        if not ig_user or not ig_pass:
            print('Instagram credentials not set (IG_USERNAME/IG_PASSWORD)')
            return False

        try:
            from instagrapi import Client
        except Exception as e:
            print(f'instagrapi not installed: {e}')
            return False

        cl = Client()
        cl.login(ig_user, ig_pass)
        # resolve user id
        try:
            uid = cl.user_id_from_username(username)
        except Exception:
            # maybe username provided is already numeric id
            try:
                uid = int(username)
            except Exception:
                print(f'Could not resolve Instagram user: {username}')
                return False

        cl.direct_send(message, [uid])
        return True
    except Exception as e:
        print(f"send_instagram error: {e}")
        return False


def telegram_desktop_send(contact_name, message, wait_open=1.0):
    """Automate Telegram Desktop to search a contact and send a message.
    Uses Ctrl+K to open contact search, types the contact name, presses Enter, types the message, and presses Enter.
    Returns True on success. Respects JARVIS_HEADLESS to avoid real keystrokes in tests.
    """
    try:
        headless = os.environ.get('JARVIS_HEADLESS', '').lower() in ('1', 'true', 'yes')
        if headless:
            print(f"[headless] telegram_desktop_send to={contact_name} msg={message}")
            return True

        # Try to open Telegram app (this uses existing openCommand logic)
        try:
            openCommand('telegram')
        except Exception:
            pass

        # Allow more time for Telegram to open and become responsive
        time.sleep(max(2.0, wait_open))

        # Try to focus the Telegram window using PyGetWindow (faster/more reliable than sending Win keys)
        try:
            import pygetwindow as gw
            wins = gw.getWindowsWithTitle('Telegram')
            if not wins:
                # try partial match
                allwins = gw.getAllTitles()
                candidate = None
                for t in allwins:
                    if t and 'telegram' in t.lower():
                        candidate = t
                        break
                if candidate:
                    wins = gw.getWindowsWithTitle(candidate)
            # If we found a window, try to activate it. Then wait a short while
            # and poll until the Telegram window appears active (or timeout).
            activated = False
            if wins:
                w = wins[0]
                try:
                    w.restore()
                except Exception:
                    pass
                try:
                    w.activate()
                except Exception:
                    try:
                        w.minimize(); w.maximize()
                    except Exception:
                        pass

            # Wait/poll loop to ensure the Telegram window is responsive before sending keystrokes
            try:
                max_wait = 6.0  # seconds
                interval = 0.25
                waited = 0.0
                while waited < max_wait:
                    wins = gw.getWindowsWithTitle('Telegram')
                    if not wins:
                        # try partial match titles
                        allwins = gw.getAllTitles()
                        candidate = None
                        for t in allwins:
                            if t and 'telegram' in t.lower():
                                candidate = t
                                break
                        if candidate:
                            wins = gw.getWindowsWithTitle(candidate)

                    if wins:
                        w = wins[0]
                        try:
                            # Attempt to activate again if not active
                            try:
                                if hasattr(w, 'isActive'):
                                    is_active = getattr(w, 'isActive')
                                else:
                                    # Fallback: assume window is active after activate call
                                    is_active = True
                            except Exception:
                                is_active = True
                            if not is_active:
                                try:
                                    w.activate()
                                except Exception:
                                    try:
                                        w.minimize(); w.maximize()
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        # Small sleep to allow GUI to settle, then assume active
                        time.sleep(0.15)
                        activated = True
                        break

                    time.sleep(interval)
                    waited += interval

                if not activated:
                    print("telegram_desktop_send: Telegram window didn't become active after waiting")
                else:
                    # give a tiny extra pause for stability
                    time.sleep(0.15)
            except Exception as e:
                print(f"telegram_desktop_send: window-wait check failed: {e}")
        except Exception as e:
            print(f"Could not activate Telegram window via PyGetWindow: {e}")

        # Try search shortcuts (prefer Ctrl+K, fallback to Ctrl+F)
        try:
            pyautogui.hotkey('ctrl', 'k')
            time.sleep(0.25)
        except Exception:
            try:
                pyautogui.hotkey('ctrl', 'f')
                time.sleep(0.25)
            except Exception:
                pass

        # Type the contact name
        # Sanitize contact_name before typing to avoid sending full command text into search box
        try:
            def _sanitize_contact_name(n):
                if not n:
                    return ''
                s = str(n).strip()
                # remove common action/platform words
                s = re.sub(r"\b(open|search|find|for|the|named|name|to|send|message|telegram|whatsapp|instagram|insta|and|then)\b", '', s, flags=re.IGNORECASE)
                # collapse whitespace
                s = re.sub(r"\s+", ' ', s).strip()
                # extract only word-like tokens (avoid punctuation/commands)
                tokens = re.findall(r"[A-Za-z0-9_\-']+", s)
                if not tokens:
                    return ''
                # limit to first 3 tokens (typical name length)
                tokens = tokens[:3]
                return ' '.join(tokens)

            sanitized_name = _sanitize_contact_name(contact_name)
            if not sanitized_name:
                # fallback: use the original but warn
                print(f"telegram_desktop_send: sanitized contact name empty from raw='{contact_name}' - using raw")
                sanitized_name = str(contact_name)
        except Exception as e:
            print(f"telegram_desktop_send: contact name sanitization failed: {e}")
            sanitized_name = str(contact_name)

        print(f"telegram_desktop_send: typing contact_name='{sanitized_name}' (raw='{contact_name}')")
        pyautogui.write(sanitized_name, interval=0.04)
        time.sleep(0.6)
        # Sometimes the first match needs an extra down arrow to select
        pyautogui.press('down')
        time.sleep(0.15)
        pyautogui.press('enter')
        time.sleep(0.6)

        # Type the message and send only if a non-empty message was provided
        if message and str(message).strip():
            pyautogui.write(str(message), interval=0.02)
            time.sleep(0.12)
            pyautogui.press('enter')

        return True
    except Exception as e:
        print(f"telegram_desktop_send error: {e}")
        return False


def whatsapp_desktop_send(contact_name, message, wait_open=1.0):
    """Automate WhatsApp Desktop to search a contact and send a message.
    Uses the app's search box (Ctrl+F) and types the contact name, selects the chat, types the message, and sends.
    Returns True on success. Respects JARVIS_HEADLESS to avoid real keystrokes in tests.
    """
    try:
        headless = os.environ.get('JARVIS_HEADLESS', '').lower() in ('1', 'true', 'yes')
        if headless:
            print(f"[headless] whatsapp_desktop_send to={contact_name} msg={message}")
            return True

        # Try to open WhatsApp app
        try:
            openCommand('whatsapp')
        except Exception:
            pass

        time.sleep(max(2.0, wait_open))

        # Focus the WhatsApp window if possible
        try:
            import pygetwindow as gw
            wins = gw.getWindowsWithTitle('WhatsApp')
            if wins:
                w = wins[0]
                try:
                    w.restore()
                except Exception:
                    pass
                try:
                    w.activate()
                except Exception:
                    try:
                        w.minimize(); w.maximize()
                    except Exception:
                        pass
                time.sleep(0.4)
        except Exception as e:
            print(f"Could not activate WhatsApp window via PyGetWindow: {e}")

        # Try opening search and typing contact name
        try:
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.2)
        except Exception:
            pass

        pyautogui.write(str(contact_name), interval=0.04)
        time.sleep(0.6)
        pyautogui.press('enter')
        time.sleep(0.6)

        # Type message and send only if a non-empty message was provided
        if message and str(message).strip():
            pyautogui.write(str(message), interval=0.02)
            time.sleep(0.12)
            pyautogui.press('enter')
        return True
    except Exception as e:
        print(f"whatsapp_desktop_send error: {e}")
        return False


# skipCurrentPrompt removed: skip option disabled

# Settings Modal 



# Assistant name
@eel.expose
def assistantName():
    name = ASSISTANT_NAME
    return name


@eel.expose
def personalInfo():
    try:
        cursor.execute("SELECT * FROM info")
        results = cursor.fetchall()
        jsonArr = json.dumps(results[0])
        eel.getData(jsonArr)
        return 1    
    except:
        print("no data")


@eel.expose
def updatePersonalInfo(name, designation, mobileno, email, city):
    cursor.execute("SELECT COUNT(*) FROM info")
    count = cursor.fetchone()[0]

    if count > 0:
        # Update existing record
        cursor.execute(
            '''UPDATE info 
               SET name=?, designation=?, mobileno=?, email=?, city=?''',
            (name, designation, mobileno, email, city)
        )
    else:
        # Insert new record if no data exists
        cursor.execute(
            '''INSERT INTO info (name, designation, mobileno, email, city) 
               VALUES (?, ?, ?, ?, ?)''',
            (name, designation, mobileno, email, city)
        )

    con.commit()
    personalInfo()
    return 1



@eel.expose
def displaySysCommand():
    cursor.execute("SELECT * FROM sys_command")
    results = cursor.fetchall()
    jsonArr = json.dumps(results)
    eel.displaySysCommand(jsonArr)
    return 1


@eel.expose
def deleteSysCommand(id):
    cursor.execute("DELETE FROM sys_command WHERE id = ?", (id,))
    con.commit()


@eel.expose
def addSysCommand(key, value):
    cursor.execute(
        '''INSERT INTO sys_command VALUES (?, ?, ?)''', (None,key, value))
    con.commit()


@eel.expose
def displayWebCommand():
    cursor.execute("SELECT * FROM web_command")
    results = cursor.fetchall()
    jsonArr = json.dumps(results)
    eel.displayWebCommand(jsonArr)
    return 1


@eel.expose
def addWebCommand(key, value):
    cursor.execute(
        '''INSERT INTO web_command VALUES (?, ?, ?)''', (None, key, value))
    con.commit()


@eel.expose
def deleteWebCommand(id):
    cursor.execute("DELETE FROM web_command WHERE Id = ?", (id,))
    con.commit()


@eel.expose
def displayPhoneBookCommand():
    cursor.execute("SELECT * FROM contacts")
    results = cursor.fetchall()
    jsonArr = json.dumps(results)
    eel.displayPhoneBookCommand(jsonArr)
    return 1


@eel.expose
def deletePhoneBookCommand(id):
    cursor.execute("DELETE FROM contacts WHERE Id = ?", (id,))
    con.commit()


@eel.expose
def InsertContacts(Name, MobileNo, Email, City):
    cursor.execute(
        '''INSERT INTO contacts VALUES (?, ?, ?, ?, ?)''', (None,Name, MobileNo, Email, City))
    con.commit()
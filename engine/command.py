import pyttsx3
import re
import speech_recognition as sr
import eel
import time
import threading
import os
import json
import tempfile

# Optional faster-whisper import (used for multilingual offline transcription)
_whisper_available = False
try:
    from faster_whisper import WhisperModel
    _whisper_available = True
except Exception:
    _whisper_available = False

from engine import config as config_module

# whisper model cache
whisper_model = None

# runtime speech language (default read from config)
try:
    current_speech_lang = getattr(config_module, 'DEFAULT_SPEECH_LANG', 'en-IN')
except Exception:
    current_speech_lang = 'en-IN'


@eel.expose
def set_speech_language(lang_code):
    """Set the runtime speech recognition language (e.g., 'en-US', 'hi-IN', 'auto')."""
    global current_speech_lang
    try:
        current_speech_lang = lang_code
        print(f"Speech language set to: {lang_code}")
        try:
            _log_voice_metric('set_language', {'lang': current_speech_lang})
        except Exception:
            pass
        try:
            eel.DisplayMessage(f'Set language to {current_speech_lang}')
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"Failed to set speech language: {e}")
        return False


@eel.expose
def get_speech_language():
    try:
        return current_speech_lang
    except Exception:
        return getattr(config_module, 'DEFAULT_SPEECH_LANG', 'en-IN')
# Global speech lock to prevent threading issues
_speech_lock = threading.Lock()

# Lazy-init TTS engine to avoid initialization side-effects during import
_tts_engine = None
_preferred_voice_id = None

def _get_tts_engine():
    """Lazily initialize and configure the pyttsx3 engine on first use."""
    global _tts_engine, _preferred_voice_id
    if _tts_engine is not None:
        return _tts_engine
    try:
        eng = pyttsx3.init('sapi5')
        # Pick a softer voice if available (prefer female or 'Zira' on Windows)
        try:
            voices = eng.getProperty('voices')
            for v in voices:
                name = getattr(v, 'name', '').lower()
                if 'zira' in name or 'female' in name or 'susan' in name:
                    _preferred_voice_id = v.id
                    break
            if not _preferred_voice_id and len(voices) > 0:
                _preferred_voice_id = voices[0].id
            if _preferred_voice_id:
                eng.setProperty('voice', _preferred_voice_id)
        except Exception:
            pass

        # Set gentler defaults
        try:
            eng.setProperty('rate', 150)
            eng.setProperty('volume', 0.85)
        except Exception:
            pass

        _tts_engine = eng
        return _tts_engine
    except Exception:
        _tts_engine = None
        return None


def _speak_chunks(engine, text):
    """Split text into sentence-like chunks and speak with small pauses to sound smoother."""
    # Very simple splitter: split on ., ?, ! and commas to create natural pauses
    import time as _time
    chunks = []
    # Prefer splitting on punctuation while preserving meaningful short clauses
    for part in re.split(r'(?<=[\.!?])\s+|,\s+', text):
        p = part.strip()
        if p:
            chunks.append(p)

    # Fallback if nothing was split
    if not chunks:
        chunks = [text]

    for i, c in enumerate(chunks):
        # Slightly reduce intensity for shorter chunks by adding a leading pause
        try:
            # Engine may be None in headless/envs; try to get or fallback to print
            eng = engine or _get_tts_engine()
            if eng is not None:
                eng.say(c)
                eng.runAndWait()
            else:
                raise RuntimeError('TTS engine unavailable')
        except Exception:
            # If runAndWait fails (rare), fallback to print
            print(f"Jarvis: {c}")
        # Small pause between chunks to sound calm and measured
        if i < len(chunks) - 1:
            _time.sleep(0.25)


def speak(text):
    """Thread-safe speech function with softer delivery"""
    text = str(text)
    try:
        # Update UI first (only if eel is available)
        try:
            eel.DisplayMessage(text)
            eel.receiverText(text)
        except:
            pass  # Skip UI updates if eel is not available

        with _speech_lock:
            # Use the persistent engine
            _speak_chunks(_tts_engine, text)

    except Exception as e:
        print(f"Error in speak function: {e}")
        # Fallback to print if speech fails
        print(f"Jarvis: {text}")


def takecommand():

    r = sr.Recognizer()
    # Use module-level cancel event to allow UI-driven cancellation
    global _cancel_listen_event
    try:
        _cancel_listen_event
    except NameError:
        _cancel_listen_event = threading.Event()

    # Play a short beep to indicate listening start (Windows winsound if available)
    try:
        if os.name == 'nt':
            import winsound
            winsound.Beep(800, 120)
    except Exception:
        pass

    with sr.Microphone() as source:
        print('listening....')
        try:
            eel.DisplayMessage('listening....')
        except:
            pass
        r.pause_threshold = 1
        r.adjust_for_ambient_noise(source)
    # Use background listening so we can honor cancel requests
        audio = None
        audio_container = []

        def _callback(recognizer, audio):
            audio_container.append(audio)

        stop_listening = None
        try:
            stop_listening = r.listen_in_background(source, _callback)
            # wait for audio or timeout or cancel
            start_t = time.time()
            while True:
                if _cancel_listen_event.is_set():
                    # cancel requested
                    try:
                        stop_listening(wait_for_stop=False)
                    except Exception:
                        pass
                    _cancel_listen_event.clear()
                    try:
                        eel.DisplayMessage('Listening cancelled')
                    except:
                        pass
                    return ""
                if audio_container:
                    audio = audio_container.pop(0)
                    try:
                        stop_listening(wait_for_stop=False)
                    except Exception:
                        pass
                    break
                if time.time() - start_t > 10:
                    # timeout waiting for phrase
                    try:
                        stop_listening(wait_for_stop=False)
                    except Exception:
                        pass
                    print('Listening timed out while waiting for phrase to start')
                    try:
                        eel.DisplayMessage('Listening timed out')
                    except:
                        pass
                    return ""
                time.sleep(0.1)
        except Exception as e:
            print(f"Error while listening (background): {e}")
            try:
                if stop_listening:
                    stop_listening(wait_for_stop=False)
            except Exception:
                pass
            try:
                eel.DisplayMessage('Microphone error')
            except:
                pass
            return ""

    try:
        print('recognizing')
        try:
            eel.DisplayMessage('recognizing....')
        except:
            pass

        # Prefer local whisper model if available (multilingual, auto-detect)
        recognized_text = ""
        try:
            wav_bytes = audio.get_wav_data()
        except Exception:
            wav_bytes = None

        # Determine runtime language preference (default from config)
        try:
            runtime_lang = current_speech_lang
        except Exception:
            runtime_lang = getattr(config_module, 'DEFAULT_SPEECH_LANG', 'en-IN')

        if _whisper_available and wav_bytes:
            # Lazily load model
            try:
                global whisper_model
                if 'whisper_model' not in globals() or whisper_model is None:
                    # load a small model by default (device: cpu)
                    whisper_model = WhisperModel('small', device='cpu')
                # write wav to temp file
                tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                try:
                    tmp.write(wav_bytes)
                    tmp.flush()
                    tmp_name = tmp.name
                finally:
                    tmp.close()

                # Use 'auto' if runtime_lang is 'auto' or empty
                wh_lang = 'auto' if not runtime_lang or str(runtime_lang).lower() in ('auto', 'detect') else runtime_lang
                segments, info = whisper_model.transcribe(tmp_name, beam_size=5, language=wh_lang)
                parts = [s.text for s in segments]
                recognized_text = ' '.join(parts).strip()
                try:
                    os.unlink(tmp_name)
                except Exception:
                    pass
            except Exception as e:
                print(f"Whisper transcription failed: {e}")
                recognized_text = ""

        # Fallback to Google recognizer if whisper not available or failed
        if not recognized_text:
            try:
                # use runtime_lang or config default
                use_lang = runtime_lang or getattr(config_module, 'DEFAULT_SPEECH_LANG', 'en-IN')
                query = r.recognize_google(audio, language=use_lang)
                recognized_text = query
            except Exception as e:
                print(f"Google recognizer failed or no speech: {e}")
                recognized_text = ""

        print(f'user said: {recognized_text}')
        try:
            eel.DisplayMessage(recognized_text)
        except:
            pass
        time.sleep(2)

    except Exception as e:
        print(f"Error recognizing audio: {e}")
        return ""

    return recognized_text.lower()


# (runtime setter is defined earlier as set_speech_language)


def takecommand_with_retries(max_retries=2):
    """Call takecommand(), retrying when empty (no speech) up to max_retries times.
    Returns the first non-empty recognized string or empty string if all attempts fail.
    """
    attempts = 0
    while attempts <= max_retries:
        if attempts > 0:
            # Ask user to repeat
            try:
                speak("I didn't catch that. Please say that again.")
                eel.DisplayMessage('Please say that again...')
            except Exception:
                pass

        result = takecommand()
        if result and result.strip():
            return result
        attempts += 1

    # After retries, inform the user
    try:
        speak("I couldn't hear anything. Please try using the text input.")
        eel.DisplayMessage("No voice detected after several attempts")
    except Exception:
        pass
    return ""


def _log_voice_metric(event_name, data=None):
    try:
        metrics_file = os.path.join(os.path.dirname(__file__), '..', 'voice_metrics.jsonl')
        entry = {'ts': time.time(), 'event': event_name, 'data': data or {}}
        with open(metrics_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        pass


@eel.expose
def cancel_listen():
    """Called from UI to cancel an in-progress listening session."""
    global _cancel_listen_event
    try:
        _cancel_listen_event
    except NameError:
        _cancel_listen_event = threading.Event()
    _cancel_listen_event.set()
    _log_voice_metric('cancel_requested')
    return True

@eel.expose
def allCommands(message=1):
    from engine.enhanced_parser import enhanced_parser
    from engine.task_manager import task_manager

    if message == 1:
        try:
            # Use retrying voice capture to improve reliability when no speech is heard
            query = takecommand_with_retries(max_retries=2)
        except Exception as e:
            print(f"Error during takecommand: {e}")
            query = ""
        print(query)
        try:
            eel.senderText(query)
        except Exception:
            print("Warning: eel.senderText failed (UI may not be connected)")
    else:
        query = message
        try:
            eel.senderText(query)
        except Exception:
            print("Warning: eel.senderText failed (UI may not be connected)")
    
    try:
        # Extract commands first (more robust than the simple heuristic)
        try:
            commands = enhanced_parser.extract_commands(query)
        except Exception:
            commands = [query]

        # Merge context-only fragments produced by the parser.
        # Example: parser may split "open telegram search vachi" and "send hola" into two parts.
        # If a part mentions a platform (telegram/whatsapp/instagram) and the next part is
        # a message-only fragment (contains 'send'/'say' etc but no platform), attach the
        # next part to the current one to preserve platform+message context.
        try:
            merged_parts = []
            i = 0
            n = len(commands)
            while i < n:
                cur = commands[i]
                cur_query = (cur.get('query') if isinstance(cur, dict) else str(cur))
                j = i + 1
                # accumulate following message-like fragments
                while j < n:
                    nxt = commands[j]
                    nxt_query = (nxt.get('query') if isinstance(nxt, dict) else str(nxt))
                    low_nxt = (nxt_query or '').lower()
                    low_cur = (cur_query or '').lower()
                    # Decide if nxt is a context/message fragment to merge
                    if re.search(r"\b(send|say|saying|says|message|dm|to|tell)\b", low_nxt) and not re.search(r"\b(telegram|whatsapp|instagram|insta)\b", low_nxt):
                        # Only merge when current mentions a platform or is an open/search command
                        if re.search(r"\b(telegram|whatsapp|instagram|insta)\b", low_cur) or re.search(r"\b(search|find|open)\b", low_cur):
                            # create a merged dict/object preserving type and original
                            if isinstance(cur, dict):
                                merged_query = (cur.get('original') or cur.get('query') or '') + ' and ' + (nxt.get('original') or nxt.get('query') or '')
                                cur = {
                                    'type': cur.get('type', 'general'),
                                    'query': merged_query,
                                    'parameters': tuple(cur.get('parameters', ())) + tuple(nxt.get('parameters', ())),
                                    'original': merged_query
                                }
                            else:
                                merged_query = str(cur) + ' and ' + str(nxt)
                                cur = merged_query
                            # advance j to consider further fragments
                            j += 1
                            continue
                    break

                merged_parts.append(cur)
                i = j

            commands = merged_parts
        except Exception as _e:
            print(f"allCommands: merging parser fragments failed: {_e}")

        # Consider it multitask if either the heuristic says so or parser returned multiple parts
        is_multi_flag = False
        try:
            is_multi_flag = enhanced_parser.is_multitask_request(query) or (isinstance(commands, list) and len(commands) > 1)
        except Exception:
            is_multi_flag = isinstance(commands, list) and len(commands) > 1

        if is_multi_flag:
            speak("I detected multiple tasks. Let me execute them for you.")

            # Get execution suggestions
            execution_plan = enhanced_parser.suggest_parallel_execution(commands)

            # Execute parallel commands first (pass structured commands so types like 'open_and_type' are preserved)
            if execution_plan.get('parallel'):
                parallel_cmds = execution_plan['parallel']
                threading.Thread(target=task_manager.execute_multiple_commands, args=(parallel_cmds,)).start()

            # Execute sequential commands
            if execution_plan.get('sequential'):
                for cmd in execution_plan['sequential']:
                    # pass the original string for single-execution path
                    threading.Thread(target=execute_single_command, args=(cmd.get('original', cmd.get('query')),)).start()
                    time.sleep(1)  # Small delay between sequential commands
        else:
            # Single command execution
            execute_single_command(query)
            
    except Exception as e:
        print(f"Error in command processing: {e}")
        speak("Sorry, there was an error processing your request")
    
    # Ensure UI resets even if errors occurred
    try:
        eel.ShowHood()
    except Exception:
        print("Warning: eel.ShowHood failed (UI may not be connected)")
    try:
        eel.hideMicStatus()
    except Exception:
        pass

def execute_single_command(query):
    """Execute a single command (extracted for reusability)"""
    import threading
    import time
    
    try:
        # Normalize query with trained corrections so user-taught synonyms apply globally
        try:
            from engine.enhanced_parser import enhanced_parser
            try:
                normalized = enhanced_parser.normalize_query(query)
                if normalized and normalized != query:
                    print(f"Normalized query: '{query}' -> '{normalized}'")
                    query = normalized
            except Exception:
                pass
        except Exception:
            pass
        # Check for complex commands first
        from engine.features import execute_complex_command
        if execute_complex_command(query):
            return  # Complex command handled
        
        if "open" in query:
            from engine.features import openCommand
            openCommand(query)
        elif "on youtube" in query:
            from engine.features import PlayYoutube
            PlayYoutube(query)
        
        elif "send message" in query or "phone call" in query or "video call" in query:
            from engine.features import findContact, whatsApp, makeCall, sendMessage
            contact_no, name = findContact(query)
            if(contact_no != 0):
                speak("Which mode you want to use whatsapp or mobile")
                preferance = takecommand()
                print(preferance)

                if "mobile" in preferance:
                    if "send message" in query or "send sms" in query: 
                        speak("what message to send")
                        message = takecommand()
                        sendMessage(message, contact_no, name)
                    elif "phone call" in query:
                        makeCall(name, contact_no)
                    else:
                        speak("please try again")
                elif "whatsapp" in preferance:
                    message = ""
                    if "send message" in query:
                        message = 'message'
                        speak("what message to send")
                        query = takecommand()
                                        
                    elif "phone call" in query:
                        message = 'call'
                    else:
                        message = 'video call'
                                        
                    whatsApp(contact_no, query, message, name)

        else:
            from engine.features import geminai
            geminai(query)
    except Exception as e:
        print(f"Error executing single command: {e}")
        speak("Sorry, I couldn't execute that command")
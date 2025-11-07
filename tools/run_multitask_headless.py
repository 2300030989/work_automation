# Headless runner: provides a minimal dummy `eel` module so engine.command can be imported
import sys
import types
import time

# Create a minimal eel stub to avoid importing the real eel package during tests
eel_stub = types.SimpleNamespace()

# functions used by engine.command and other modules
def noop(*args, **kwargs):
    print(f"[eel_stub] called noop with args={args} kwargs={kwargs}")

def display_message(msg):
    print(f"[eel_stub] DisplayMessage: {msg}")

def sender_text(msg):
    print(f"[eel_stub] senderText: {msg}")

def receiver_text(msg):
    print(f"[eel_stub] receiverText: {msg}")

def show_hood():
    print("[eel_stub] ShowHood called")

def hide_mic_status():
    print("[eel_stub] hideMicStatus called")

# expose decorator (no-op)
def expose(fn=None, *a, **k):
    if fn is None:
        return lambda f: f
    return fn

# attach to stub
eel_stub.DisplayMessage = display_message
eel_stub.senderText = sender_text
eel_stub.receiverText = receiver_text
eel_stub.ShowHood = show_hood
eel_stub.hideMicStatus = hide_mic_status
eel_stub.expose = expose

# insert into sys.modules so 'import eel' returns our stub
sys.modules['eel'] = eel_stub

# Now import command module and run the test
from engine.command import allCommands

TEST_QUERY = "open notepad, open notepad and type bahubali and open youtube, open youtube play dosti song"
print('HEADLESS RUNNER: calling allCommands with test query')
res = allCommands(TEST_QUERY)
print('allCommands returned:', res)

# Sleep to allow background threads to run and print logs
print('Waiting 6 seconds for background tasks/logs...')
for i in range(6):
    time.sleep(1)
    print('.', end='', flush=True)
print('\nHeadless run finished')

# --- Add a lightweight stub for engine.features so task_manager won't import heavy libs ---
import types as _types
features_stub = _types.ModuleType('engine.features')

def _openCommand(cmd):
    print(f"[features_stub] openCommand called with: {cmd}")
    return True

def _PlayYoutube(cmd):
    print(f"[features_stub] PlayYoutube called with: {cmd}")
    return True

def _findContact(cmd):
    print(f"[features_stub] findContact called with: {cmd}")
    return (0, '')

def _whatsApp(*a, **k):
    print(f"[features_stub] whatsApp called: args={a} kwargs={k}")

def _makeCall(*a, **k):
    print(f"[features_stub] makeCall called: args={a} kwargs={k}")

def _sendMessage(*a, **k):
    print(f"[features_stub] sendMessage called: args={a} kwargs={k}")

def _geminai(q):
    print(f"[features_stub] geminai (AI) called with: {q}")

def _chatBot(q):
    print(f"[features_stub] chatBot called with: {q}")

def _openNotepadAndType(text):
    print(f"[features_stub] openNotepadAndType called with text: {text}")
    return True

features_stub.openCommand = _openCommand
features_stub.PlayYoutube = _PlayYoutube
features_stub.findContact = _findContact
features_stub.whatsApp = _whatsApp
features_stub.makeCall = _makeCall
features_stub.sendMessage = _sendMessage
features_stub.geminai = _geminai
features_stub.chatBot = _chatBot
features_stub.openNotepadAndType = _openNotepadAndType

import sys as _sys
_sys.modules['engine.features'] = features_stub

# Re-import allCommands now that features is stubbed; call again to exercise paths
try:
    from importlib import reload
    import engine.command as _cmdmod
    reload(_cmdmod)
    print('\nCalling allCommands again with stubbed features...')
    _cmdmod.allCommands(TEST_QUERY)
except Exception as e:
    print('Error reloading/calling allCommands with stubs:', e)

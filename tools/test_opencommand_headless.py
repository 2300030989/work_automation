# Headless test for openCommand with typing intent
import sys, types, time

# Simple eel stub
eel = types.SimpleNamespace()
def noop(*a, **k): print('[eel] noop', a, k)
eel.DisplayMessage = lambda m: print('[eel] DisplayMessage:', m)
eel.senderText = lambda m: print('[eel] senderText:', m)
eel.receiverText = lambda m: print('[eel] receiverText:', m)
eel.ShowHood = lambda : print('[eel] ShowHood')
eel.hideMicStatus = lambda : print('[eel] hideMicStatus')
eel.expose = lambda f=None: (f if f is None else f)

sys.modules['eel'] = eel

# Stub pyautogui and pyperclip and engine.auto_typer to avoid real typing
import types as _types
pyautogui_stub = _types.ModuleType('pyautogui')
def _click(*a, **k): print('[pyautogui] click', a, k)
def _hotkey(*a, **k): print('[pyautogui] hotkey', a, k)
def _press(*a, **k): print('[pyautogui] press', a, k)
def _typewrite(*a, **k): print('[pyautogui] typewrite', a, k)
def _size(): return (800, 600)
pyautogui_stub.click = _click
pyautogui_stub.hotkey = _hotkey
pyautogui_stub.press = _press
pyautogui_stub.typewrite = _typewrite
pyautogui_stub.size = _size

sys.modules['pyautogui'] = pyautogui_stub

pyperclip_stub = _types.SimpleNamespace()
pyperclip_stub.copy = lambda t: print('[pyperclip] copy:', t)
sys.modules['pyperclip'] = pyperclip_stub

# Stub engine.auto_typer.type_in_application
import importlib
mod = _types.ModuleType('engine.auto_typer')
def type_in_application(text, delay=0.03):
    print(f"[auto_typer_stub] would type: {text} (delay={delay})")
    return True
mod.type_in_application = type_in_application
sys.modules['engine.auto_typer'] = mod

# Now import openCommand and run test
from engine.features import openCommand

print('TEST: openCommand("open notepad and type bahubali")')
res = openCommand('open notepad and type bahubali')
print('Result:', res)

print('TEST: openCommand("open notepad, open notepad and type bahubali and open youtube, open youtube play dosti song")')
res2 = openCommand('open notepad, open notepad and type bahubali and open youtube, open youtube play dosti song')
print('Result2:', res2)

# Wait a moment for any background prints
time.sleep(1)
print('HEADLESS TEST COMPLETE')

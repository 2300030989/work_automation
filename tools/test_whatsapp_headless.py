# Headless test for WhatsApp automation in execute_complex_command
import sys, types

# Minimal eel stub
eel = types.SimpleNamespace()
eel.DisplayMessage = lambda m: print('[eel] DisplayMessage:', m)
eel.senderText = lambda m: print('[eel] senderText:', m)
eel.receiverText = lambda m: print('[eel] receiverText:', m)
eel.ShowHood = lambda : print('[eel] ShowHood')
eel.hideMicStatus = lambda : print('[eel] hideMicStatus')
eel.expose = lambda f=None: (f if f is None else f)
sys.modules['eel'] = eel

# Stub whatsApp and findContact by inserting a fake engine.features module or monkeypatching
from types import ModuleType
features_stub = ModuleType('engine.features')

def fake_whatsApp(mobile_no, message, flag, name):
    print(f"[stub whatsApp] to={mobile_no}, name={name}, message={message}, flag={flag}")

def fake_findContact(q):
    # pretend any name 'praveen' resolves to a fake number
    if 'praveen' in q.lower():
        return ('+911234567890', 'Praveen')
    return (0, 0)

features_stub.whatsApp = fake_whatsApp
features_stub.findContact = fake_findContact

import sys as _sys
_sys.modules['engine.features'] = features_stub

# Now import execute_complex_command and run tests
from engine.features import execute_complex_command

cases = [
    "open whatsapp search praveen and send hi",
    "send whatsapp message to praveen hi",
    "whatsapp praveen send hello there",
]

for c in cases:
    print('\nCASE:', c)
    r = execute_complex_command(c)
    print('Result:', r)

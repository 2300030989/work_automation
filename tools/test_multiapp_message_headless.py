# Headless test for multi-platform messaging (whatsapp/telegram/instagram)
import sys, types

# stub eel
eel = types.SimpleNamespace()
eel.DisplayMessage = lambda m: print('[eel] DisplayMessage:', m)
eel.expose = lambda f=None: (f if f is None else f)
sys.modules['eel'] = eel

# Stub findContact and whatsApp in engine.features by creating a small module
import engine.features as features

# Monkeypatch findContact and whatsApp on the real module
def fake_findContact(q):
    if 'praveen' in q.lower():
        return ('+911234567890', 'Praveen')
    return (0, 0)

def fake_whatsApp(mobile_no, message, flag, name):
    print(f"[stub whatsApp] to={mobile_no}, name={name}, message={message}, flag={flag}")

features.findContact = fake_findContact
features.whatsApp = fake_whatsApp

# Now call the real execute_complex_command from engine.features
cases = [
    'open whatsapp search praveen and send hi',
    'send whatsapp message to praveen hi',
    'open telegram search praveen and send hi',
    'send instagram message to praveen hello',
]

for c in cases:
    print('\nCASE:', c)
    try:
        r = features.execute_complex_command(c)
    except Exception as e:
        print('Exception during execute_complex_command:', e)
        r = False
    print('Result:', r)

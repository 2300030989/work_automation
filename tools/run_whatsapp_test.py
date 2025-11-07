# Simple runner for whatsapp parsing test
import sys
sys.path.insert(0, 'e:/jarvis-main/jarvis-main')
import engine.features as features

def fake_findContact(q):
    print('[test] findContact called with:', q)
    if 'praveen' in q.lower():
        return ('+911234567890', 'Praveen')
    return (0, 0)

def fake_whatsApp(mobile_no, message, flag, name):
    print(f'[test stub whatsApp] to={mobile_no}, name={name}, message={message}, flag={flag}')

features.findContact = fake_findContact
features.whatsApp = fake_whatsApp

q = 'open whatsapp search name praveen and send hi'
print('\nCalling execute_complex_command with:', q)
r = features.execute_complex_command(q)
print('Result:', r)

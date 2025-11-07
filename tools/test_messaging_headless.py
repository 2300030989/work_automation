# Headless messaging parsing tests
import sys
sys.path.insert(0, 'e:/jarvis-main/jarvis-main')
import engine.features as features

# Stubs

def fake_findContact(q):
    print('[test] findContact called with:', q)
    ql = q.lower()
    if 'praveen' in ql:
        return ('+911234567890', 'Praveen')
    if 'alice' in ql:
        return ('+441234567890', 'Alice')
    return (0, 0)

called = []
def fake_whatsApp(mobile_no, message, flag, name):
    print(f'[test stub whatsApp] to={mobile_no}, name={name}, message={message}, flag={flag}')
    called.append((mobile_no, message, flag, name))

# Monkeypatch
features.findContact = fake_findContact
features.whatsApp = fake_whatsApp

cases = [
    "open whatsapp search name praveen and send hi",
    "send whatsapp message to praveen hi",
    "open whatsapp search praveen and send hello",
    "whatsapp praveen send hi",
    "send whatsapp to praveen saying hello",
    "open telegram search praveen and send hi",
    "send instagram message to alice hello",
]

results = {}
for q in cases:
    print('\nTest case:', q)
    try:
        r = features.execute_complex_command(q)
        results[q] = bool(r)
        print('Result:', r)
    except Exception as e:
        results[q] = False
        print('Exception:', e)

print('\nSummary:')
for k, v in results.items():
    print(k, '->', v)

# Quick assertion-style exit code
failed = [k for k,v in results.items() if not v]
if failed:
    print('\nFailed cases:', failed)
    sys.exit(2)
else:
    print('\nAll cases passed')
    sys.exit(0)

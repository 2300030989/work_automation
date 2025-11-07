# Diagnostic helper: list visible window titles and check for Telegram process
import sys
sys.path.insert(0, 'e:/jarvis-main/jarvis-main')
import time

print('Listing window titles using PyGetWindow (if available)')
try:
    import pygetwindow as gw
    titles = gw.getAllTitles()
    print('Window titles (count={}):'.format(len(titles)))
    for t in titles[:200]:
        if t:
            print(' -', t)
except Exception as e:
    print('pygetwindow not available or failed:', e)

print('\nChecking for Telegram process via psutil (if available)')
try:
    import psutil
    found = False
    for p in psutil.process_iter(['name', 'exe', 'cmdline']):
        try:
            name = (p.info.get('name') or '').lower()
            if 'telegram' in name:
                print('Found process:', p.info)
                found = True
        except Exception:
            pass
    if not found:
        print('No Telegram process found (by name)')
except Exception as e:
    print('psutil not available or failed:', e)

print('\nDiagnostic complete')

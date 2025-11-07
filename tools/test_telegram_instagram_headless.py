# Headless tests for telegram/instagram send helpers
import sys
sys.path.insert(0, 'e:/jarvis-main/jarvis-main')
import os
os.environ['JARVIS_HEADLESS'] = '1'
from engine.features import send_telegram, send_instagram

print('Testing headless telegram send')
print(send_telegram('praveen', 'hello from jarvis'))
print('Testing headless instagram send')
print(send_instagram('alice', 'hello from jarvis'))

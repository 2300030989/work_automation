# Headless test for send_telegram helper
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.features import send_telegram


def test_send_telegram_headless():
    # Ensure headless mode to avoid real network calls
    os.environ['JARVIS_HEADLESS'] = '1'
    # Call with a fake contact and message
    ok = send_telegram('@praveen', 'hello from jarvis')
    print('headless send_telegram returned:', ok)
    if not ok:
        raise SystemExit(2)


if __name__ == '__main__':
    test_send_telegram_headless()
    print('headless test passed')

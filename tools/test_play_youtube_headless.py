# Headless test for PlayYoutube
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.features import PlayYoutube


def test_play_yy():
    os.environ['JARVIS_HEADLESS'] = '1'
    ok = PlayYoutube('play naatu naatu song on youtube')
    print('PlayYoutube headless returned:', ok)
    if not ok:
        raise SystemExit(2)

if __name__ == '__main__':
    test_play_yy()
    print('headless PlayYoutube test passed')

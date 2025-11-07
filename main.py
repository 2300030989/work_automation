import os
try:
    import eel
except Exception:
    # Provide a lightweight eel stub so the application can run in environments
    # where the `eel` package is not installed. This prevents a hard crash
    # when starting from `run.py`. The real GUI experience requires the
    # `eel` package; prefer `pip install eel` for full functionality.
    class _EelStub:
        def init(self, *args, **kwargs):
            print("[eel stub] init called", args, kwargs)

        def expose(self, f=None):
            # decorator or direct call
            if f is None:
                def _dec(fn):
                    return fn
                return _dec
            return f

        def hideLoader(self):
            print('[eel stub] hideLoader')

        def hideFaceAuth(self):
            print('[eel stub] hideFaceAuth')

        def hideFaceAuthSuccess(self):
            print('[eel stub] hideFaceAuthSuccess')

        def hideStart(self):
            print('[eel stub] hideStart')

        def start(self, *args, **kwargs):
            # Non-GUI fallback: print a message and block so the process stays alive
            host = kwargs.get('host', 'localhost')
            port = kwargs.get('port', 8000)
            print(f"[eel stub] start called — web UI not available. Visit http://{host}:{port}/index.html if you installed eel.")
            try:
                # Simple blocking loop to mimic eel.start behaviour
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print('[eel stub] interrupted')

    eel = _EelStub()

from engine.features import *
from engine.command import *

def start():
    
    eel.init("www")

    playAssistantSound()
    
    @eel.expose
    def init():
        # Skip face authentication and ADB setup, go directly to main interface
        print("Initializing Jarvis without face authentication...")
        
        eel.hideLoader()
        eel.hideFaceAuth()
        eel.hideFaceAuthSuccess()
        speak("Hello, Welcome Sir, How can I Help You")
        eel.hideStart()
        playAssistantSound()
    
    # Pick a free port by trying to bind a socket (safer than starting eel repeatedly)
    import socket

    def _is_port_free(port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('localhost', port))
            s.close()
            return True
        except Exception:
            try:
                s.close()
            except:
                pass
            return False

    selected_port = None
    for port in range(8000, 8011):
        if _is_port_free(port):
            selected_port = port
            break

    if selected_port is None:
        selected_port = 8000

    # Try to open browser on the selected port
    try:
        os.system(f'start msedge.exe --app="http://localhost:{selected_port}/index.html"')
    except:
        print(f"Could not open browser automatically. Please navigate to http://localhost:{selected_port}/index.html")

    # Start eel on the selected port (blocking)
    try:
        eel.start('index.html', mode=None, host='localhost', port=selected_port, block=True)
    except Exception as e:
        print(f"Failed to start eel on port {selected_port}: {e}")
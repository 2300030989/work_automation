Developer notes


```bash
python tools/smoke_test.py
```


```bash
python -m pytest -q
```

### Windows Start search fallback (developer notes)

- A new fallback was added to `engine.openCommand()` that uses the Windows Start Menu search to open applications when other methods (DB mapping, PATH/exe, store protocol) don't find the app.
- The helper is `engine.features.windows_search_open(app_name)` and it uses `pyautogui` to press the Windows key, type the app name, and press Enter.

Testing and safety:

- Headless simulation: set the environment variable `JARVIS_HEADLESS=1` before running tests to prevent real keyboard events. Example (PowerShell):

```powershell
$env:PYTHONPATH='E:\jarvis-main\jarvis-main'
$env:JARVIS_HEADLESS='1'
python -c "from engine.features import openCommand; openCommand('open some-unique-app')"
```

- Live GUI mode: remove the `JARVIS_HEADLESS` variable (or set it to empty) and run `openCommand()` from an interactive desktop session. Be careful: `pyautogui` will send real keystrokes to the active window.

- Notes: pyautogui needs an interactive desktop, and timing/layout differences or non-English keyboard layouts may require tweaking the sleep intervals in `windows_search_open()`.

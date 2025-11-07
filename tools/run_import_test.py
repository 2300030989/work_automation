import importlib, traceback

try:
    importlib.invalidate_caches()
    m = importlib.import_module('engine.features')
    print('import ok')
except Exception:
    traceback.print_exc()
    raise

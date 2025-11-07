import os
import sys
# Ensure project root is on sys.path so `import engine` works when running from tools/
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
	sys.path.insert(0, proj_root)

from engine.features import execute_complex_command

print('Executing real UI action: open telegram search praveen and send hi')
res = execute_complex_command('open telegram search praveen and send hi')
print('Result:', res)

p = r'e:\\jarvis-main (3)\\jarvis-main\\jarvis-main\\engine\\features.py'
with open(p, 'rb') as f:
    lines = f.read().splitlines()
for i in range(940, 965):
    if i < len(lines):
        print(f"{i+1}: {lines[i]!r}")
    else:
        print(f"{i+1}: <no line>")

# Debug script: reproduce user's multitask utterance through parser and task manager
from engine import enhanced_parser
from engine import task_manager

QUERY = "open notepad, open notepad and type bahubali and open youtube, open youtube play dosti song"

print('\nQUERY:')
print(QUERY)

# is_multitask_request
try:
    is_multi = enhanced_parser.enhanced_parser.is_multitask_request(QUERY)
except Exception as e:
    is_multi = f'ERROR: {e}'
print('\nIS_MULTITASK_REQUEST:')
print(is_multi)

# extract_commands
try:
    extracted = enhanced_parser.enhanced_parser.extract_commands(QUERY)
except Exception as e:
    extracted = f'ERROR: {e}'
print('\nEXTRACTED COMMANDS:')
for i, c in enumerate(extracted, 1):
    if isinstance(c, dict):
        print(f'[{i}] type={c.get("type")}, query={c.get("query")}, parameters={c.get("parameters")}')
    else:
        print(f'[{i}] RAW: {repr(c)}')

# parse_multiple_commands (task_manager)
try:
    parsed = task_manager.task_manager.parse_multiple_commands(QUERY)
except Exception as e:
    parsed = f'ERROR: {e}'
print('\nTASK_MANAGER PARSED COMMANDS:')
if isinstance(parsed, list):
    for i, p in enumerate(parsed, 1):
        print(f'[{i}] {p}')
else:
    print(parsed)

# suggest_parallel_execution
try:
    suggestion = enhanced_parser.enhanced_parser.suggest_parallel_execution(extracted)
except Exception as e:
    suggestion = f'ERROR: {e}'
print('\nSUGGESTED PARALLEL/SEQUENTIAL EXECUTION:')
print(suggestion)

# get_priority_commands
try:
    prioritized = enhanced_parser.enhanced_parser.get_priority_commands(extracted)
except Exception as e:
    prioritized = f'ERROR: {e}'
print('\nPRIORITIZED COMMAND ORDER:')
for i, c in enumerate(prioritized, 1):
    print(f'[{i}] type={c.get("type")}, query={c.get("query")}')

print('\nDone')

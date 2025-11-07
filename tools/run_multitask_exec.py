# Runner to test end-to-end allCommands() behavior with a multi-command string
import os
import time

# Ensure local package imports resolve
os.environ.setdefault('PYTHONPATH', os.getcwd())

from engine.command import allCommands

TEST_QUERY = "open notepad, open notepad and type bahubali and open youtube, open youtube play dosti song"

print("Invoking allCommands with:")
print(TEST_QUERY)

# Call allCommands with the string (message != 1 means treat as text input)
result = allCommands(TEST_QUERY)
print("allCommands returned:", result)

# Give some time for background threads to start and print
print("Waiting 5 seconds for background execution traces...")
time.sleep(5)
print("Done")

# Run multitask execution using engine.command.allCommands
import time
from engine.command import allCommands

TEST_QUERY = "open notepad, open notepad and type bahubali and open youtube, open youtube play dosti song"

print("Running multitask test with query:")
print(TEST_QUERY)

# Call allCommands with the test query
allCommands(TEST_QUERY)

# Sleep to allow background threads to run and print logs
print("Waiting for background tasks to complete...")
time.sleep(8)
print("Done.")

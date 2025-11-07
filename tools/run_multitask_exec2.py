# Run multitask execution test for Jarvis
import time
from engine.command import allCommands

TEST_QUERY = "open notepad, open notepad and type bahubali and open youtube, open youtube play dosti song"

print("Running multitask execution test...")
print(f"Test query: {TEST_QUERY}")

# Call allCommands with the test query
allCommands(TEST_QUERY)

# Sleep to allow background threads to print logs and perform actions
print("Waiting for background tasks to complete...")
time.sleep(8)
print("Test complete.")

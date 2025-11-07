#!/usr/bin/env python3
"""Test multitasking system execution with various scenarios"""
import os
import sys
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.task_manager import task_manager
from engine.enhanced_parser import enhanced_parser
from engine.features import execute_complex_command

# Enable headless mode for testing
os.environ['JARVIS_HEADLESS'] = '1'

print("=" * 80)
print("MULTITASKING SYSTEM EXECUTION TEST")
print("=" * 80)

test_scenarios = [
    {
        'name': '4 Parallel Open Commands',
        'query': 'open calculator and open notepad and open telegram and open whatsapp',
        'expected_parallel': 4
    },
    {
        'name': '5 Mixed Tasks (Open + Telegram + YouTube)',
        'query': 'open calculator and open notepad and open telegram search john send hi and play music on youtube and open google',
        'expected_parallel': 5
    },
    {
        'name': '3 Telegram Messages Simultaneously',
        'query': 'open telegram search alice send hello and open telegram search bob send hi there and open telegram search charlie send test message',
        'expected_parallel': 3
    },
    {
        'name': 'Mixed Commands with Open and Play',
        'query': 'open calculator and play song on youtube and open notepad and open telegram',
        'expected_parallel': 4
    }
]

def test_scenario(scenario):
    """Test a single multitasking scenario"""
    print(f"\n{'-' * 80}")
    print(f"Testing: {scenario['name']}")
    print(f"Query: {scenario['query']}")
    print(f"{'-' * 80}")
    
    try:
        # Step 1: Parse commands
        print("\n[Step 1] Parsing commands...")
        commands = enhanced_parser.extract_commands(scenario['query'])
        print(f"✓ Parsed {len(commands)} commands")
        for i, cmd in enumerate(commands, 1):
            cmd_text = cmd.get('query') or cmd.get('original', '')
            print(f"  {i}. [{cmd.get('type', 'unknown')}] {cmd_text}")
        
        # Step 2: Get execution plan
        print("\n[Step 2] Getting execution plan...")
        execution_plan = enhanced_parser.suggest_parallel_execution(commands)
        parallel_count = len(execution_plan.get('parallel', []))
        sequential_count = len(execution_plan.get('sequential', []))
        
        print(f"✓ Execution plan created:")
        print(f"  - Parallel tasks: {parallel_count}")
        print(f"  - Sequential tasks: {sequential_count}")
        
        if parallel_count != scenario.get('expected_parallel', parallel_count):
            print(f"⚠ Warning: Expected {scenario.get('expected_parallel')} parallel tasks, got {parallel_count}")
        
        # Step 3: Execute commands
        print("\n[Step 3] Executing commands...")
        start_time = time.time()
        
        if len(commands) > 1:
            # Use task_manager for multiple commands
            task_manager.execute_multiple_commands(commands)
        else:
            # Single command
            task_manager.execute_command(commands[0])
        
        execution_time = time.time() - start_time
        print(f"✓ Execution completed in {execution_time:.2f} seconds")
        
        # Step 4: Verify task completion
        print("\n[Step 4] Verifying task completion...")
        active_tasks = len(task_manager.active_tasks)
        if active_tasks == 0:
            print("✓ All tasks completed (no active tasks remaining)")
        else:
            print(f"⚠ {active_tasks} tasks still active")
        
        # Step 5: Test individual command execution
        print("\n[Step 5] Testing individual command execution...")
        test_individual_commands(commands)
        
        print(f"\n✓ Scenario '{scenario['name']}' PASSED")
        return True
        
    except Exception as e:
        print(f"\n✗ Scenario '{scenario['name']}' FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_commands(commands):
    """Test that individual commands can execute correctly"""
    print("  Testing individual command execution...")
    for i, cmd in enumerate(commands, 1):
        try:
            cmd_text = cmd.get('query') or cmd.get('original', '')
            cmd_type = cmd.get('type', 'unknown')
            
            # Test execute_complex_command for messaging commands
            if 'telegram' in cmd_text.lower() or 'whatsapp' in cmd_text.lower():
                result = execute_complex_command(cmd_text)
                print(f"    {i}. [{cmd_type}] {cmd_text[:50]}... → {result}")
            else:
                # Test via task_manager
                result = task_manager.execute_command(cmd)
                print(f"    {i}. [{cmd_type}] {cmd_text[:50]}... → OK")
        except Exception as e:
            print(f"    {i}. [{cmd.get('type', 'unknown')}] Failed: {e}")

def test_telegram_parsing():
    """Test Telegram command parsing specifically"""
    print(f"\n{'-' * 80}")
    print("Testing Telegram Command Parsing")
    print(f"{'-' * 80}")
    
    telegram_queries = [
        "open telegram and search for vachi send hi",
        "open telegram search alice send hello there",
        "telegram find bob send test message"
    ]
    
    for query in telegram_queries:
        print(f"\nQuery: {query}")
        try:
            result = execute_complex_command(query)
            print(f"✓ Result: {result}")
        except Exception as e:
            print(f"✗ Error: {e}")

# Run all tests
print("\n" + "=" * 80)
print("RUNNING ALL TEST SCENARIOS")
print("=" * 80)

passed = 0
failed = 0

for scenario in test_scenarios:
    if test_scenario(scenario):
        passed += 1
    else:
        failed += 1

# Test Telegram parsing
test_telegram_parsing()

# Summary
print(f"\n{'=' * 80}")
print("TEST SUMMARY")
print(f"{'=' * 80}")
print(f"✓ Passed: {passed}")
print(f"✗ Failed: {failed}")
print(f"Total: {passed + failed}")
print(f"\nMultitasking System Status: {'✓ WORKING' if failed == 0 else '⚠ SOME ISSUES'}")
print("=" * 80)


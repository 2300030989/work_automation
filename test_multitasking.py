#!/usr/bin/env python3
"""
Test script for Jarvis multitasking functionality
"""

from engine.task_manager import task_manager
from engine.enhanced_parser import enhanced_parser

def test_multitasking():
    """Test various multitasking scenarios"""
    
    print("=== Jarvis Multitasking Test ===\n")
    
    # Test cases
    test_queries = [
        "Open notepad and open calculator",
        "Play music on youtube and open google",
        "Search for weather and tell me the time",
        "Open notepad then open calculator and also play music on youtube",
        "Call john and send message to mary",
        "What time is it and what's the weather",
        "Open google and search for python tutorials and also open notepad"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"Test {i}: {query}")
        
        # Check if it's a multitask request
        is_multitask = enhanced_parser.is_multitask_request(query)
        print(f"  Multitask detected: {is_multitask}")
        
        if is_multitask:
            # Extract commands
            commands = enhanced_parser.extract_commands(query)
            print(f"  Extracted {len(commands)} commands:")
            
            for j, cmd in enumerate(commands):
                print(f"    {j+1}. {cmd['type']}: {cmd['original']}")
            
            # Get execution plan
            execution_plan = enhanced_parser.suggest_parallel_execution(commands)
            print(f"  Parallel commands: {len(execution_plan['parallel'])}")
            print(f"  Sequential commands: {len(execution_plan['sequential'])}")
            
            # Simulate execution (don't actually run to avoid system calls)
            if execution_plan['parallel']:
                parallel_queries = [cmd['original'] for cmd in execution_plan['parallel']]
                print(f"  Would execute in parallel: {parallel_queries}")
            
            if execution_plan['sequential']:
                sequential_queries = [cmd['original'] for cmd in execution_plan['sequential']]
                print(f"  Would execute sequentially: {sequential_queries}")
        
        print("-" * 50)

def demo_voice_commands():
    """Show example voice commands that work with multitasking"""
    
    print("\n=== Example Voice Commands for Multitasking ===\n")
    
    examples = [
        "Jarvis, open notepad and calculator",
        "Open google and play music on youtube",
        "Search for weather and tell me the time",
        "Open notepad then open calculator and also open google",
        "What's the weather and what time is it",
        "Open multiple apps: notepad, calculator, and google",
        "Start notepad and play music simultaneously",
        "Open google and search for python tutorials",
        "Call john and send a message to mary",
        "Open notepad and also open calculator and play music"
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"{i:2d}. \"{example}\"")
    
    print("\n=== Tips for Using Multitasking ===\n")
    print("• Use connecting words: 'and', 'also', 'then', 'next'")
    print("• Use semicolons or ampersands: ';' or '&'")
    print("• Be specific about what you want to do simultaneously")
    print("• Commands like 'open', 'play', 'search' can run in parallel")
    print("• Commands like 'call', 'message' are executed sequentially")

if __name__ == "__main__":
    test_multitasking()
    demo_voice_commands()
    
    print("\n=== Ready to Test! ===\n")
    print("To test with the actual Jarvis interface:")
    print("1. Run: python run.py")
    print("2. Try the voice commands shown above")
    print("3. Jarvis will detect multitask requests and execute them simultaneously")

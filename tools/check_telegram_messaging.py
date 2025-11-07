#!/usr/bin/env python3
"""
Check if Telegram messaging functionality is working properly.
Tests both Telethon API and Desktop automation methods.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def check_telethon_installation():
    """Check if telethon library is installed"""
    try:
        import telethon
        print("✓ Telethon is installed")
        print(f"  Version: {telethon.__version__}")
        return True
    except ImportError:
        print("✗ Telethon is NOT installed")
        print("  Install it with: pip install telethon")
        return False

def check_environment_variables():
    """Check if required Telegram environment variables are set"""
    api_id = os.environ.get('TELEGRAM_API_ID')
    api_hash = os.environ.get('TELEGRAM_API_HASH')
    session = os.environ.get('TELEGRAM_SESSION', 'jarvis_telegram')
    
    print("\n=== Environment Variables Check ===")
    if api_id:
        print(f"✓ TELEGRAM_API_ID is set: {api_id[:3]}*** (hidden)")
    else:
        print("✗ TELEGRAM_API_ID is NOT set")
        print("  Get it from: https://my.telegram.org/apps")
    
    if api_hash:
        print(f"✓ TELEGRAM_API_HASH is set: {api_hash[:6]}*** (hidden)")
    else:
        print("✗ TELEGRAM_API_HASH is NOT set")
        print("  Get it from: https://my.telegram.org/apps")
    
    print(f"  TELEGRAM_SESSION: {session}")
    
    return bool(api_id and api_hash)

def test_send_telegram_function():
    """Test the send_telegram function"""
    print("\n=== Testing send_telegram() Function ===")
    
    # Import after path setup
    from engine.features import send_telegram
    
    # Check if in headless mode
    headless = os.environ.get('JARVIS_HEADLESS', '').lower() in ('1', 'true', 'yes')
    if headless:
        print("⚠ Running in HEADLESS mode (simulation only)")
        result = send_telegram('@test_user', 'Test message from Jarvis')
        if result:
            print("✓ send_telegram() returned True (headless mode)")
        else:
            print("✗ send_telegram() returned False")
        return result
    
    # Real test (requires credentials)
    print("Testing with real credentials...")
    try:
        # Use a test contact (you can change this)
        test_contact = '@test_user'  # Change to a valid Telegram username
        test_message = 'Test message from Jarvis - checking if messaging works'
        
        print(f"Attempting to send message to: {test_contact}")
        result = send_telegram(test_contact, test_message)
        
        if result:
            print("✓ send_telegram() completed successfully")
        else:
            print("✗ send_telegram() returned False")
            print("  Check error messages above for details")
        
        return result
    except Exception as e:
        print(f"✗ Error testing send_telegram(): {e}")
        return False

def test_telegram_desktop_function():
    """Test the telegram_desktop_send function"""
    print("\n=== Testing telegram_desktop_send() Function ===")
    
    from engine.features import telegram_desktop_send
    
    headless = os.environ.get('JARVIS_HEADLESS', '').lower() in ('1', 'true', 'yes')
    if headless:
        print("⚠ Running in HEADLESS mode (simulation only)")
        result = telegram_desktop_send('test_contact', 'Test message')
        if result:
            print("✓ telegram_desktop_send() returned True (headless mode)")
        else:
            print("✗ telegram_desktop_send() returned False")
        return result
    
    print("⚠ telegram_desktop_send() requires Telegram Desktop app to be installed")
    print("  This will attempt to automate the desktop app UI")
    print("  Skipping real test to avoid UI automation (set JARVIS_HEADLESS=1 to test)")
    return None

def check_dependencies():
    """Check for other required dependencies"""
    print("\n=== Checking Dependencies ===")
    
    dependencies = {
        'pyautogui': 'pyautogui',
        'pygetwindow': 'pygetwindow'
    }
    
    all_installed = True
    for module_name, package_name in dependencies.items():
        try:
            __import__(module_name)
            print(f"✓ {package_name} is installed")
        except ImportError:
            print(f"✗ {package_name} is NOT installed")
            print(f"  Install with: pip install {package_name}")
            all_installed = False
    
    return all_installed

def main():
    """Run all checks"""
    print("=" * 60)
    print("Telegram Messaging Functionality Check")
    print("=" * 60)
    
    results = {
        'telethon_installed': check_telethon_installation(),
        'env_vars_set': check_environment_variables(),
        'dependencies': check_dependencies(),
    }
    
    # Only test functions if basic requirements are met
    if results['telethon_installed'] and results['env_vars_set']:
        results['send_telegram'] = test_send_telegram_function()
    else:
        print("\n⚠ Skipping send_telegram() test - missing requirements")
        results['send_telegram'] = None
    
    test_telegram_desktop_function()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if results['telethon_installed'] and results['env_vars_set']:
        if results['send_telegram']:
            print("✓ Telegram messaging (Telethon API) appears to be WORKING")
        elif results['send_telegram'] is False:
            print("✗ Telegram messaging (Telethon API) is NOT working")
            print("  Check the error messages above for details")
        else:
            print("⚠ Could not test Telegram messaging (Telethon API)")
    else:
        print("✗ Telegram messaging (Telethon API) cannot work:")
        if not results['telethon_installed']:
            print("  - Telethon library is not installed")
        if not results['env_vars_set']:
            print("  - Environment variables are not set")
    
    print("\nTo set up Telegram API credentials:")
    print("1. Go to https://my.telegram.org/apps")
    print("2. Create a new application")
    print("3. Get your API ID and API Hash")
    print("4. Set environment variables:")
    print("   - TELEGRAM_API_ID=your_api_id")
    print("   - TELEGRAM_API_HASH=your_api_hash")
    print("5. Run the function once to authenticate (it will prompt for phone number)")
    
    return results

if __name__ == '__main__':
    main()

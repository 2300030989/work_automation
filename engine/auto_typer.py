import time
import pyautogui
from engine.command import speak


def type_in_application(text, delay=0.03):
    """
    Type text in the currently active application
    """
    try:
        # Small delay to ensure application is focused
        time.sleep(0.2)

        # Type the text character by character
        pyautogui.typewrite(text, interval=delay)

        print(f"Successfully typed: {text}")
        return True

    except Exception as e:
        print(f"Error typing text: {e}")
        speak("Sorry, I couldn't type the text")
        return False


def type_with_enter(text, delay=0.03):
    """
    Type text and press Enter
    """
    try:
        type_in_application(text, delay)
        time.sleep(0.15)
        pyautogui.press('enter')
        return True
    except Exception as e:
        print(f"Error typing with Enter: {e}")
        return False


def clear_and_type(text, delay=0.03):
    """
    Select all text and replace with new text
    """
    try:
        # Select all text (Ctrl+A)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1)

        # Type new text
        pyautogui.typewrite(text, interval=delay)

        print(f"Successfully cleared and typed: {text}")
        return True

    except Exception as e:
        print(f"Error clearing and typing: {e}")
        return False

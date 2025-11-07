import sqlite3
import threading
from contextlib import contextmanager

class ThreadSafeDB:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    @contextmanager
    def get_connection(self):
        """Get a thread-safe database connection"""
        conn = sqlite3.connect("jarvis.db", check_same_thread=False)
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

# Global thread-safe database instance
thread_safe_db = ThreadSafeDB()

def get_system_command(app_name):
    """Get system command path safely"""
    with thread_safe_db.get_connection() as cursor:
        try:
            cursor.execute('SELECT path FROM sys_command WHERE LOWER(name)=?', (app_name.lower(),))
            results = cursor.fetchall()
            if results:
                return results[0][0]
        except Exception:
            pass
        return None

def get_web_command(app_name):
    """Get web command URL safely"""
    with thread_safe_db.get_connection() as cursor:
        try:
            cursor.execute('SELECT url FROM web_command WHERE LOWER(name)=?', (app_name.lower(),))
            results = cursor.fetchall()
            if results:
                return results[0][0]
        except Exception:
            pass
        return None


def get_all_system_names():
    """Return a list of all names registered in sys_command"""
    with thread_safe_db.get_connection() as cursor:
        cursor.execute('SELECT name FROM sys_command')
        results = cursor.fetchall()
        return [r[0] for r in results if r and r[0]]


def get_all_web_names():
    """Return a list of all names registered in web_command"""
    with thread_safe_db.get_connection() as cursor:
        cursor.execute('SELECT name FROM web_command')
        results = cursor.fetchall()
        return [r[0] for r in results if r and r[0]]


def save_system_command(name: str, path: str):
    """Save a new system command mapping if it doesn't already exist."""
    if not name or not path:
        return False
    name = name.strip()
    path = path.strip()
    try:
        with thread_safe_db.get_connection() as cursor:
            cursor.execute('SELECT COUNT(*) FROM sys_command WHERE LOWER(name)=?', (name.lower(),))
            if cursor.fetchone()[0] == 0:
                cursor.execute('INSERT INTO sys_command (name, path) VALUES (?, ?)', (name, path))
                return True
    except Exception:
        pass
    return False


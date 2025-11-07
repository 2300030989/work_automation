import threading
import re
import time
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, ALL_COMPLETED
from engine.command import speak
from engine.features import openCommand, PlayYoutube, findContact, whatsApp, makeCall, sendMessage, geminai, chatBot
import eel

class TaskManager:
    def __init__(self, max_workers=15):
        # Increase default max_workers for faster parallel execution
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = {}
        self.task_queue = queue.Queue()
        self.task_id_counter = 0
        
    def generate_task_id(self):
        self.task_id_counter += 1
        return f"task_{self.task_id_counter}"
    
    def execute_command(self, command, task_type="single"):
        """Execute a single command"""
        try:
            # accept either structured command dict or plain string
            if isinstance(command, dict):
                cmd_obj = command
                # Prefer the parsed 'query' (cleaned sub-query) over the raw 'original'
                command = cmd_obj.get('query') or cmd_obj.get('original')
            else:
                cmd_obj = None

            start_t = time.time()
            print(f"Executing command: '{command}' [thread={threading.current_thread().name}] start={start_t}")
            command_lower = (command or '').lower()
            
            if "open" in command_lower and "youtube" in command_lower:
                # Handle "open youtube" command
                result = openCommand(command)
                if result:
                    print(f"Successfully executed: {command}")
                else:
                    print(f"Failed to execute: {command}")
            elif command_lower.startswith('open_and_type') or 'open_and_type' in command_lower:
                # Expect command in form: 'open X and type Y' -> try open then type
                try:
                    # Best-effort: find the 'type' portion
                    parts = command.split(' and ', 1)
                    open_part = parts[0] if parts else command
                    type_part = parts[1] if len(parts) > 1 else ''
                    if open_part:
                        openCommand(open_part)
                    if type_part:
                        # Delegate to notepad-typing helper if it looks like notepad
                        try:
                            from engine.features import openNotepadAndType
                            # Strip leading verbs
                            t = re.sub(r'^(type|write)\s+', '', type_part.strip(), flags=re.IGNORECASE)
                            openNotepadAndType(t)
                        except Exception:
                            print('open_and_type: typing helper failed')
                    print(f"Successfully executed: {command}")
                except Exception as e:
                    print(f"Error in open_and_type: {e}")
            elif cmd_obj and cmd_obj.get('type') == 'open_and_type':
                # Structured open_and_type command: open the app then type
                try:
                    combined = cmd_obj.get('original') or cmd_obj.get('query')
                    # Split into open and type portion
                    parts = combined.split(' and ', 1)
                    open_part = parts[0] if parts else combined
                    type_part = parts[1] if len(parts) > 1 else ''
                    if open_part:
                        openCommand(open_part)
                    if type_part:
                        try:
                            from engine.features import openNotepadAndType
                            t = re.sub(r'^(type|write)\s+', '', type_part.strip(), flags=re.IGNORECASE)
                            openNotepadAndType(t)
                        except Exception:
                            print('open_and_type: typing helper failed')
                    print(f"Successfully executed: {command}")
                except Exception as e:
                    print(f"Error in open_and_type: {e}")
            elif "play" in command_lower and ("youtube" in command_lower or "on youtube" in command_lower):
                # Handle "play song on youtube" command
                result = PlayYoutube(command)
                if result:
                    print(f"Successfully executed: {command}")
                else:
                    print(f"Failed to execute: {command}")
            elif "open" in command_lower:
                # Handle other open commands
                result = openCommand(command)
                if result:
                    print(f"Successfully executed: {command}")
                else:
                    print(f"Failed to execute: {command}")
            elif "send message" in command_lower or "phone call" in command_lower or "video call" in command_lower:
                # Handle messaging and calls - check if it's a Telegram/WhatsApp command first
                if "telegram" in command_lower or "whatsapp" in command_lower:
                    # This is handled by execute_complex_command for Telegram/WhatsApp
                    try:
                        from engine.features import execute_complex_command
                        result = execute_complex_command(command)
                        if result:
                            print(f"Successfully executed messaging command: {command}")
                            return
                    except Exception as e:
                        print(f"Complex command handler failed: {e}")
                
                # Fallback to traditional contact-based messaging
                contact_no, name = findContact(command)
                if contact_no != 0:
                    # In multitasking mode, use mobile by default to avoid blocking
                    # Don't ask for user input in parallel execution
                    if "send message" in command_lower or "send sms" in command_lower:
                        sendMessage("Hello from Jarvis", contact_no, name)
                    elif "phone call" in command_lower:
                        makeCall(name, contact_no)
                    print(f"Successfully executed: {command}")
                else:
                    print(f"Contact not found for: {command}")
            elif "telegram" in command_lower and ("send" in command_lower or "message" in command_lower):
                # Handle Telegram messaging commands directly
                try:
                    from engine.features import execute_complex_command
                    result = execute_complex_command(command)
                    if result:
                        print(f"Successfully executed Telegram command: {command}")
                    else:
                        print(f"Telegram command failed: {command}")
                except Exception as e:
                    print(f"Error executing Telegram command: {e}")
            else:
                # Try AI response
                try:
                    geminai(command)
                    print(f"Successfully executed: {command}")
                except:
                    chatBot(command)
                    print(f"Successfully executed: {command}")
        except Exception as e:
            print(f"Error executing command '{command}': {e}")
            # Don't use speak in threading context to avoid conflicts
            print(f"Failed to execute command: {command}")
        finally:
            try:
                end_t = time.time()
                print(f"Finished command: '{command}' end={end_t} duration={end_t - start_t:.2f}s [thread={threading.current_thread().name}]")
            except Exception:
                pass
    
    def execute_multiple_commands(self, commands):
        """Execute multiple commands simultaneously (supports 4-5 tasks efficiently)"""
        if not commands:
            return
        
        total_commands = len(commands)
        print(f"[TaskManager] Processing {total_commands} commands simultaneously")
        # Run speak in a separate thread to avoid blocking the task manager
        try:
            print("[TaskManager] Speaking announcement (non-blocking)")
            threading.Thread(target=speak, args=(f"Executing {total_commands} commands",), daemon=True).start()
        except Exception as e:
            print(f"[TaskManager] Failed to start speak thread: {e}")

        # Detect GUI-sensitive tasks that involve typing or notepad; these should run sequentially
        def _is_gui_sensitive(cmd):
            try:
                if isinstance(cmd, dict):
                    text = (cmd.get('query') or cmd.get('original') or '')
                else:
                    text = str(cmd or '')
                t = text.lower()
                # Consider typing, writing, open_and_type, and notepad operations as GUI-sensitive
                if 'open_and_type' in t or 'open and type' in t:
                    return True
                if 'type ' in t or t.strip().startswith('type') or 'write ' in t:
                    return True
                if 'notepad' in t:
                    return True
                return False
            except Exception:
                return False

        # Detect commands that need sequential execution (calls, messages with user interaction)
        def _needs_sequential(cmd):
            try:
                if isinstance(cmd, dict):
                    text = (cmd.get('query') or cmd.get('original') or '')
                else:
                    text = str(cmd or '')
                t = text.lower()
                # Commands that need user interaction should run sequentially
                # But messaging commands without user prompts can run in parallel
                if 'phone call' in t or 'video call' in t:
                    return True
                if 'send message' in t and 'which mode' in t:
                    return True
                # Telegram/WhatsApp messaging via API/desktop automation can be parallel
                if 'telegram' in t or 'whatsapp' in t:
                    return False  # These can run in parallel
                return False
            except Exception:
                return False

        parallel_cmds = []
        gui_cmds = []
        sequential_cmds = []
        
        for c in commands:
            if _is_gui_sensitive(c):
                gui_cmds.append(c)
            elif _needs_sequential(c):
                sequential_cmds.append(c)
            else:
                parallel_cmds.append(c)

        print(f"[TaskManager] Classification: {len(parallel_cmds)} parallel, {len(gui_cmds)} GUI-sensitive, {len(sequential_cmds)} sequential")

        # Submit parallel tasks (can handle 4-5+ tasks simultaneously)
        futures = []
        task_info = {}
        for i, command in enumerate(parallel_cmds):
            task_id = self.generate_task_id()
            task_info[task_id] = {
                'command': command,
                'index': i + 1,
                'type': 'parallel',
                'start_time': time.time()
            }
            self.active_tasks[task_id] = task_info[task_id]
            future = self.executor.submit(self.execute_command, command)
            futures.append((task_id, i, future))
            # Log submission and initial future state
            try:
                print(f"[TaskManager] Submitted parallel task {i+1}/{len(parallel_cmds)}: {command} | id={task_id} | future.done={future.done()} | cancelled={future.cancelled()}")
                # Also print a compact mapping for quick lookup
                print(f"[TaskManager] task_map: {task_id} -> {str(command)[:120]}")
            except Exception:
                print(f"[TaskManager] Submitted parallel task {i+1}/{len(parallel_cmds)}: {command}")

        # Run GUI-sensitive tasks sequentially in the current thread to avoid focus contention
        gui_success = 0
        for i, command in enumerate(gui_cmds):
            try:
                task_id = self.generate_task_id()
                task_info[task_id] = {
                    'command': command,
                    'index': len(parallel_cmds) + i + 1,
                    'type': 'gui',
                    'start_time': time.time()
                }
                self.active_tasks[task_id] = task_info[task_id]
                print(f"[TaskManager] Running GUI-sensitive task {i+1}/{len(gui_cmds)}: {command}")
                self.execute_command(command)
                gui_success += 1
                task_info[task_id]['completed'] = True
                task_info[task_id]['end_time'] = time.time()
                del self.active_tasks[task_id]
                print(f"[TaskManager] GUI task {i+1} completed")
            except Exception as e:
                print(f"[TaskManager] GUI task {i+1} failed: {e}")
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]

        # Run sequential tasks one after another
        seq_success = 0
        for i, command in enumerate(sequential_cmds):
            try:
                task_id = self.generate_task_id()
                task_info[task_id] = {
                    'command': command,
                    'index': len(parallel_cmds) + len(gui_cmds) + i + 1,
                    'type': 'sequential',
                    'start_time': time.time()
                }
                self.active_tasks[task_id] = task_info[task_id]
                print(f"[TaskManager] Running sequential task {i+1}/{len(sequential_cmds)}: {command}")
                self.execute_command(command)
                seq_success += 1
                task_info[task_id]['completed'] = True
                task_info[task_id]['end_time'] = time.time()
                del self.active_tasks[task_id]
                print(f"[TaskManager] Sequential task {i+1} completed")
                if i < len(sequential_cmds) - 1:
                    time.sleep(0.5)  # Small delay between sequential tasks
            except Exception as e:
                print(f"[TaskManager] Sequential task {i+1} failed: {e}")
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]

        # Wait for all parallel tasks to complete with an overall timeout
        # Determine per-task timeout and compute an overall wait (max of per-task timeouts)
        completed_tasks = 0
        future_map = {future: (task_id, i) for (task_id, i, future) in futures}
        per_future_timeouts = {}
        for task_id, i, future in futures:
            command_text = task_info.get(task_id, {}).get('command', '')
            if isinstance(command_text, dict):
                command_text = command_text.get('query') or command_text.get('original') or ''
            timeout = 60 if ('telegram' in str(command_text).lower() or 'whatsapp' in str(command_text).lower()) else 45
            per_future_timeouts[future] = timeout

        # Use wait to avoid blocking on a single future sequentially
        future_list = [f for (_, _, f) in futures]
        # Use a more generous overall timeout when multiple parallel tasks are present.
        # Multiply the max per-task timeout by the number of parallel tasks to allow
        # concurrent network-bound operations to complete without false timeouts.
        max_per = max(per_future_timeouts.values()) if per_future_timeouts else 45
        overall_timeout = max_per * max(1, len(future_list))
        print(f"[TaskManager] Waiting for up to {overall_timeout}s for all {len(futures)} parallel tasks to complete (max_per_task={max_per})")

        done, not_done = wait(future_list, timeout=overall_timeout, return_when=ALL_COMPLETED)

        # Process completed futures
        for future in done:
            try:
                task_id, i = future_map.get(future, (None, None))
                # re-raise exception if any
                exc = None
                try:
                    exc = future.exception(timeout=0)
                except Exception:
                    pass
                if exc:
                    print(f"[TaskManager] Parallel task (id={task_id}) failed with exception: {exc}")
                else:
                    print(f"[TaskManager] Parallel task (id={task_id}) completed successfully")
                    completed_tasks += 1
                if task_id and task_id in task_info:
                    task_info[task_id]['completed'] = True
                    task_info[task_id]['end_time'] = time.time()
                if task_id and task_id in self.active_tasks:
                    del self.active_tasks[task_id]
            except Exception as e:
                print(f"[TaskManager] Error processing completed future: {e}")

        # Handle not-done futures (timed out)
        for future in not_done:
            try:
                task_id, i = future_map.get(future, (None, None))
                print(f"[TaskManager] Parallel task (id={task_id}) did not complete within {overall_timeout}s, attempting to cancel")
                try:
                    future.cancel()
                except Exception:
                    pass
                try:
                    exc = future.exception(timeout=0)
                except Exception:
                    exc = None
                print(f"[TaskManager] Parallel task (id={task_id}) timed out. future_exception={exc}")
                if task_id and task_id in self.active_tasks:
                    del self.active_tasks[task_id]
            except Exception as e:
                print(f"[TaskManager] Error handling not-done future: {e}")

        total_success = completed_tasks + gui_success + seq_success
        print(f"[TaskManager] All tasks completed. {total_success} out of {total_commands} successful")
        if total_success == total_commands:
            speak(f"Successfully completed all {total_commands} tasks")
        else:
            speak(f"Completed {total_success} out of {total_commands} tasks")
    
    def parse_multiple_commands(self, query):
        """Parse a query to extract multiple commands"""
        # Common separators for multiple commands
        separators = [" and ", " also ", " then ", " after that ", " next ", "; ", " & "]
        
        commands = [query.strip()]

        for separator in separators:
            if separator in query.lower():
                # Split by separator and clean up
                parts = [p.strip() for p in re.split(re.escape(separator), query, flags=re.IGNORECASE) if p.strip()]
                if not parts:
                    continue

                # Heuristic merge: attach context-only fragments like 'send X' or 'say X'
                # to the previous part when that previous part mentions a platform (telegram/whatsapp/instagram)
                merged = []
                i = 0
                n = len(parts)
                while i < n:
                    cur = parts[i]
                    # Merge following fragments that look like message/body or search/find
                    j = i + 1
                    while j < n:
                        nxt = parts[j]
                        low_nxt = (nxt or '').lower()
                        low_cur = (cur or '').lower()
                        # If next fragment is a context fragment (send/say/search/find/message)
                        # and it does NOT itself include another platform, attach it to current.
                        if re.search(r"\b(send|say|saying|says|message|dm|search|find|to)\b", low_nxt) and not re.search(r"\b(telegram|whatsapp|instagram|insta)\b", low_nxt):
                            # Only attach if current mentions a platform or already looks like a command that should take a body
                            if re.search(r"\b(telegram|whatsapp|instagram|insta)\b", low_cur) or re.search(r"\b(search|find)\b", low_cur) or re.search(r"\bopen\b", low_cur):
                                cur = cur + ' and ' + nxt
                                j += 1
                                continue
                        break

                    merged.append(cur.strip())
                    # advance i to j
                    i = j

                commands = [cmd for cmd in merged if cmd]
                break

        # Filter out empty commands (safety)
        commands = [cmd for cmd in commands if cmd and cmd.strip()]

        return commands
    
    def shutdown(self):
        """Shutdown the task manager"""
        self.executor.shutdown(wait=True)

# Global task manager instance
task_manager = TaskManager()

@eel.expose
def execute_multiple_commands(query):
    """Eel exposed function to execute multiple commands"""
    commands = task_manager.parse_multiple_commands(query)
    
    if len(commands) > 1:
        # Execute multiple commands
        threading.Thread(target=task_manager.execute_multiple_commands, args=(commands,)).start()
    else:
        # Execute single command
        threading.Thread(target=task_manager.execute_command, args=(commands[0],)).start()
    
    return f"Processing {len(commands)} command(s)"

@eel.expose
def get_active_tasks():
    """Get list of currently active tasks"""
    return list(task_manager.active_tasks.keys())

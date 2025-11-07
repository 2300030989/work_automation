import re
import os
import json

class EnhancedCommandParser:
    def __init__(self):
        self.command_patterns = {
            'open': r'open\s+([a-zA-Z0-9\s]+)',
            'youtube': r'play\s+([a-zA-Z0-9\s]+)\s+on\s+youtube',
            'search': r'search\s+for\s+([a-zA-Z0-9\s]+)',
            'call': r'(?:call|phone)\s+([a-zA-Z0-9\s]+)',
            'message': r'(?:send\s+)?(?:message|text)\s+(?:to\s+)?([a-zA-Z0-9\s]+)',
            'weather': r'(?:weather|forecast)\s+(?:for\s+)?([a-zA-Z0-9\s,]+)',
            'time': r'(?:what\s+time|current\s+time)',
            'date': r'(?:what\s+date|current\s+date)',
            'calculate': r'(?:calculate|compute)\s+([0-9+\-*/().\s]+)',
            'note': r'(?:note|remember)\s+([a-zA-Z0-9\s]+)',
            'reminder': r'(?:remind\s+me|set\s+reminder)\s+([a-zA-Z0-9\s]+)'
        }
        
        self.multitask_indicators = [
            'and', 'also', 'then', 'after that', 'next', '&', ';', ',',
            'while', 'during', 'at the same time', 'simultaneously'
        ]
        # load persisted synonyms (user-trained corrections)
        try:
            self.synonyms = self._load_synonyms()
        except Exception:
            self.synonyms = {}
    
    def extract_commands(self, query):
        """Extract individual commands from a complex query"""
        commands = []

        # Normalize query first (apply trained corrections)
        try:
            normalized_query = self.normalize_query(query)
        except Exception:
            normalized_query = query

        # Split by multitask indicators
        parts = self._split_by_multitask_indicators(normalized_query)
        
        for part in parts:
            command = self._parse_single_command(part.strip())
            if command:
                commands.append(command)
        
        # Post-process to merge patterns like: open X + (type|write) Y => open_and_type
        merged = []
        i = 0
        while i < len(commands):
            cur = commands[i]
            nxt = commands[i+1] if i+1 < len(commands) else None

            try:
                nxt_query_l = (nxt.get('query') or '').strip().lower() if nxt else ''
            except Exception:
                nxt_query_l = ''

            # If next piece is a 'type/write' general command, attach it to the open command
            if nxt and cur.get('type') == 'open' and nxt.get('type') in ('general', 'note') and (
                nxt_query_l.startswith('type') or nxt_query_l.startswith('write') or nxt_query_l.startswith('type in') or nxt_query_l.startswith('type into') or nxt_query_l.startswith('write to')
            ):
                combined_query = f"{cur.get('original','')} and {nxt.get('original','')}"
                merged_cmd = {
                    'type': 'open_and_type',
                    'query': combined_query,
                    'parameters': tuple(cur.get('parameters', ())) + tuple(nxt.get('parameters', ())),
                    'original': combined_query
                }
                merged.append(merged_cmd)
                i += 2
                continue

            merged.append(cur)
            i += 1

        return merged
    
    SYNONYMS_PATH = os.path.join(os.path.dirname(__file__), "synonyms.json")

    def _load_synonyms(self):
        try:
            if os.path.exists(self.SYNONYMS_PATH):
                with open(self.SYNONYMS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return {k.lower(): v for k, v in data.items()}
        except Exception:
            pass
        return {}

    def _save_synonyms(self):
        try:
            with open(self.SYNONYMS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.synonyms, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def train_correction(self, wrong: str, correct: str):
        """Persist a user-taught correction. Both inputs are normalized to lower-case."""
        if not wrong or not correct:
            return False
        w = wrong.strip().lower()
        c = correct.strip()
        if not w or not c:
            return False
        self.synonyms[w] = c
        self._save_synonyms()
        return True

    def normalize_query(self, query: str) -> str:
        """Apply known corrections to the query. Replaces standalone tokens that match keys in synonyms."""
        if not query:
            return query
        # Don't normalize text that is part of a body after write/type/translate
        # Find position of writing verbs and split the query into (pre, post)
        lower_q = query.lower()
        split_match = re.search(r"\b(write|type|translate)(?:\s+an?|\s+the)?\b", lower_q)
        post_start = None
        if split_match:
            post_start = split_match.end()

        tokens = re.findall(r"\w+|\W+", query)
        # curated and DB-backed app list
        common_apps = ['youtube', 'brave', 'chrome', 'edge', 'firefox', 'notepad', 'calculator', 'whatsapp', 'spotify', 'vscode', 'pycharm']
        try:
            from engine.thread_safe_db import get_all_system_names, get_all_web_names
            db_names = []
            try:
                db_names = get_all_system_names() + get_all_web_names()
            except Exception:
                db_names = []
            # merge and dedupe
            candidate_apps = list(dict.fromkeys(common_apps + [n.lower() for n in db_names if isinstance(n, str)]))
        except Exception:
            candidate_apps = common_apps

        import difflib

        # For each token, only normalize if it's before the 'post_start' index (i.e., not in body text)
        idx = 0
        for i, t in enumerate(tokens):
            token_len = len(t)
            # if token is non-word (spaces/punct), just advance index
            if not re.match(r"^\w+$", t):
                idx += token_len
                continue

            # if token appears after the write/type/translate keyword, skip normalization
            if post_start is not None and idx >= post_start:
                idx += token_len
                continue

            key = t.strip().lower()
            # user-trained synonyms win first
            if key and key in self.synonyms:
                tokens[i] = self.synonyms[key]
                idx += token_len
                continue

            # fuzzy-match against candidate apps with a high cutoff
            try:
                matches = difflib.get_close_matches(key, candidate_apps, n=1, cutoff=0.78)
                if matches:
                    tokens[i] = matches[0]
            except Exception:
                pass

            idx += token_len

        return "".join(tokens)
    
    def _split_by_multitask_indicators(self, query):
        """Split query by multitask indicators"""
        # Create a regex pattern for all indicators
        pattern = '|'.join([re.escape(indicator) for indicator in self.multitask_indicators])
        
        # Split by the pattern
        parts = re.split(pattern, query, flags=re.IGNORECASE)
        
        # Clean up parts
        cleaned_parts = []
        for part in parts:
            part = part.strip()
            if part and len(part) > 2:  # Filter out very short parts
                cleaned_parts.append(part)
        
        return cleaned_parts if cleaned_parts else [query]
    
    def _parse_single_command(self, query):
        """Parse a single command and return structured command"""
        query_lower = query.lower()
        
        # Check each pattern
        for command_type, pattern in self.command_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                return {
                    'type': command_type,
                    'query': query,
                    'parameters': match.groups(),
                    'original': query
                }
        
        # If no specific pattern matches, treat as general query
        return {
            'type': 'general',
            'query': query,
            'parameters': [],
            'original': query
        }
    
    def is_multitask_request(self, query):
        """Check if the query contains multitask indicators"""
        query_lower = query.lower()
        # If query explicitly contains patterns like 'open X and write/type/translate Y',
        # treat it as a single complex command (do not mark as multitask)
        try:
            if re.search(r"open\s+[a-zA-Z0-9_\-]+.*\b(?:and|then|,)\b.*\b(?:write|type|translate|translate to|translate in)\b", query_lower, flags=re.IGNORECASE):
                return False
        except Exception:
            pass

        return any(indicator in query_lower for indicator in self.multitask_indicators)
    
    def get_priority_commands(self, commands):
        """Sort commands by priority (immediate actions first)"""
        priority_order = {
            'call': 1,
            'message': 2,
            'open': 3,
            'youtube': 4,
            'search': 5,
            'weather': 6,
            'time': 7,
            'date': 8,
            'calculate': 9,
            'note': 10,
            'reminder': 11,
            'general': 12
        }
        
        return sorted(commands, key=lambda x: priority_order.get(x['type'], 999))
    
    def suggest_parallel_execution(self, commands):
        """Suggest which commands can be executed in parallel (optimized for 4-5 tasks)"""
        parallel_groups = []
        sequential_commands = []
        
        for command in commands:
            command_type = command.get('type', 'general')
            command_text = (command.get('query') or command.get('original') or '').lower()
            
            # Commands that can run in parallel
            if command_type in ['open', 'youtube', 'search', 'weather', 'time', 'date', 'calculate']:
                parallel_groups.append(command)
            # Telegram/WhatsApp messaging can run in parallel (uses API/desktop automation)
            elif 'telegram' in command_text or 'whatsapp' in command_text:
                if 'send' in command_text or 'message' in command_text:
                    parallel_groups.append(command)  # Telegram/WhatsApp messaging can be parallel
                else:
                    parallel_groups.append(command)
            # Traditional calls/messages that need user interaction should be sequential
            elif command_type in ['call']:
                sequential_commands.append(command)
            # Traditional SMS messages might need user interaction
            elif command_type in ['message']:
                # Check if it's a simple message command without user prompts
                if 'send message' in command_text and not ('which mode' in command_text or 'whatsapp or mobile' in command_text):
                    parallel_groups.append(command)  # Can run in parallel if no user interaction needed
                else:
                    sequential_commands.append(command)
            elif command_type in ['note', 'reminder']:
                sequential_commands.append(command)
            else:
                # Default to parallel for unknown types
                parallel_groups.append(command)
        
        return {
            'parallel': parallel_groups,
            'sequential': sequential_commands
        }

# Global parser instance
enhanced_parser = EnhancedCommandParser()

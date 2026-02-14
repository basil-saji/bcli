import sys, time, threading, json, os
from broadcaster import Broadcaster
from colorama import Fore, Style, init

try:
    import msvcrt
    def get_key(): return msvcrt.getch().decode('utf-8', errors='ignore')
except ImportError:
    import tty, termios
    def get_key():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

init(autoreset=True)
MEMORY_FILE = "memory.json"
SUPABASE_URL = "https://wqqckkuycvthvizcwfgn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxcWNra3V5Y3Z0aHZpemN3ZmduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYxNDcxMDYsImV4cCI6MjA4MTcyMzEwNn0.d2mfBuqKG8g4NSLb-EMCnzd-U-_mH35FwOxsbjbuGQ8"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_memory(data):
    with open(MEMORY_FILE, 'w') as f: json.dump(data, f, indent=4)

def run_cli():
    mem = load_memory()
    
    # UI FIX: No suggested room name, user enters freely
    room = input("Room id: ").strip()
    if not room: room = "general"
    
    username = mem.get('username')
    if not username:
        username = input("Username: ")
        mem['username'] = username
    
    save_memory(mem)

    input_buffer = ""
    terminal_lock = threading.Lock()
    def reprint_input():
        sys.stdout.write(f"\r\033[K> {input_buffer}")
        sys.stdout.flush()

    bc = Broadcaster(SUPABASE_URL, SUPABASE_KEY, room, username, terminal_lock, reprint_input)
    
    # Load Room history if it exists in memory
    bc.display_history = mem.get('rooms', {}).get(room, [])

    while not bc.enabled: time.sleep(0.1)

    try:
        while True:
            char = get_key()
            if char == '\x03': raise KeyboardInterrupt
            with terminal_lock:
                if char in ('\r', '\n'):
                    if input_buffer.startswith(';'):
                        parts = input_buffer[1:].split()
                        cmd = parts[0].lower() if parts else ""
                        if cmd == "clear": 
                            bc.display_history = []
                            sys.stdout.write("\033[H\033[J")
                        elif cmd in ("exit", "quit", "kill"): raise KeyboardInterrupt
                        elif cmd == "nick" and len(parts) > 1:
                            old = bc.username
                            bc.username = parts[1]
                            mem['username'] = bc.username
                            save_memory(mem)
                            bc.send({"from": "System", "content": f"{old} changed name to {bc.username}"})
                        input_buffer = ""
                    elif input_buffer.strip():
                        # Direct message handling
                        if input_buffer.startswith(';@'):
                            parts = input_buffer[2:].split(' ', 1)
                            if len(parts) == 2:
                                bc.send({"to": parts[0], "content": parts[1]})
                        else:
                            bc.send({"content": input_buffer})
                        input_buffer = ""
                    
                    # Persistence
                    if 'rooms' not in mem: mem['rooms'] = {}
                    mem['rooms'][room] = bc.display_history[-50:]
                    save_memory(mem)
                    bc._refresh_ui()

                elif char in ('\x7f', '\x08'):
                    input_buffer = input_buffer[:-1]
                    reprint_input()
                elif ord(char) >= 32:
                    input_buffer += char
                    sys.stdout.write(char)
                    sys.stdout.flush()
    except KeyboardInterrupt:
        if 'rooms' not in mem: mem['rooms'] = {}
        mem['rooms'][room] = bc.display_history[-50:]
        save_memory(mem)
        sys.exit(0)

if __name__ == "__main__":
    run_cli()